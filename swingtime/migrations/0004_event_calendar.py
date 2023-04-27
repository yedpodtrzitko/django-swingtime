# Generated by Django 4.2 on 2023-04-26 15:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("swingtime", "0003_auto_20230426_1506"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="group",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="swingtime.eventgroup",
            ),
            preserve_default=False,
        ),
    ]
