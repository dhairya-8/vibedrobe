# adminside/management/commands/generate_fbt_rules.py

from django.core.management.base import BaseCommand
from django.db import transaction, utils
from collections import defaultdict
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules

from adminside.models import Order_Details, Frequently_Bought_Together

class Command(BaseCommand):
    help = 'Analyzes order history and generates "Frequently Bought Together" rules.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--support',
            type=float,
            help='The minimum support threshold (recommended: 0.005-0.02 for 2000 orders)',
        )
        parser.add_argument(
            '--lift',
            type=float,
            default=1.2,
            help='The minimum lift threshold (default: 1.2)',
        )
        parser.add_argument(
            '--confidence',
            type=float,
            default=0.1,
            help='The minimum confidence threshold (default: 0.1)',
        )

    def handle(self, *args, **kwargs):
        try:
            min_support = kwargs['support']
            min_lift = kwargs['lift']
            min_confidence = kwargs['confidence']

            # Interactive prompt for min_support if not provided
            if min_support is None:
                self.stdout.write(self.style.NOTICE("\n📊 FBT Rule Generation - Support Threshold Guide"))
                self.stdout.write("=" * 60)
                self.stdout.write("For 2000 orders, recommended support values:")
                self.stdout.write("  • 0.005 (0.5%) = Products bought together at least ~10 times")
                self.stdout.write("  • 0.01  (1%)   = Products bought together at least ~20 times")
                self.stdout.write("  • 0.02  (2%)   = Products bought together at least ~40 times")
                self.stdout.write("  • 0.03  (3%)   = Products bought together at least ~60 times")
                self.stdout.write("\nLower values = More rules (but potentially weaker patterns)")
                self.stdout.write("Higher values = Fewer rules (but stronger patterns)")
                self.stdout.write("=" * 60 + "\n")
                
                while True:
                    try:
                        prompt_input = input("Enter minimum support value (e.g., 0.01): ")
                        min_support = float(prompt_input)
                        if 0 < min_support < 1:
                            break
                        else:
                            self.stdout.write(self.style.ERROR("Please enter a value between 0 and 1."))
                    except ValueError:
                        self.stdout.write(self.style.ERROR("Invalid input. Please enter a number."))
            
            self.stdout.write(self.style.SUCCESS(
                f"\n🔍 Starting FBT Analysis\n"
                f"   Support: {min_support} | Lift: {min_lift} | Confidence: {min_confidence}\n"
            ))

            # --- 1. DATA PREPARATION ---
            self.stdout.write("Step 1/4: Fetching transaction data...")
            valid_orders = Order_Details.objects.filter(
                order_id__status__in=['delivered', 'shipped']
            ).values('order_id_id', 'product_variant_id__product_id_id').distinct()

            transactions_dict = defaultdict(list)
            for entry in valid_orders:
                transactions_dict[entry['order_id_id']].append(entry['product_variant_id__product_id_id'])
            
            transactions = [items for items in transactions_dict.values() if len(items) > 1]

            if not transactions:
                self.stdout.write(self.style.WARNING("❌ No multi-item transactions found. Cannot generate FBT rules."))
                return

            total_transactions = len(transactions)
            self.stdout.write(f"   ✓ Found {total_transactions} multi-item orders to analyze\n")

            # Calculate minimum occurrences
            min_occurrences = int(min_support * total_transactions)
            self.stdout.write(f"   → Products must appear together at least {min_occurrences} times\n")

            # --- 2. ALGORITHM EXECUTION ---
            self.stdout.write("Step 2/4: Running Apriori algorithm...")
            te = TransactionEncoder()
            te_ary = te.fit(transactions).transform(transactions)
            df = pd.DataFrame(te_ary, columns=te.columns_)

            frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)
            
            if frequent_itemsets.empty:
                self.stdout.write(self.style.WARNING(
                    f"\n❌ No frequent itemsets found with support >= {min_support}\n"
                    f"\n💡 SOLUTIONS:\n"
                    f"   1. Lower the support value (try {min_support/2:.4f})\n"
                    f"   2. Generate more seed orders (current: ~{total_transactions})\n"
                    f"   3. Check if your PRODUCT_CLUSTERS cover all products\n"
                ))
                return

            self.stdout.write(f"   ✓ Found {len(frequent_itemsets)} frequent itemsets\n")

            self.stdout.write("Step 3/4: Generating association rules...")
            rules = association_rules(
                frequent_itemsets, 
                metric="confidence", 
                min_threshold=min_confidence
            )
            
            # Additional filtering by lift
            rules = rules[rules['lift'] >= min_lift]
            
            if rules.empty:
                self.stdout.write(self.style.WARNING(
                    f"\n❌ No association rules found meeting criteria:\n"
                    f"   • Confidence >= {min_confidence}\n"
                    f"   • Lift >= {min_lift}\n"
                    f"\n💡 SOLUTIONS:\n"
                    f"   1. Lower confidence threshold (try 0.05)\n"
                    f"   2. Lower lift threshold (try 1.0)\n"
                    f"   3. Verify your seed data has strong product associations\n"
                ))
                return
                
            self.stdout.write(f"   ✓ Generated {len(rules)} association rules\n")

            # --- 3. STORE RESULTS ---
            self.stdout.write("Step 4/4: Saving rules to database...")
            
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

            self.stdout.write(self.style.SUCCESS(
                f"\n{'='*60}\n"
                f"✅ SUCCESS! Saved {len(fbt_objects_to_create)} FBT rules\n"
                f"{'='*60}\n"
                f"\n📊 Rule Quality Breakdown:\n"
            ))
            
            # Show quality metrics
            if fbt_objects_to_create:
                high_lift = sum(1 for obj in fbt_objects_to_create if obj.lift_score >= 2.0)
                medium_lift = sum(1 for obj in fbt_objects_to_create if 1.5 <= obj.lift_score < 2.0)
                low_lift = sum(1 for obj in fbt_objects_to_create if obj.lift_score < 1.5)
                
                self.stdout.write(f"   Strong rules (lift >= 2.0):     {high_lift}")
                self.stdout.write(f"   Medium rules (1.5 <= lift < 2): {medium_lift}")
                self.stdout.write(f"   Weak rules (lift < 1.5):        {low_lift}")
                
                avg_confidence = sum(obj.confidence_score for obj in fbt_objects_to_create) / len(fbt_objects_to_create)
                self.stdout.write(f"\n   Average Confidence: {avg_confidence:.2%}")
            
            self.stdout.write("\n💡 TIP: Check your product pages to see FBT recommendations!\n")

        except utils.OperationalError as e:
            self.stdout.write(self.style.ERROR("\n❌ DATABASE ERROR: Could not connect to the database."))
            self.stdout.write(self.style.NOTICE(f"DEBUGGING: Ensure your database server is running.\n"))
            self.stdout.write(f"Technical Error: {e}")

        except utils.IntegrityError as e:
            self.stdout.write(self.style.ERROR("\n❌ DATA INTEGRITY ERROR: Invalid product reference."))
            self.stdout.write(self.style.NOTICE(
                f"DEBUGGING: This happens when an order contains a product ID\n"
                f"that no longer exists in your Product table.\n"
            ))
            self.stdout.write(f"Technical Error: {e}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR("\n❌ UNEXPECTED ERROR"))
            self.stdout.write(f"Technical Error: {type(e).__name__} - {e}")