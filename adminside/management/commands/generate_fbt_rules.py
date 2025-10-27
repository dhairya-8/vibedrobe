# adminside/management/commands/generate_fbt_rules.py

from django.core.management.base import BaseCommand
from django.db import transaction, utils
from collections import defaultdict
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules

# --- IMPORTANT --- ensure your models are imported correctly
from adminside.models import Order_Details, Frequently_Bought_Together

class Command(BaseCommand):
    help = 'Analyzes order history and generates "Frequently Bought Together" rules.'

    # --- UPDATED: Made the argument optional to allow for interactive input ---
    def add_arguments(self, parser):
        parser.add_argument(
            '--support',
            type=float,
            # No default value, so we can check if it was provided
            help='The minimum support threshold. If not provided, the script will ask for it.',
        )

    def handle(self, *args, **kwargs):
        try:
            min_support = kwargs['support']

            # --- NEW: Interactive prompt for min_support if not provided ---
            if min_support is None:
                while True:
                    try:
                        prompt_input = input("Please enter the minimum support value (e.g., 0.01): ")
                        min_support = float(prompt_input)
                        if 0 < min_support < 1:
                            break
                        else:
                            self.stdout.write(self.style.ERROR("Please enter a value between 0 and 1."))
                    except ValueError:
                        self.stdout.write(self.style.ERROR("Invalid input. Please enter a number."))
            
            self.stdout.write(self.style.SUCCESS(f"📊 Starting FBT rule generation with min_support={min_support}..."))

            # --- 1. DATA PREPARATION ---
            self.stdout.write("Fetching and preparing transaction data...")
            valid_orders = Order_Details.objects.filter(
                order_id__status__in=['delivered', 'shipped']
            ).values('order_id_id', 'product_variant_id__product_id_id').distinct()

            transactions_dict = defaultdict(list)
            for entry in valid_orders:
                transactions_dict[entry['order_id_id']].append(entry['product_variant_id__product_id_id'])
            
            transactions = [items for items in transactions_dict.values() if len(items) > 1]

            if not transactions:
                self.stdout.write(self.style.WARNING("No multi-item transactions found to analyze. Exiting."))
                return

            total_transactions = len(transactions)
            self.stdout.write(f"Found {total_transactions} multi-item transactions to analyze.")

            # --- 2. ALGORITHM EXECUTION ---
            self.stdout.write("Running Apriori algorithm...")
            te = TransactionEncoder()
            te_ary = te.fit(transactions).transform(transactions)
            df = pd.DataFrame(te_ary, columns=te.columns_)

            frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)
            
            if frequent_itemsets.empty:
                self.stdout.write(self.style.WARNING(f"Apriori did not find any frequent itemsets with the given support."))
                self.stdout.write(self.style.NOTICE(f"SOLUTION: Try running the command again with a lower --support value than {min_support}."))
                return

            rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.2)
            
            if rules.empty:
                self.stdout.write(self.style.WARNING("No strong association rules found (lift > 1.2)."))
                self.stdout.write(self.style.NOTICE("SOLUTION: The data may not have strong associations, or you could try a lower lift threshold."))
                return
                
            self.stdout.write(f"Generated {len(rules)} potential rules.")

            # --- 3. STORE RESULTS ---
            self.stdout.write("Filtering and saving the best rules to the database...")
            
            with transaction.atomic():
                Frequently_Bought_Together.objects.all().delete()
                
                fbt_objects_to_create = []
                processed_pairs = set()
                
                for _, row in rules.iterrows():
                    if len(row['antecedents']) == 1 and len(row['consequents']) == 1:
                        product_a_id = list(row['antecedents'])[0]
                        product_b_id = list(row['consequents'])[0]

                        if product_a_id > product_b_id:
                            product_a_id, product_b_id = product_b_id, product_a_id
                        
                        pair = (product_a_id, product_b_id)
                        if pair in processed_pairs:
                            continue
                        
                        processed_pairs.add(pair)

                        frequency = int(round(row['support'] * total_transactions))
                        frequency_count = max(1, frequency)

                        fbt_objects_to_create.append(
                            Frequently_Bought_Together(
                                product_a_id_id=product_a_id,
                                product_b_id_id=product_b_id,
                                frequency_count=frequency_count,
                                support_score=row['support'],
                                confidence_score=row['confidence'],
                                lift_score=row['lift']
                            )
                        )
                
                Frequently_Bought_Together.objects.bulk_create(fbt_objects_to_create)

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully saved {len(fbt_objects_to_create)} unique FBT rules to the database."))

        # --- NEW: Catch specific and general errors ---
        except utils.OperationalError as e:
            self.stdout.write(self.style.ERROR("\n❌ DATABASE ERROR: Could not connect to the database."))
            self.stdout.write(self.style.NOTICE(f"DEBUGGING INFO: Ensure your database server is running and settings are correct."))
            self.stdout.write(f"Technical Error: {e}")

        except utils.IntegrityError as e:
            self.stdout.write(self.style.ERROR("\n❌ DATA INTEGRITY ERROR: A rule could not be saved to the database."))
            self.stdout.write(self.style.NOTICE(f"DEBUGGING INFO: This might happen if a product ID from an old order no longer exists in your Product table."))
            self.stdout.write(f"Technical Error: {e}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR("\n❌ AN UNEXPECTED ERROR OCCURRED."))
            self.stdout.write(self.style.NOTICE(f"DEBUGGING INFO: Please review the error message below to identify the problem."))
            self.stdout.write(f"Technical Error: {type(e).__name__} - {e}")