# Generated by Django 2.1.5 on 2019-03-28 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0100_auto_20190328_1300'),
    ]

    operations = [
        migrations.AddField(
            model_name='reviewitem',
            name='category',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
    ]
