# adminside/management/commands/generate_features.py

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from adminside.models import Product, ML_Feature_Vectors
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.models import Model
import numpy as np
from PIL import Image
from rembg import remove

# Load the ML model once
base_model = VGG16(weights='imagenet', include_top=False)
model = Model(inputs=base_model.input, outputs=base_model.output)

def extract_features(img_path):
    """Extracts features from an image, with background removal."""
    try:
        original_img = Image.open(img_path)
        img_no_bg = remove(original_img)
        
        img = img_no_bg.resize((224, 224))
        if img.mode != "RGB": 
            img = img.convert("RGB")
            
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        features = model.predict(x).flatten()
        return features.tolist()
    except Exception as e:
        print(f"Error processing image {img_path}: {e}")
        return None

class Command(BaseCommand):
    help = 'Generates feature vectors for all products.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting to process all products...'))
        
        for product in Product.objects.all():
            if not product.base_image:
                continue

            image_path = os.path.join(settings.MEDIA_ROOT, str(product.base_image))
            
            if not os.path.exists(image_path):
                self.stdout.write(self.style.WARNING(f'SKIPPED: Image not found for {product.name} at {image_path}'))
                continue

            self.stdout.write(f'Processing {product.name}...')
            
            feature_vector = extract_features(image_path)
            
            if feature_vector:
                ML_Feature_Vectors.objects.update_or_create(
                    product_id=product,
                    defaults={
                        'feature_vector': feature_vector,
                        'model_name': 'VGG16-Rembg',
                        'model_version': '1.0',
                        'vector_length': len(feature_vector),
                    }
                )

        self.stdout.write(self.style.SUCCESS('Finished processing all products!'))