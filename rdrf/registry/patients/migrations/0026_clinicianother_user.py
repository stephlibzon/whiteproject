# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-01-12 11:46
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('patients', '0025_auto_20171025_1256'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinicianother',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
