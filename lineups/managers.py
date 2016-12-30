import datetime
import json
import logging
import pytz
import urllib.request

from django.db import models
from django.db.models import Q

logger = logging.getLogger('django')
date_format = "%Y-%m-%d"


class PlayerManager(models.Manager):
    def update_player(self, playerName, force_update=False):
        playerId = self.get_player_id_by_name(playerName)
        # TODO: Check into any potential player updates
        if self.model.objects.filter(id=playerId).exists() and force_update != True:
            logger.debug("Skipping player ID: " + str(playerId))
            return self.get(pk=playerId)
        else:
            try:
                logger.info("Updating player ID: " + str(playerId))
                url = 'https://statsapi.web.nhl.com/api/v1/people/' + str(playerId)
                response = urllib.request.urlopen(url).read()
                data = json.loads(response.decode())

                for player in data['people']:

                    try:
                        if "currentTeam" in player:
                            currentTeamId = player['currentTeam']['id']
                        else:
                            currentTeamId = None

                        if "primaryNumber" in player:
                            primaryNumber = player['primaryNumber']
                        else:
                            primaryNumber = None

                        if "currentAge" in player:
                            currentAge = player['currentAge']
                        else:
                            currentAge = None

                        if "birthStateProvince" in player:
                            birthStateProvince = player['birthStateProvince']
                        else:
                            birthStateProvince = None

                        if "alternateCaptain" in player:
                            alternateCaptain = player['alternateCaptain']
                        else:
                            alternateCaptain = None

                        if "captain" in player:
                            captain = player['captain']
                        # Roll back any change if something goes wrong
                        else:
                            captain = None

                        if "shootsCatches" in player:
                            shootsCatches = player['shootsCatches']
                        else:
                            shootsCatches = None

                        unaware_birth_date = datetime.datetime.strptime(player['birthDate'], date_format)
                        birth_date = pytz.utc.localize(unaware_birth_date)

                        p, created = self.update_or_create(id=playerId, defaults={
                            'full_name': player['fullName'],
                            'link': player['link'],
                            'first_name': player['firstName'],
                            'last_name': player['lastName'],
                            'primary_number': primaryNumber,
                            'birth_date': birth_date,
                            'current_age': currentAge,
                            'birth_city': player['birthCity'],
                            'birth_state_province': birthStateProvince,
                            'birth_country': player['birthCountry'],
                            'height': player['height'],
                            'weight': player['weight'],
                            'active': player['active'],
                            'alternate_captain': alternateCaptain,
                            'captain': captain,
                            'rookie': player['rookie'],
                            'shoots_catches': shootsCatches,
                            'roster_status': player['rosterStatus'],
                            'team_id': currentTeamId,
                            'primary_position_abbr': player['primaryPosition'][
                                'abbreviation']})
                        return p

                    except Exception as e:
                        logger.error("Could not insert the following player stats:")
                        logger.error(player)
                        logger.error("Got the following error:")
                        logger.error(e)
                        # db.rollback()
                        raise e

            except Exception as e:
                logger.error("Could not connect to player API:")
                logger.error("Got the following error:")
                logger.error(e)
                # Roll back any change if something goes wrong
                # db.rollback()
                raise e

    def get_player_id_by_name(self, playerName):
        try:
            for player in self.model.objects.filter(full_name=playerName):
                return player.id

            # Couldn't find the player, use the NHL suggest search
            lastName = playerName.split(None, 1)[1].strip()
            firstName = playerName.split(None, 1)[0].strip()
            logging.info("Searching for player ID by name using NHL suggest link for " + firstName + " " + lastName)

            # Search by last name, then first name for all suggestions if more than one
            url = "https://suggest.svc.nhl.com/svc/suggest/v1/minactiveplayers/" + urllib.parse.quote(lastName) + "/99999"
            response = urllib.request.urlopen(url).read()
            data = json.loads(response.decode())
            # Response example: {"suggestions":["8477971|Englund|Andreas|1|0|6\u0027 3\"|189|Stockholm||SWE|1996-01-21|OTT|D|39|andreas-englund-8477971"]}
            if len(data['suggestions']) == 1:
                return data['suggestions'][0].split("|")[0]

            for player in data['suggestions']:
                player_info = player.split("|")
                if firstName == player_info[2]:
                    return player_info[0]

            # Nothing was found, so search by first name and look for last name
            url = "https://suggest.svc.nhl.com/svc/suggest/v1/minactiveplayers/" + urllib.parse.quote(firstName) + "/99999"
            response = urllib.request.urlopen(url).read()
            data = json.loads(response.decode())
            if len(data['suggestions']) == 1:
                return data['suggestions'][0].split("|")[0]

            # Response example: {"suggestions":["8477971|Englund|Andreas|1|0|6\u0027 3\"|189|Stockholm||SWE|1996-01-21|OTT|D|39|andreas-englund-8477971"]}
            for player in data['suggestions']:
                player_info = player.split("|")
                if lastName == player_info[1]:
                    return player_info[0]

            # Dmitri Orlov is not spelled correctly on daily faceoff
            if firstName == "Dmitri" and lastName == "Orlov":
                return 8475200

            raise ValueError("Could not find any player ID.")

        except Exception as e:
            logging.error("Could not find player ID for " + playerName)
            logging.error("Got the following error:")
            logging.error(e)
            raise e

class GameManager(models.Manager):
    def get_game(self, gameInfo):
        # Game info in for ABC@DEF 7:00 PM ET
        teams = gameInfo.split()[0]
        home_team = teams.split("@")[1]
        away_team = teams.split("@")[0]
        home_team_id = 0
        away_team_id = 0
        return self.get_game_by_ids(home_team_id, away_team_id)

    def get_game_pk_by_ids(self, home_team_id, away_team_id):
        try:
            # Find the latest gamePk with the given team IDs
            for game in self.model.objects.filter(Q(home_team_id=home_team_id), Q(away_team_id=away_team_id)).order_by(
                    '-game_pk'):
                return game.game_pk

        except Exception as e:
            logging.error("Could not find gamePk for " + str(home_team_id) + ", " + str(away_team_id))
            logging.error("Got the following error:")
            logging.error(e)
            raise e


    def get_game_by_ids(self, home_team_id, away_team_id):
        try:
            # Find the latest gamePk with the given team IDs
            for game in self.model.objects.filter(Q(home_team_id=home_team_id), Q(away_team_id=away_team_id)).order_by(
                    '-game_pk'):
                return game

        except Exception as e:
            logging.error("Could not find game for " + str(home_team_id) + ", " + str(away_team_id))
            logging.error("Got the following error:")
            logging.error(e)
            raise e

class TeamManager(models.Manager):
    def get_team_id(self, team_name):
        try:
            for team in self.model.objects.filter(Q(name=team_name) | Q(team_name=team_name.split()[1])):
                return team.id

        except Exception as e:
            logging.error("Could not find gamePk for " + team_name)
            logging.error("Got the following error:")
            logging.error(e)
            raise e

    def get_team_id_by_city(self, team_city):
        try:
            for team in self.model.objects.filter(location_name=team_city):
                return team.id

            if team_city == "N.Y. Rangers":
                return 3
            elif team_city == "N.Y. Islanders":
                return 2
            elif team_city == "Montreal":
                return 8

            ValueError("Could not find team by city: " + team_city)

        except Exception as e:
            logging.error("Could not find gamePk for " + team_city)
            logging.error("Got the following error:")
            logging.error(e)
            raise e
