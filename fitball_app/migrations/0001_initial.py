# Generated by Django 3.2.3 on 2021-09-19 19:54

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Devices',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_name', models.CharField(max_length=200)),
                ('display_number', models.IntegerField(default=0)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='media/')),
            ],
        ),
    ]
