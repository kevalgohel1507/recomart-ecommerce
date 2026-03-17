from django.db import migrations, models


def populate_vendor_financials(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')

    for order in Order.objects.all().iterator():
        line_total = float(order.total or 0)
        platform_fee = round(line_total * 0.12, 2)
        platform_fee_gst = round(platform_fee * 0.18, 2)
        vendor_profit = round(line_total - platform_fee - platform_fee_gst, 2)

        order.platform_fee = platform_fee
        order.platform_fee_gst = platform_fee_gst
        order.vendor_profit = vendor_profit
        order.save(update_fields=['platform_fee', 'platform_fee_gst', 'vendor_profit'])


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_order_payment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='platform_fee',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='order',
            name='platform_fee_gst',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='order',
            name='vendor_profit',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Packed', 'Packed'), ('Out for Delivery', 'Out for Delivery'), ('Shipped', 'Shipped'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled'), ('Rejected', 'Rejected')], default='Pending', max_length=20),
        ),
        migrations.RunPython(populate_vendor_financials, migrations.RunPython.noop),
    ]
