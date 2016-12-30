from django.db import models
from lineups.managers import PlayerManager


class Team(models.Model):
    name = models.CharField(max_length=200)
    link = models.CharField(max_length=200)
    abbreviation = models.CharField(max_length=10)
    team_name = models.CharField(max_length=200)
    location_name = models.CharField(max_length=200)
    first_year_of_play = models.IntegerField()
    official_site_url = models.CharField(max_length=200)
    division_id = models.IntegerField()
    conference_id = models.IntegerField()
    franchise_id = models.IntegerField()
    short_name = models.CharField(max_length=50)
    active = models.BooleanField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.team_name)


class TeamStats(models.Model):
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    season_id = models.IntegerField()
    games_played = models.IntegerField()
    wins = models.IntegerField()
    ties = models.IntegerField()
    losses = models.IntegerField()
    ot_losses = models.IntegerField()
    points = models.IntegerField()
    reg_plus_ot_wins = models.IntegerField()
    point_pctg = models.FloatField()
    goals_for = models.IntegerField()
    goals_against = models.IntegerField()
    goals_for_per_game = models.FloatField()
    goals_against_per_game = models.FloatField()
    pp_pctg = models.FloatField()
    pk_pctg = models.FloatField()
    shots_for_per_game = models.FloatField()
    shots_against_per_game = models.FloatField()
    faceoff_win_pctg = models.FloatField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, %s, GP W L T OTL: %s %s %s %s %s' % (self.team, self.season, self.games_played, self.wins, self.losses, self.ties, self.ot_losses)


class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.PROTECT, null=True)
    full_name = models.CharField(max_length=200)
    link = models.CharField(max_length=400)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    primary_number = models.CharField(max_length=200, null=True)
    birth_date = models.DateTimeField()
    current_age = models.IntegerField(null=True)
    birth_city = models.CharField(max_length=200)
    birth_state_province = models.CharField(max_length=200, null=True)
    birth_country = models.CharField(max_length=200)
    height = models.CharField(max_length=10)
    weight = models.IntegerField(default=0)
    active = models.BooleanField()
    alternate_captain = models.NullBooleanField(null=True)
    captain = models.NullBooleanField(null=True)
    rookie = models.BooleanField()
    shoots_catches = models.CharField(max_length=10, null=True)
    roster_status = models.CharField(max_length=10)
    primary_position_abbr = models.CharField(max_length=10)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = PlayerManager()

    def __str__(self):
        return '%s' % (self.full_name)


class Game(models.Model):
    game_pk = models.IntegerField(unique=True)
    link = models.CharField(max_length=400)
    game_type = models.CharField(max_length=10)
    season = models.IntegerField()
    game_date = models.DateTimeField()
    status_code = models.IntegerField()
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="away_team")
    away_score = models.IntegerField()
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="home_team")
    home_score = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.game_pk)


class GameOdds(models.Model):
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    # home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="home_team")
    home_moneyline = models.CharField(max_length=50)
    home_probability = models.FloatField()
    # away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="away_team")
    away_moneyline = models.CharField(max_length=50)
    away_probability = models.FloatField()
    number_of_goals = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, home: %s, away: %s' % (self.game, self.home_moneyline, self.away_moneyline)

