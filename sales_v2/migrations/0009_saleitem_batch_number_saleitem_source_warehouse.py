from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse_v2', '0001_initial'),
        ('sales_v2', '0008_alter_invoice_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='batch_number',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='saleitem',
            name='source_warehouse',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='warehouse_v2.warehouse'),
        ),
    ]
