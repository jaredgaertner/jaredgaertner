import argparse
import datetime
import json
import logging
import pytz
import re
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Q, Avg
from django.utils import timezone

from lineups.models import Player, PlayerLine, Game, GameOdds, Team, TeamStats, PlayerGame, PlayerGameStats, PlayerGameExpectedStats

from bs4 import BeautifulSoup

logger = logging.getLogger('django')
date_format = "%Y-%m-%d"

class Command(BaseCommand):
    help = 'Updates players, games, and team stats, pass in update as of date in form YYYY-MM-DD (by default yesterday)'

    def add_arguments(self, parser):

        def valid_date(date_string):
            try:
                unaware_start_date = datetime.datetime.strptime(date_string, date_format)
                return pytz.utc.localize(unaware_start_date)
            except ValueError:
                msg = "Not a valid date: '{0}'.".format(date_string)
                raise argparse.ArgumentTypeError(msg)

        default_date = timezone.now() - datetime.timedelta(days=1)
        default_date_string = datetime.datetime.strftime(default_date, date_format)
        parser.add_argument('update_as_of', nargs='?', type=valid_date, default=default_date_string,
                            help='Date to update back to.')

    def handle(self, *args, **options):
        update_as_of = options['update_as_of']
        update_teams()
        update_team_stats("20162017")
        update_games(update_as_of)
        update_game_odds()
        # update_player_game_starting_goalies()
        update_player_line()
        update_player_game(update_as_of)


        # Find point values
        # update_games_draftkings_points(update_as_of)

        # self.stdout.write(self.style.SUCCESS('Successfully updated games as of "%s"' % update_as_of))
        logger.info('Successfully updated games as of ' + str(options['update_as_of']))


def update_teams():
    url = 'https://statsapi.web.nhl.com/api/v1/teams'
    response = urllib.request.urlopen(url).read()
    data = json.loads(response.decode())
    logger.debug(data)
    for team in data['teams']:
        if Team.objects.filter(id=team['id']).exists():
            logger.info("Skipping team ID: " + str(team['id']))
        else:
            try:
                t, created = Team.objects.update_or_create(
                    id=team['id'],
                    defaults={
                        'link': team['link'],
                        'abbreviation': team['abbreviation'],
                        'team_name': team['teamName'],
                        'location_name': team['locationName'],
                        'first_year_of_play': team['firstYearOfPlay'],
                        'official_site_url': team['officialSiteUrl'],
                        'division_id': team['division']['id'],
                        'conference_id': team['conference']['id'],
                        'franchise_id': team['franchise']['franchiseId'],
                        'short_name': team['shortName'],
                        'active': team['active']})

            except Exception as e:
                logger.error("Could not insert the following team:")
                logger.error(team)
                logger.error("Got the following error:")
                logger.error(e)
                # Roll back any change if something goes wrong
                # db.rollback()
                raise e


def update_team_stats(season):
    # Create team data
    url = "http://www.nhl.com/stats/rest/grouped/team/basic/season/teamsummary?cayenneExp=seasonId=" + season + "%20and%20gameTypeId=2"
    response = urllib.request.urlopen(url).read()
    data = json.loads(response.decode())
    logger.info("Updating team stats")
    for team_stat in data['data']:
        try:
            ts, created = TeamStats.objects.update_or_create(
                team_id=team_stat['teamId'],
                defaults={
                    'season_id': team_stat['seasonId'],
                    'games_played': team_stat['gamesPlayed'],
                    'wins': team_stat['wins'],
                    'ties': team_stat['ties'],
                    'losses': team_stat['losses'],
                    'ot_losses': team_stat['otLosses'],
                    'points': team_stat['points'],
                    'reg_plus_ot_wins': team_stat['regPlusOtWins'],
                    'point_pctg': team_stat['pointPctg'],
                    'goals_for': team_stat['goalsFor'],
                    'goals_against': team_stat['goalsAgainst'],
                    'goals_for_per_game': team_stat['goalsForPerGame'],
                    'goals_against_per_game': team_stat['goalsAgainstPerGame'],
                    'pp_pctg': team_stat['ppPctg'],
                    'pk_pctg': team_stat['pkPctg'],
                    'shots_for_per_game': team_stat['shotsForPerGame'],
                    'shots_against_per_game': team_stat['shotsAgainstPerGame'],
                    'faceoff_win_pctg': team_stat['faceoffWinPctg']})
            ts.save()

        except Exception as e:
            logging.error("Could not insert the following team stats:")
            logging.error(team_stat)
            logging.error("Got the following error:")
            # Roll back any change if something goes wrong
            # db.rollback()
            raise e


