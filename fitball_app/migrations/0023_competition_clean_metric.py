# Generated by Django 3.2.3 on 2021-10-19 19:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitball_app', '0022_auto_20211013_0055'),
    ]

    operations = [
        migrations.AddField(
            model_name='competition',
            name='clean_metric',
            field=models.CharField(default='Metric', max_length=200),
            preserve_default=False,
        ),
    ]
