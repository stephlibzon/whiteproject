# Generated by Django 2.1.15 on 2020-07-16 12:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0036_patient_cic_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='patient',
            old_name='cic_id',
            new_name='deident',
        ),
    ]
