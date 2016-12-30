from django.contrib import admin

from .models import Team, Player, Game, PlayerGame, Lineup

admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Game)
admin.site.register(PlayerGame)
admin.site.register(Lineup)