def update_games(start_date):
    # Update games data
    end_date = timezone.now() + datetime.timedelta(days=1)
    url = 'https://statsapi.web.nhl.com/api/v1/schedule?startDate=' + start_date.strftime(
        "%Y-%m-%d") + '&endDate=' + end_date.strftime("%Y-%m-%d")
    response = urllib.request.urlopen(url).read()
    data = json.loads(response.decode())
    for date in data['dates']:
        for game in date['games']:
            # Only want regular season and playoff games (not all-star (A))
            if game['gameType'] in ['R', 'P']:
                logger.info("Updating game ID: " + str(game['gamePk']))
                try:
                    g, created = Game.objects.update_or_create(
                        game_pk=game['gamePk'],
                        defaults={'link': game['link'],
                                  'game_type': game['gameType'],
                                  'season': game['season'],
                                  'game_date': game['gameDate'],
                                  'status_code': game['status']['statusCode'],
                                  'away_team_id': game['teams']['away']['team']['id'],
                                  'away_score': game['teams']['away']['score'],
                                  'home_team_id': game['teams']['home']['team']['id'],
                                  'home_score': game['teams']['home']['score']})

                except Exception as e:
                    logger.error("Could not insert the following game:")
                    logger.error(game)
                    logger.error("Got the following error:")
                    logger.error(e)
                    # Roll back any change if something goes wrong
                    # db.rollback()
                    raise e


def update_player_game(update_date):
    # Create player stats data
    # Loop through all games in DB where game date gte update date
    for game in Game.objects.filter(game_date__gte=update_date).order_by('game_pk'):
        game_pk = game.game_pk
        url = 'https://statsapi.web.nhl.com/api/v1/game/' + str(game_pk) + '/feed/live'
        response = urllib.request.urlopen(url).read()
        gameJSON = json.loads(response.decode())

        if gameJSON['gameData']['status']['statusCode'] != "7":  # Game isn't final, skip
            logger.info("Game not finished, updating expected stats for game ID: " + str(game_pk))
            update_player_game_expected_stats(game)
        else:
            logger.info("Updating player stats for game ID: " + str(game_pk))
            update_player_game_stats(gameJSON, game)


def update_player_game_stats(gameJSON, game):
    awayTeamId = gameJSON['liveData']['boxscore']['teams']['away']['team']['id']
    homeTeamId = gameJSON['liveData']['boxscore']['teams']['home']['team']['id']
    try:
        for playerIndex in gameJSON['liveData']['boxscore']['teams']['away']['players']:
            playerJSON = gameJSON['liveData']['boxscore']['teams']['away']['players'][playerIndex]
            position = playerJSON['position']['abbreviation']

            player = Player.objects.update_player(playerJSON['person']['id'])
            playerGame = PlayerGame(player=player, game=game,
                                    opponent=Team.objects.get(pk=homeTeamId))
            playerGame.save()
            if position in ['RW', 'LW', 'C', 'D']:
                update_skater_stats(playerJSON, playerGame)

            elif position == 'G':
                update_goalie_stats(playerJSON, playerGame)

            else:
                # raise ValueError("Invalid position.")
                logger.debug(
                    "Skipping player ID (most likely did not play): " + str(playerJSON['person']['id']))

        for playerIndex in gameJSON['liveData']['boxscore']['teams']['home']['players']:
            playerJSON = gameJSON['liveData']['boxscore']['teams']['home']['players'][playerIndex]
            position = playerJSON['position']['abbreviation']

            player = Player.objects.update_player(playerJSON['person']['id'])
            playerGame = PlayerGame(player=player, game=game,
                                    opponent=Team.objects.get(pk=awayTeamId))
            playerGame.save()
            if position in ['RW', 'LW', 'C', 'D']:
                update_skater_stats(playerJSON, playerGame)

            elif position == 'G':
                update_goalie_stats(playerJSON, playerGame)
            else:
                # raise ValueError("Invalid position.")
                logger.debug(
                    "Skipping player ID (most likely did not play): " + str(playerJSON['person']['id']))

    except Exception as e:
        logger.error("Could not insert the following player stats:")
        logger.error(playerJSON)
        logger.error("Game PK: " + str(game.game_pk))
        logger.error("Got the following error:")
        logger.error(e)
        # Roll back any change if something goes wrong
        # db.rollback()
        raise e


