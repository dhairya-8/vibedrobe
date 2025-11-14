# adminside/management/commands/extract_features.py

import os
import pickle
import numpy as np
import torch
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from adminside.models import Product

import timm
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform


class Command(BaseCommand):
    help = 'Extract features from all product images using ConvNeXt V2 Large model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='convnextv2_features.pkl',
            help='Output file name for features (default: convnextv2_features.pkl)'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        output_path = os.path.join(settings.BASE_DIR, output_file)

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('VIBEDROBE IMAGE FEATURE EXTRACTION'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # --- LOAD THE MODEL ---
        self.stdout.write('\n📦 Loading ConvNeXt V2 Large model...')
        self.stdout.write('⚠️  First run will download ~800MB model weights...\n')

        try:
            model = timm.create_model('convnextv2_large.fcmae_ft_in22k_in1k_384', pretrained=True)
            model.eval()

            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model = model.to(device)

            config = resolve_data_config({}, model=model)
            transform = create_transform(**config)

            self.stdout.write(self.style.SUCCESS(f'✅ Model loaded on {device}'))
            self.stdout.write(f'   Input size: {config["input_size"]}')
            self.stdout.write(f'   Model parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M\n')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to load model: {e}'))
            return

        # --- EXTRACT FEATURES ---
        all_products = Product.objects.all()
        total = all_products.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️  No products found in database!'))
            return

        self.stdout.write(f'🔍 Found {total} products in database')
        self.stdout.write('⏳ Starting feature extraction...\n')

        product_features = {}
        success_count = 0
        error_count = 0

        for idx, product in enumerate(all_products, 1):
            # Progress indicator
            if idx % 50 == 0 or idx == total:
                percentage = (idx / total) * 100
                self.stdout.write(f'   Progress: {idx}/{total} ({percentage:.1f}%) | '
                                f'Success: {success_count} | Errors: {error_count}')

            # Check if product has image
            if not product.base_image:
                error_count += 1
                continue

            if not hasattr(product.base_image, 'path'):
                error_count += 1
                continue

            image_path = product.base_image.path

            if not os.path.exists(image_path):
                self.stdout.write(self.style.WARNING(
                    f'⚠️  Image not found for Product ID {product.id}: {image_path}'
                ))
                error_count += 1
                continue

            # Extract features
            try:
                img = Image.open(image_path).convert('RGB')
                img_tensor = transform(img).unsqueeze(0).to(device)

                with torch.no_grad():
                    features = model.forward_features(img_tensor)
                    features = features.mean(dim=[2, 3])  # Global average pooling
                    features = features.cpu().numpy().flatten()

                product_features[product.id] = features
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  Failed to process Product ID {product.id}: {str(e)}'
                ))
                error_count += 1

        # --- SAVE FEATURES ---
        self.stdout.write('\n💾 Saving features to disk...')

        try:
            with open(output_path, 'wb') as f:
                pickle.dump(product_features, f)

            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            
            if len(product_features) > 0:
                feature_dim = len(list(product_features.values())[0])
            else:
                feature_dim = 0

            self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
            self.stdout.write(self.style.SUCCESS('✅ FEATURE EXTRACTION COMPLETE!'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(f'📊 Statistics:')
            self.stdout.write(f'   Total products processed: {total}')
            self.stdout.write(f'   Successfully extracted: {success_count}')
            self.stdout.write(f'   Errors: {error_count}')
            self.stdout.write(f'   Feature dimension: {feature_dim}')
            self.stdout.write(f'   Output file: {output_path}')
            self.stdout.write(f'   File size: {file_size_mb:.2f} MB')
            self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to save features: {e}'))