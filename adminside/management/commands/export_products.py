# adminside/management/commands/export_products.py

import csv
from django.core.management.base import BaseCommand

# --- IMPORTANT ---
# Make sure to replace 'vibedrobe_app' with the actual name of your app where the models are defined.
from adminside.models import Product

class Command(BaseCommand):
    help = 'Exports all active product data to a CSV file for ML analysis.'

    def handle(self, *args, **kwargs):
        # Define the output file path. This will create the file in your project's root directory.
        file_path = 'product_data.csv'
        self.stdout.write(f"Starting product export to {file_path}...")

        # Use a 'with' statement to ensure the file is properly closed.
        # encoding='utf-8' is important to handle special characters.
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Create a CSV writer object.
            writer = csv.writer(csvfile)

            # --- Define the Header Row ---
            # These are the column names in your CSV file.
            headers = [
                'id', 'name', 'description', 'price', 'category', 'subcategory',
                'brand', 'color', 'material', 'gender', 'tags'
            ]
            writer.writerow(headers)

            # --- Query and Write the Data ---
            # We use select_related to efficiently fetch related model data in a single query.
            # We use prefetch_related for the many-to-many relationship with tags.
            products = Product.objects.filter(is_active=True).select_related(
                'subcategory_id', 'subcategory_id__category_id', 'brand_id', 'material_id'
            ).prefetch_related('product_tags_set')

            # Loop through each product and write its data to a new row in the CSV.
            for product in products:
                # Combine all tags for a product into a single, comma-separated string.
                tags = ', '.join([tag.tag for tag in product.product_tags_set.all()])

                writer.writerow([
                    product.id,
                    product.name,
                    product.description,
                    product.price,
                    product.subcategory_id.category_id.name,
                    product.subcategory_id.name,
                    product.brand_id.name,
                    product.color,
                    product.material_id.name,
                    product.gender,
                    tags
                ])

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully exported {products.count()} products to {file_path}"))