def update_skater_stats(playerJSON, playerGame):
    pgs = PlayerGameStats(player_game=playerGame,
                          time_on_ice=playerJSON['stats']['skaterStats']['timeOnIce'],
                          assists=playerJSON['stats']['skaterStats']['assists'],
                          goals=playerJSON['stats']['skaterStats']['goals'],
                          shots=playerJSON['stats']['skaterStats']['shots'],
                          hits=playerJSON['stats']['skaterStats']['hits'],
                          power_play_goals=playerJSON['stats']['skaterStats']['powerPlayGoals'],
                          power_play_assists=playerJSON['stats']['skaterStats']['powerPlayAssists'],
                          penalty_minutes=playerJSON['stats']['skaterStats']['penaltyMinutes'],
                          faceoff_wins=playerJSON['stats']['skaterStats']['faceOffWins'],
                          faceoff_taken=playerJSON['stats']['skaterStats']['faceoffTaken'],
                          takeaways=playerJSON['stats']['skaterStats']['takeaways'],
                          giveaways=playerJSON['stats']['skaterStats']['giveaways'],
                          short_handed_goals=playerJSON['stats']['skaterStats']['shortHandedGoals'],
                          short_handed_assists=playerJSON['stats']['skaterStats']['shortHandedAssists'],
                          blocked=playerJSON['stats']['skaterStats']['blocked'],
                          plus_minus=playerJSON['stats']['skaterStats']['plusMinus'],
                          even_time_on_ice=playerJSON['stats']['skaterStats']['evenTimeOnIce'],
                          power_play_time_on_ice=playerJSON['stats']['skaterStats'][
                              'powerPlayTimeOnIce'],
                          short_handed_time_on_ice=playerJSON['stats']['skaterStats'][
                              'shortHandedTimeOnIce'])
    pgs.save()


def update_skater_expected_stats(playerGame, average_goals_against_for_league):
    expected_stats = get_expected_skater_stats(playerGame)

    try:
        goals = expected_stats['goals']
        assists = expected_stats['assists']

        # Get opponent goals against
        opponent_stats = TeamStats.objects.get(team_id=playerGame.opponent_id)
        goals_against_percentage = opponent_stats.goals_against_per_game / average_goals_against_for_league
        goals *= goals_against_percentage
        assists *= goals_against_percentage

        PlayerGameExpectedStats.objects.update_or_create(player_game_id=playerGame.id,
                                                         defaults={
                                                             'goals': goals,
                                                             'assists': assists,
                                                             'shots_on_goal': expected_stats['shots_on_goal'],
                                                             'blocked_shots': expected_stats['blocked_shots'],
                                                             'short_handed_points': expected_stats['short_handed_points'],
                                                             'shootout_goals': expected_stats['shootout_goals'],
                                                             'hat_tricks': expected_stats['hat_tricks'],
                                                             'wins': 0,
                                                             'saves': 0,
                                                             'goals_against': 0,
                                                             'shutouts': 0
                                                         })
    except Exception as e:
        logging.error("Could not update expected stats.")
        logging.error("Got the following error:")
        logging.error(e)
        # Roll back any change if something goes wrong
        # db.rollback()
        raise e


def update_goalie_stats(playerJSON, playerGame):
    pgs = PlayerGameStats(player_game=playerGame,
                          time_on_ice=playerJSON['stats']['goalieStats']['timeOnIce'],
                          assists=playerJSON['stats']['goalieStats']['assists'],
                          goals=playerJSON['stats']['goalieStats']['goals'],
                          penalty_minutes=playerJSON['stats']['goalieStats']['pim'],
                          shots_against=playerJSON['stats']['goalieStats']['shots'],
                          saves=playerJSON['stats']['goalieStats']['saves'],
                          power_play_saves=playerJSON['stats']['goalieStats']['powerPlaySaves'],
                          short_handed_saves=playerJSON['stats']['goalieStats']['shortHandedSaves'],
                          even_saves=playerJSON['stats']['goalieStats']['evenSaves'],
                          short_handed_shots_against=playerJSON['stats']['goalieStats'][
                              'shortHandedShotsAgainst'],
                          even_shots_against=playerJSON['stats']['goalieStats']['evenShotsAgainst'],
                          power_play_shots_against=playerJSON['stats']['goalieStats'][
                              'powerPlayShotsAgainst'],
                          decision=playerJSON['stats']['goalieStats']['decision'])
    pgs.save()


