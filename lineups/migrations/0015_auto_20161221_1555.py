# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-21 23:55
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lineups', '0014_remove_teamstats_goals_against_per_game_percentage'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gameodds',
            old_name='away_money_line',
            new_name='away_moneyline',
        ),
        migrations.RenameField(
            model_name='gameodds',
            old_name='home_money_line',
            new_name='home_moneyline',
        ),
    ]