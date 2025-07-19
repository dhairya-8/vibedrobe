from django import template
import os

register = template.Library()

@register.filter
def is_duplicate(gallery_path, base_path):
    """Check if gallery image is a duplicate of base image"""
    if not gallery_path or not base_path:
        return False
        
    gallery_name = os.path.basename(str(gallery_path))
    base_name = os.path.basename(str(base_path))
    
    # For patterns like p1_base.jpg and p1_g1.jpg
    return (gallery_name.endswith('_g1.jpg') and 
            gallery_name.split('_')[0] == base_name.split('_')[0])