def update_goalie_expected_stats(playerGame):
    expected_stats = get_expected_goalie_stats(playerGame)
    try:
        goals = expected_stats['goals']
        assists = expected_stats['assists']

        # Get vegas odds to see how likely a win is for goalies
        # TODO: add to this to find expected number of goals and goals against
        if playerGame.game.game_pk != None:
            for game_odds in GameOdds.objects.filter(game_id=playerGame.game_id):
                if game_odds.game.home_team_id == playerGame.player.team_id:
                    expected_stats['wins'] = game_odds.home_probability
                elif game_odds.game.away_team_id == playerGame.player.team_id:
                    expected_stats['wins'] = game_odds.away_probability
                    # else:
                    #     logging.info(game_odds)
                    #     logging.info(playerGame.get_game_pk())
                    #     logging.info(playerGame)
                    #     raise ValueError("Neither team matched for the given gamePk.")

        PlayerGameExpectedStats.objects.update_or_create(player_game_id=playerGame.id,
                                                         defaults={
                                                             'goals': goals,
                                                             'assists': assists,
                                                             'shots_on_goal': 0,
                                                             'blocked_shots': 0,
                                                             'short_handed_points': 0,
                                                             'shootout_goals': 0,
                                                             'hat_tricks': 0,
                                                             'wins': expected_stats['wins'],
                                                             'saves': expected_stats['saves'],
                                                             'goals_against': expected_stats['goals_against'],
                                                             'shutouts': expected_stats['shutouts']
                                                         })
    except Exception as e:
        logging.error("Could not update expected stats.")
        logging.error("Got the following error:")
        logging.error(e)
        # Roll back any change if something goes wrong
        # db.rollback()
        raise e


# def update_player_game_starting_goalies():
#     starting_goalies = []
#     try:
#         logging.info("Finding starting goalies...")
#         url = "http://www2.dailyfaceoff.com/starting-goalies/" + str(timezone.now().year) + "/" + str(
#             timezone.now().month) + "/" + str(timezone.now().day) + "/"
#         soup = BeautifulSoup(urllib.request.urlopen(url).read(), "html.parser")
#         # matchups = soup.find(id="matchups")
#         for row in soup.find_all("div", "goalie"):
#             if row.find("h5") != None:
#                 goalie_name = row.h5.a.string
#                 logging.info("Adding goalie: " + str(goalie_name))
#                 status = row.dl.dt.string
#                 logging.info("Status: " + str(status))
#
#                 starting_goalies.append(goalie_name)
#
#             # Not currently needed, as only shows goalies which aren't confirmed
#             # Else, we need to look at the document.write statement
#             else:
#                 match = re.search(r"document\.write\(\"(.+)\"\)", str(row))
#                 goalie_info = BeautifulSoup(match.group(1), "html.parser")
#                 goalie_name = goalie_info.h5.a.string
#                 logging.info("Not adding goalie: " + str(goalie_name))
#                 status = goalie_info.dl.dt.string
#                 logging.info("Status: " + str(status))
#                 # starting_goalies.append(goalie_name)
#
#         return starting_goalies
#
#     except Exception as e:
#         logging.error("Could not connect to dailyfaceoff to get starting goalies.")
#         logging.error("Got the following error:")
#         logging.error(e)
#         # Roll back any change if something goes wrong
#         # db.rollback()
#         raise e


def update_player_line(force_update=False):
    try:
        # Check if we've updated in the last 12 hours
        twelve_hours_ago = timezone.now() - datetime.timedelta(hours=12)
        if PlayerLine.objects.filter(updated__gte=twelve_hours_ago).exists() and force_update != True:
            logging.info("Skipping updating lineup combinations, recently updated....")
        else:
            logging.info("Finding line combinations...")
            url = "http://www2.dailyfaceoff.com/teams"
            soup = BeautifulSoup(urllib.request.urlopen(url).read(), "html.parser")
            teams = soup.find(id="matchups_container")
            for team in teams.find_all("a"):
                url = team.get("href")
                if url.startswith("/teams"):
                    url = "http://www2.dailyfaceoff.com" + team.get("href")
                    soup = BeautifulSoup(urllib.request.urlopen(url).read(), "html.parser")
                    lineups = soup.find(id="matchups_container")
                    for td in lineups.find_all("td"):
                        logging.debug(td)
                        # Going to ignore powerplay lineups for now
                        position = td.get("id")
                        logging.debug(position)
                        if position.startswith(("C", "LW", "RW", "LD", "RD", "G", "IR")) and td.a != None:
                            playerName = td.a.img.get("alt")
                            logging.info("Setting " + str(playerName) + " to " + position)
                            player = Player.objects.update_player(playerName)
                            pl = PlayerLine(player=player.id, line=position)
                            pl.save()
                        else:
                            logging.debug("ignoring..." + str(position))


    except Exception as e:
        logging.error(
            "Could not connect to dailyfaceoff to get lineup combinations or failed to add to database.")
        logging.error("Got the following error:")
        logging.error(e)
        raise e