class PlayerGame(models.Model):
    player = models.ForeignKey(Player, on_delete=models.PROTECT)
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    opponent = models.ForeignKey(Team, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, %s' % (self.player, self.game)


class PlayerGameStats(models.Model):
    player_game = models.ForeignKey(PlayerGame, on_delete=models.PROTECT)
    time_on_ice = models.CharField(max_length=50)
    assists = models.IntegerField()
    goals = models.IntegerField()
    shots = models.IntegerField(default=0)
    hits = models.IntegerField(default=0)
    power_play_goals = models.IntegerField(default=0)
    power_play_assists = models.IntegerField(default=0)
    penalty_minutes = models.CharField(max_length=50, default="0:00")
    faceoff_wins = models.IntegerField(default=0)
    faceoff_taken = models.IntegerField(default=0)
    takeaways = models.IntegerField(default=0)
    giveaways = models.IntegerField(default=0)
    short_handed_goals = models.IntegerField(default=0)
    short_handed_assists = models.IntegerField(default=0)
    blocked = models.IntegerField(default=0)
    plus_minus = models.IntegerField(default=0)
    even_time_on_ice = models.CharField(max_length=50, default="0:00")
    power_play_time_on_ice = models.CharField(max_length=50, default="0:00")
    short_handed_time_on_ice = models.CharField(max_length=50, default="0:00")
    shots_against = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    power_play_saves = models.IntegerField(default=0)
    short_handed_saves = models.IntegerField(default=0)
    even_saves = models.IntegerField(default=0)
    short_handed_shots_against = models.IntegerField(default=0)
    even_shots_against = models.IntegerField(default=0)
    power_play_shots_against = models.IntegerField(default=0)
    decision = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s: (%s, %,s) (goals, assists)' % (self.player_game, self.goals, self.assists)


class PlayerGameExpectedStats(models.Model):
    player_game = models.ForeignKey(PlayerGame, on_delete=models.PROTECT)
    goals = models.FloatField(default=0.0)
    assists = models.FloatField(default=0.0)
    shots_on_goal = models.FloatField(default=0.0)
    blocked_shots = models.FloatField(default=0.0)
    short_handed_points = models.FloatField(default=0.0)
    shootout_goals = models.FloatField(default=0.0)
    hat_tricks = models.FloatField(default=0.0)
    wins = models.FloatField(default=0.0)
    saves = models.FloatField(default=0.0)
    goals_against = models.FloatField(default=0.0)
    shutouts = models.FloatField(default=0.0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s: (%s, %,s) (goals, assists)' % (self.player_game, self.goals, self.assists)


class PlayerGameValues(models.Model):
    player_game = models.ForeignKey(PlayerGame, on_delete=models.PROTECT)
    expected_value = models.FloatField(default=0.0)
    actual_value = models.FloatField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, (%s, %,s) (expected, actual)' % (self.player_game, self.expected_value, self.actual_value)

class PlayerGameStartingGoalies(models.Model):
    player_game = models.ForeignKey(PlayerGame, on_delete=models.PROTECT)
    home_goalie = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="home_goalie", null=True)
    away_goalie = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="away_goalie", null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, (%s, %,s) (home goalie, away goalie)' % (self.player_game, self.home_goalie, self.away_goalie)

class PlayerGameDraftKings(models.Model):
    player_game = models.ForeignKey(PlayerGame, on_delete=models.PROTECT)
    name_and_id = models.CharField(max_length=100)
    id = models.IntegerField()
    salary = models.IntegerField()
    position = models.CharField(max_length=100)
    draft_type = models.CharField(max_length=100)
    date_for_lineup = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, (%s, %s, %,s) (id, position, salary)' % (self.player_game, self.id, self.position, self.salary)


class PlayerLine(models.Model):
    player = models.ForeignKey(Player, on_delete=models.PROTECT)
    line = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, %s' % (self.player, self.line)


class Lineup(models.Model):
    centre1 = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="centre1")
    centre2 = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="centre2")
    winger1 = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="winger1")
    winger2 = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="winger2")
    winger3 = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="winger3")
    defence1 = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="defence1")
    defence2 = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="defence2")
    goalie = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="goalie")
    util = models.ForeignKey(PlayerGame, on_delete=models.PROTECT, related_name="util")
    total_weight = models.FloatField()
    total_value = models.FloatField()
    actual_value = models.FloatField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s, %s, %s, %s, %s, %s, %s, %s, %s, %s' % (
        self.centre1, self.centre2, self.winger1, self.winger2, self.winger3, self.defence1, self.defence2, self.goalie, self.util, self.total_values)
