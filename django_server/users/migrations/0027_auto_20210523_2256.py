# Generated by Django 3.1.7 on 2021-05-23 19:56

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_auto_20210522_0136'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userstat',
            name='time_from',
            field=models.DateTimeField(default=datetime.datetime(2021, 5, 23, 19, 56, 11, 306626, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='userstat',
            name='time_to',
            field=models.DateTimeField(default=datetime.datetime(2021, 5, 23, 19, 56, 11, 306626, tzinfo=utc)),
        ),
    ]
