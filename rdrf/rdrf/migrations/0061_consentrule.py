# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-01-17 13:07
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('rdrf', '0060_annotation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsentRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('capability', models.CharField(choices=[('see_patient', 'See Patient')], max_length=50)),
                ('consent_question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.ConsentQuestion')),
                ('registry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.Registry')),
                ('user_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Group')),
            ],
        ),
    ]