def get_implied_probability(american_odds):
    if american_odds < 0:
        positive_odds = -american_odds
        return (positive_odds) / (positive_odds + 100)
    else:
        return 100 / (american_odds + 100)

def update_game_odds():
    try:
        # Use Vegas Insider
        url = "http://www.vegasinsider.com/nhl/odds/las-vegas/"
        soup = BeautifulSoup(urllib.request.urlopen(url).read(), "lxml")
        table = soup.find('table', attrs={'class': 'frodds-data-tbl'})
        rows = table.find_all('tr')
        for i in range(len(rows)):
            # Skip every other row (contains TV info)
            if i % 2 != 0:
                continue

            cols = rows[i].find_all('td')
            teams = cols[0].find_all('a')
            if len(teams) == 0:
                continue

            away_team = teams[0].string
            home_team = teams[1].string
            vi_concensus = cols[2].a

            # Skip if the odds aren't up yet
            if vi_concensus == None:
                continue
            else:
                # Find first moneyline, as second contains odds for 1st period
                vi_concensus_info = vi_concensus.contents
                home_moneyline = vi_concensus_info[4].strip()
                home_ip = get_implied_probability(int(home_moneyline))
                visiting_moneyline = vi_concensus_info[2].strip()
                visiting_ip = get_implied_probability(int(visiting_moneyline))
                total_p = home_ip + visiting_ip
                home_p = home_ip / total_p
                visiting_p = visiting_ip / total_p

                # Find first total, as second contains odds for 1st period
                total_points = vi_concensus.contents[0].strip()
                # over_adjust = event.periods.period.total.over_adjust.string
                # under_adjust = event.periods.period.total.under_adjust.string
                home_team_id = Team.objects.get_team_id_by_city(home_team)
                away_team_id = Team.objects.get_team_id_by_city(away_team)
                game_pk = Game.objects.get_game_pk_by_ids(home_team_id, away_team_id)

                logging.debug("Away team: " + away_team)
                logging.debug("Home team: " + home_team)
                logging.debug("Home moneyline: " + home_moneyline)
                logging.debug("Visiting moneyline: " + visiting_moneyline)
                logging.debug("Home probability: " + str(home_p))
                logging.debug("Visiting probability: " + str(visiting_p))
                logging.debug("Total points (goals): " + str(total_points))
                # logging.info(over_adjust)
                # logging.info(under_adjust)
                logging.debug("Away team ID: " + str(away_team_id))
                logging.debug("Home team ID: " + str(home_team_id))
                logging.debug("GamePK: " + str(game_pk))

                go = GameOdds(game=Game.objects.get(game_pk=game_pk), home_moneyline=home_moneyline,
                              home_probability=home_p, away_moneyline=visiting_moneyline, away_probability=visiting_p,
                              number_of_goals=total_points)
                go.save()

    except Exception as e:
        logging.error("Could not find odds")
        logging.error("Got the following error:")
        logging.error(e)
        raise e


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
        ]


