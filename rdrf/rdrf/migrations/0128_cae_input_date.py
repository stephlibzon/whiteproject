# Generated by Django 2.1.15 on 2020-06-16 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0127_cae_error_string'),
    ]

    operations = [
        migrations.AddField(
            model_name='customactionexecution',
            name='input_data',
            field=models.TextField(blank=True),
        ),
    ]
