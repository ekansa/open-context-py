# Generated by Django 3.0.8 on 2020-10-27 23:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('all_items', '0001_initial'),
        ('importer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasourcefield',
            name='context',
            field=models.ForeignKey(db_column='context_uuid', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='all_items.AllManifest'),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='is_current',
            field=models.BooleanField(default=True),
        ),
    ]