def get_expected_skater_stats(playerGame):
    skater_stats = {"goals": 0,
                    "assists": 0,
                    "shots_on_goal": 0,
                    "blocked_shots": 0,
                    "short_handed_points": 0,
                    "shootout_goals": 0,
                    "hat_tricks": 0}

    # if playerGame.get_primary_position() == "G":
    #     return skater_stats

    try:
        logging.debug("Getting player value for " + str(playerGame.player_id))
        # Find average points for last week and for the year
        with connection.cursor() as cursor:
            cursor.execute('''select coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.goals else null end),0) AS average_goals_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.goals else null end),0) AS average_goals_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.goals else null end),0) AS average_goals_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.assists else null end),0) AS average_assists_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.assists else null end),0) AS average_assists_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.assists else null end),0) AS average_assists_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.shots else null end),0) AS average_shots_on_goal_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.shots else null end),0) AS average_shots_on_goal_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.shots else null end),0) AS average_shots_on_goal_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.blocked else null end),0) AS average_blocked_shots_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.blocked else null end),0) AS average_blocked_shots_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.blocked else null end),0) AS average_blocked_shots_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.short_handed_goals + pgs.short_handed_assists else null end),0) AS average_short_handed_points_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.short_handed_goals + pgs.short_handed_assists else null end),0) AS average_short_handed_points_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.short_handed_goals + pgs.short_handed_assists else null end),0) AS average_short_handed_points_last_two_weeks,
                0 average_shootout_goals_last_year,
                0 average_shootout_goals_this_year,
                0 average_shootout_goals_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then (case when pgs.goals >= 3 then 1 else 0 end) else null end),0) AS average_hat_tricks_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then (case when pgs.goals >= 3 then 1 else 0 end) else null end),0) AS average_hat_tricks_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then (case when pgs.goals >= 3 then 1 else 0 end) else null end),0) AS average_hat_tricks_last_two_weeks,
                count(case when g.game_pk between 2015020001 and 2015039999 then 1 else null end) as games_last_year,
                count(case when g.game_pk between 2016020001 and 2016039999 then 1 else null end) as games_this_year,
                count(case when g.game_date > localtimestamp - interval '14 days' then 1 else null end) AS games_last_two_weeks
            from lineups_playergamestats pgs
            inner join lineups_playergame pg
            on pgs.player_game_id = pg.id
            inner join lineups_game g
            on pg.game_id = g.id
            where pg.player_id = %s and
                (g.game_pk between 2015020001 and 2016039999)''', [playerGame.player_id])

            value = 0
            for player_stats in dictfetchall(cursor):
                # Calculate value (ignore players that haven't played a game this year)
                if player_stats['games_this_year'] != 0:
                    # Calculate total games (will be over one due to last two weeks, but want to find the ratio for each stat)
                    total_games = player_stats['games_last_year'] + player_stats['games_this_year'] + player_stats[
                        'games_last_two_weeks']
                    games_last_year_ratio = player_stats['games_last_year'] / total_games
                    games_this_year_ratio = player_stats['games_this_year'] / total_games
                    games_last_two_weeks_ratio = player_stats['games_last_two_weeks'] / total_games
                    logging.debug("Total games last year is " + str(player_stats['games_last_year']))
                    logging.debug("Total games this year is " + str(player_stats['games_this_year']))
                    logging.debug("Total games last two weeks is " + str(player_stats['games_last_two_weeks']))

                    # Loop through and get an adjusted value based on each time interval
                    for key, value in skater_stats.items():
                        skater_stats[key] = games_last_year_ratio * float(
                            player_stats['average_' + key + '_last_year']) + games_this_year_ratio * float(
                            player_stats['average_' + key + '_this_year']) + games_last_two_weeks_ratio * float(
                            player_stats['average_' + key + '_last_two_weeks'])
                        logging.debug("For player id " + str(playerGame.player_id) + ": " + key + " = " + str(skater_stats[key]) + "")

            return skater_stats

    except Exception as e:
        logging.error("Could not get skater expected stats.")
        logging.error("Got the following error:")
        logging.error(e)
        # Roll back any change if something goes wrong
        # db.rollback()
        raise e


