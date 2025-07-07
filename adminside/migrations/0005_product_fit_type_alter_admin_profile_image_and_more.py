

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminside', '0004_alter_user_gender'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='fit_type',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='admin',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to='adminside/admin_profile_pictures/'),
        ),
        migrations.AlterField(
            model_name='product',
            name='base_image',
            field=models.ImageField(blank=True, null=True, upload_to='products/base'),
        ),
        migrations.AlterField(
            model_name='product_gallery',
            name='image_path',
            field=models.ImageField(blank=True, null=True, upload_to='products/gallery'),
        ),
    ]
