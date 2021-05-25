# Generated by Django 3.1.7 on 2021-05-21 18:09

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_auto_20210521_2106'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='employer_key',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='ref_key',
        ),
        migrations.AlterField(
            model_name='userstat',
            name='time_from',
            field=models.DateTimeField(default=datetime.datetime(2021, 5, 21, 18, 9, 47, 600590, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='userstat',
            name='time_to',
            field=models.DateTimeField(default=datetime.datetime(2021, 5, 21, 18, 9, 47, 600590, tzinfo=utc)),
        ),
    ]