# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-20 10:41
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lineups', '0006_auto_20161220_0239'),
    ]

    operations = [
        migrations.RenameField(
            model_name='playergamestats',
            old_name='power_player_assists',
            new_name='power_play_assists',
        ),
    ]
