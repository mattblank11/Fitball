# Generated by Django 3.2.3 on 2021-09-21 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitball_app', '0016_alter_discord_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='goal',
            name='goal_category',
            field=models.CharField(default=1, max_length=200),
            preserve_default=False,
        ),
    ]
