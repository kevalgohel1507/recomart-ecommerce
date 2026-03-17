from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0017_bundleproduct_discounted_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="short_description",
            field=models.TextField(blank=True),
        ),
    ]