def get_expected_goalie_stats(playerGame):
    goalie_stats = {"wins": 0,
                    "saves": 0,
                    "goals_against": 0,
                    "shutouts": 0,
                    "goals": 0,
                    "assists": 0}

    try:
        logging.debug("Getting player value for " + str(playerGame.player_id))
        # Find average points for last week and for the year
        with connection.cursor() as cursor:
            cursor.execute('''select coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then (case when pgs.decision = 'W' then 1 else 0 end) else null end),0) AS average_wins_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then (case when pgs.decision = 'W' then 1 else 0 end) else null end),0) AS average_wins_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then (case when pgs.decision = 'W' then 1 else 0 end) else null end),0) AS average_wins_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.saves else null end),0) AS average_saves_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.saves else null end),0) AS average_saves_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.saves else null end),0) AS average_saves_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.shots_against - pgs.saves else null end),0) AS average_goals_against_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.shots_against - pgs.saves else null end),0) AS average_goals_against_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.shots_against - pgs.saves else null end),0) AS average_goals_against_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then (case when pgs.decision = 'W' and pgs.shots_against = pgs.saves and pgs.time_on_ice > '59:30' then 1 else 0 end) else null end),0) AS average_shutouts_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then (case when pgs.decision = 'W' and pgs.shots_against = pgs.saves and pgs.time_on_ice > '59:30' then 1 else 0 end) else null end),0) AS average_shutouts_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then (case when pgs.decision = 'W' and pgs.shots_against = pgs.saves and pgs.time_on_ice > '59:30' then 1 else 0 end) else null end),0) AS average_shutouts_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.goals else null end),0) AS average_goals_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.goals else null end),0) AS average_goals_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.goals else null end),0) AS average_goals_last_two_weeks,
                coalesce(avg(case when g.game_pk between 2015020001 and 2015039999 then pgs.assists else null end),0) AS average_assists_last_year,
                coalesce(avg(case when g.game_pk between 2016020001 and 2016039999 then pgs.assists else null end),0) AS average_assists_this_year,
                coalesce(avg(case when g.game_date > localtimestamp - interval '14 days' then pgs.assists else null end),0) AS average_assists_last_two_weeks,
                count(case when g.game_pk between 2015020001 and 2015039999 then 1 else null end) as games_last_year,
                count(case when g.game_pk between 2016020001 and 2016039999 then 1 else null end) as games_this_year,
                count(case when g.game_date > localtimestamp - interval '14 days' then 1 else null end) AS games_last_two_weeks
            from lineups_playergamestats pgs
            inner join lineups_playergame pg
            on pgs.player_game_id = pg.id
            inner join lineups_game g
            on pg.game_id = g.id
            where pg.player_id = %s and
                (g.game_pk between 2015020001 and 2016039999)''', [playerGame.player_id])

            value = 0
            for player_stats in dictfetchall(cursor):
                # Calculate value (ignore players that haven't played a game this year)
                if player_stats['games_this_year'] != 0:
                    # Calculate total games (will be over one due to last two weeks, but want to find the ratio for each stat)
                    total_games = player_stats['games_last_year'] + player_stats['games_this_year'] + player_stats[
                        'games_last_two_weeks']
                    games_last_year_ratio = player_stats['games_last_year'] / total_games
                    games_this_year_ratio = player_stats['games_this_year'] / total_games
                    games_last_two_weeks_ratio = player_stats['games_last_two_weeks'] / total_games
                    logging.debug("Total games last year is " + str(player_stats['games_last_year']))
                    logging.debug("Total games this year is " + str(player_stats['games_this_year']))
                    logging.debug("Total games last two weeks is " + str(player_stats['games_last_two_weeks']))

                    # Loop through and get an adjusted value based on each time interval
                    for key, value in goalie_stats.items():
                        goalie_stats[key] = games_last_year_ratio * float(player_stats['average_' + key + '_last_year']) + \
                                            games_this_year_ratio * float(player_stats['average_' + key + '_this_year']) + \
                                            games_last_two_weeks_ratio * float(player_stats['average_' + key + '_last_two_weeks'])
                        logging.debug("For player id " + str(playerGame.player_id) + ": " + key + " = " + str(goalie_stats[key]) + "")

            return goalie_stats

    except Exception as e:
        logging.error("Could not get goalie expected stats.")
        logging.error("Got the following error:")
        logging.error(e)
        # Roll back any change if something goes wrong
        # db.rollback()
        raise e

    return goalie_stats


def get_average_goals_against_for_league():
    return TeamStats.objects.aggregate(Avg('goals_against_per_game'))['goals_against_per_game__avg']


def update_player_game_expected_stats(game):
    try:
        # Get average gaa for league to adjust stats based on opponent for skaters
        average_goals_against_for_league = get_average_goals_against_for_league()

        # Find all players on the home team
        for player in Player.objects.filter(team_id=game.home_team_id, active=True):
            playerGame = PlayerGame(player=player, game=game, opponent_id=game.away_team_id)
            playerGame.save()
            if player.primary_position_abbr in ['RW', 'LW', 'C', 'D']:
                update_skater_expected_stats(playerGame, average_goals_against_for_league)
            elif player.primary_position_abbr == 'G':
                update_goalie_expected_stats(playerGame)
            else:
                # raise ValueError("Invalid position.")
                logger.debug("Skipping player ID (unknown position): " + str(player))

        # Find all players on the away team
        for player in Player.objects.filter(team_id=game.away_team_id, active=True):
            playerGame = PlayerGame(player=player, game=game, opponent_id=game.home_team_id)
            playerGame.save()
            if player.primary_position_abbr in ['RW', 'LW', 'C', 'D']:
                update_skater_expected_stats(playerGame, average_goals_against_for_league)
            elif player.primary_position_abbr == 'G':
                update_goalie_expected_stats(playerGame)
            else:
                # raise ValueError("Invalid position.")
                logger.debug("Skipping player ID (unknown position): " + str(player))

    except Exception as e:
        logging.error("Could not update expected stats for game " + str(game))
        logging.error("Got the following error:")
        logging.error(e)
        raise e

