# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-20 01:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lineups', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lineup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_weight', models.FloatField()),
                ('total_value', models.FloatField()),
                ('actual_value', models.FloatField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('centre1', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='centre1', to='lineups.PlayerGame')),
                ('centre2', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='centre2', to='lineups.PlayerGame')),
                ('defence1', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='defence1', to='lineups.PlayerGame')),
                ('defence2', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='defence2', to='lineups.PlayerGame')),
                ('goalie', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='goalie', to='lineups.PlayerGame')),
                ('util', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='util', to='lineups.PlayerGame')),
                ('winger1', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='winger1', to='lineups.PlayerGame')),
                ('winger2', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='winger2', to='lineups.PlayerGame')),
                ('winger3', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='winger3', to='lineups.PlayerGame')),
            ],
        ),
    ]
