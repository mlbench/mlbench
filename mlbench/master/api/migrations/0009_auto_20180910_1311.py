# Generated by Django 2.0.7 on 2018-09-10 13:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_modelrun_finished_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kubepod',
            name='labels',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='kubepod',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='kubepod',
            name='node_name',
            field=models.CharField(max_length=1000),
        ),
    ]