# def update_games_draftkings_points(db, update_date):
#     # Draftkings point system:
#     # Players will accumulate points as follows:
#     #     Goal = +3 PTS
#     #     Assist = +2 PTS
#     #     Shot on Goal = +0.5 PTS
#     #     Blocked Shot = +0.5 PTS
#     #     Short Handed Point Bonus (Goal/Assist) = +1 PTS
#     #     Shootout Goal = +0.2 PTS
#     #     Hat Trick Bonus = +1.5 PTS
#     #
#     # Goalies only will accumulate points as follows:
#     #     Win = +3 PTS
#     #     Save = +0.2 PTS
#     #     Goal Against = -1 PTS
#     #     Shutout Bonus = +2 PTS
#     #     Goalie Scoring Notes:
#     #     Goalies WILL receive points for all stats they accrue, including goals and assists.
#     #     The Goalie Shutout Bonus is credited to goalies if they complete the entire game with 0 goals allowed in regulation + overtime. Shootout goals will not prevent a shutout. Goalie must complete the entire game to get credit for a shutout.
#
#     # Create points data
#     # Player stats
#     db.query('''SELECT gpss.*
#                 FROM games g
#                 LEFT JOIN player_games_skater_stats gpss ON g.gamePk = gpss.gamePk
#                 WHERE g.gameDate > ?''', (update_date,))
#     for player_stats in db.fetchall():
#         try:
#             gamePk = player_stats['gamePk']
#             playerId = player_stats['playerId']
#             points = player_stats["goals"] * 3 + player_stats["assists"] * 2 + player_stats["shots"] * 0.5 + \
#                      player_stats["blocked"] * 0.5 + player_stats["shortHandedGoals"] + player_stats[
#                          "shortHandedAssists"]  # + player_stats["Shootout"] * 0.2
#             if player_stats["goals"] >= 3:
#                 points += 1.5
#
#             logger.info("Updating player " + str(playerId) + " draftkings stats for game ID: " + str(gamePk))
#             db.query('''INSERT or REPLACE INTO games_draftkings_points
#                      (gamePk,
#                       playerId,
#                       points) VALUES(?,?,?)''', (gamePk, playerId, points))
#
#         except Exception as e:
#             logger.error("Could not insert the following player points for DraftKings:")
#             logger.error(player_stats)
#             logger.error("Got the following error:")
#             logger.error(e)
#             # Roll back any change if something goes wrong
#             # db.rollback()
#             # raise e
#
#     # Goalie stats
#     db.query('''SELECT gpgs.*
#                 FROM games g
#                 LEFT JOIN player_games_goalie_stats gpgs ON g.gamePk = gpgs.gamePk
#                 WHERE g.gameDate > ?''', (update_date,))
#     for goalie_stats in db.fetchall():
#         try:
#             gamePk = goalie_stats['gamePk']
#             playerId = goalie_stats['playerId']
#
#             goals_against = (goalie_stats["shots"] - goalie_stats["saves"])
#             points = goalie_stats["saves"] * 0.2 - goals_against + goalie_stats["goals"] * 3 + goalie_stats[
#                                                                                                    "assists"] * 2
#             if goalie_stats["decision"] == "W":
#                 points += 3
#
#             if goals_against == 0:
#                 # check time on ice as well, needs to be the entire game
#                 # Accounts for cases where the goalie is pulled (delayed penalty)
#                 #  by not being quite 60 minutes
#                 # TODO: Fix this up, not quite correct, needs to check game length
#                 min, seconds = [int(i) for i in goalie_stats["timeOnIce"].split(':')]
#                 if (min * 60 + seconds) > 3550:
#                     points += 2
#
#             db.query('''INSERT or REPLACE INTO games_draftkings_points
#                      (gamePk,
#                       playerId,
#                       points) VALUES(?,?,?)''', (gamePk, playerId, points))
#
#         except Exception as e:
#             logger.error("Could not insert the following goalie points for DraftKings:")
#             logger.error(goalie_stats)
#             logger.error("Got the following error:")
#             logger.error(e)
#             # Roll back any change if something goes wrong
#             # db.rollback()
#             # raise e
#
#
# def get_player_id_by_name(db, playerName):
#     try:
#         db.query("select p.id from players p where p.fullName = ?", (playerName,))
#         for player in db.fetchall():
#             return player['id']
#
#             # Couldn't find the player, try their last name only
#             # db.query("select p.id from players p where lower(p.lastName) = lower(?)", (playerName.split()[1],))
#             # for player in db.fetchall():
#             #     return player['id']
#
#     except Exception as e:
#         logger.error("Could not find player ID for " + playerName)
#         logger.error("Got the following error:")
#         logger.error(e)
#         raise e
