# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-23 09:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lineups', '0016_auto_20161221_1556'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerGameStartingGoalies',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('away_goalie', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='away_goalie', to='lineups.Player')),
                ('home_goalie', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='home_goalie', to='lineups.Player')),
                ('player_game', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lineups.PlayerGame')),
            ],
        ),
    ]
