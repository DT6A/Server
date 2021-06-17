# Generated by Django 3.1.7 on 2021-06-17 15:09

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0041_auto_20210617_1701'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedmessage',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='userstat',
            name='time_from',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='userstat',
            name='time_to',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]