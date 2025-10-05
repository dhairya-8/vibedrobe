# adminside/management/commands/generate_fbt_rules.py

from django.core.management.base import BaseCommand
from django.db import transaction
from collections import defaultdict
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules

# --- IMPORTANT ---
from adminside.models import Order_Details, Product, Frequently_Bought_Together

class Command(BaseCommand):
    help = 'Analyzes order history and generates "Frequently Bought Together" rules.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("📊 Starting FBT rule generation..."))

        # --- 1. DATA PREPARATION ---
        self.stdout.write("Fetching and preparing transaction data...")
        # We only consider completed orders for accurate analysis.
        valid_orders = Order_Details.objects.filter(
            order_id__status__in=['delivered', 'shipped']
        ).values('order_id_id', 'product_variant_id__product_id_id').distinct()

        # Group product IDs by their order ID
        transactions_dict = defaultdict(list)
        for entry in valid_orders:
            transactions_dict[entry['order_id_id']].append(entry['product_variant_id__product_id_id'])
        
        # Format for mlxtend: a list of lists, filtering out single-item orders
        transactions = [items for items in transactions_dict.values() if len(items) > 1]

        if not transactions:
            self.stdout.write(self.style.WARNING("No multi-item transactions found. Exiting."))
            return

        self.stdout.write(f"Found {len(transactions)} multi-item transactions to analyze.")

        # --- 2. ALGORITHM EXECUTION ---
        self.stdout.write("Running Apriori algorithm to find patterns...")
        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions)
        df = pd.DataFrame(te_ary, columns=te.columns_)

        # --- TUNING PARAMETER: min_support ---
        # This is the most important parameter. 0.01 means "must appear in at least 1% of orders".
        # If you get no rules, try making this number smaller (e.g., 0.005).
        frequent_itemsets = apriori(df, min_support=0.01, use_colnames=True)
        
        if frequent_itemsets.empty:
            self.stdout.write(self.style.WARNING("Apriori did not find any frequent itemsets. Try lowering `min_support`."))
            return

        # Generate the final association rules
        # We're looking for rules with high "lift" (items that are more likely to be bought together than by random chance)
        rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.2)
        
        if rules.empty:
            self.stdout.write(self.style.WARNING("No strong association rules found. Try lowering the `min_threshold` for the metric."))
            return
            
        self.stdout.write(f"Generated {len(rules)} potential rules.")

        # --- 3. STORE RESULTS ---
        self.stdout.write("Saving the best rules to the database...")
        
        with transaction.atomic():
            # Clear old rules before adding new ones
            Frequently_Bought_Together.objects.all().delete()
            
            fbt_objects_to_create = []
            
            # We are interested in simple "If you buy A, you might like B" rules.
            # So we filter for rules with only one item in the antecedent and consequent.
            for _, row in rules.iterrows():
                if len(row['antecedents']) == 1 and len(row['consequents']) == 1:
                    product_a_id = list(row['antecedents'])[0]
                    product_b_id = list(row['consequents'])[0]

                    fbt_objects_to_create.append(
                        Frequently_Bought_Together(
                            product_a_id_id=product_a_id,
                            product_b_id_id=product_b_id,
                            support_score=row['support'],
                            confidence_score=row['confidence'],
                            lift_score=row['lift']
                        )
                    )
            
            # Use bulk_create for high performance
            Frequently_Bought_Together.objects.bulk_create(fbt_objects_to_create)

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully saved {len(fbt_objects_to_create)} FBT rules to the database."))