from django.db import migrations, models


def add_discounted_price_column(apps, schema_editor):
    table_name = "products_bundle_products"
    connection = schema_editor.connection

    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)

    existing_cols = [col.name if hasattr(col, "name") else col[0] for col in description]
    if "discounted_price" in existing_cols:
        return

    quoted_table = schema_editor.quote_name(table_name)
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {quoted_table} ADD COLUMN discounted_price NUMERIC(10,2)")


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0016_smart_search_query"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_discounted_price_column, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="BundleProduct",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("discounted_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        (
                            "bundle",
                            models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="bundle_items", to="products.bundle"),
                        ),
                        (
                            "product",
                            models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="bundle_items", to="products.product"),
                        ),
                    ],
                    options={
                        "db_table": "products_bundle_products",
                        "unique_together": {("bundle", "product")},
                    },
                ),
                migrations.AlterField(
                    model_name="bundle",
                    name="products",
                    field=models.ManyToManyField(related_name="bundles", through="products.BundleProduct", to="products.product"),
                ),
            ],
        ),
    ]
