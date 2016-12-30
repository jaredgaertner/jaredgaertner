import argparse
import copy
import csv
import datetime
import logging
import pytz
import random
import re
import urllib
from bs4 import BeautifulSoup
from knapsack import knapsack, brute_force

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Q, Avg
from django.utils import timezone

from lineups.models import Player, Game, PlayerGame, PlayerGameDraftKings

from bs4 import BeautifulSoup

logger = logging.getLogger('django')
date_format = "%Y-%m-%d"

class Command(BaseCommand):
    help = 'Calculates lineups, pass in date in form YYYY-MM-DD (by default today)'

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
        parser.add_argument('date_for_lineup', nargs='?', type=valid_date, default=default_date_string,
                            help='Date to create lineups for.')

    def handle(self, *args, **options):
        logging.debug("Hardcoding date and goalies for the lineup....")
        date_for_lineup = timezone.now()
        date_for_lineup = options['date_for_lineup']

        lineup_type = "initial"
        force_update = False
        number_of_lineups = 15
        lowering_value = -0.1  # Value decrease after player is used in lineup

        # calculate all lineups/entries
        calculate_lineups(date_for_lineup, number_of_lineups, lineup_type, lowering_value, force_update)

        # Get statistics from previous night
        # if lineup_type == "initial":
        #     calculate_statistics(db)

def calculate_sets_of_players(skaters, goalies, util, limit, type="knapsack"):
    if type == "knapsack":
        return knapsack(skaters, goalies, util, limit)
    elif type == "brute_force":
        return brute_force(skaters, goalies, util, limit)  # , 100, 4000)
    else:
        raise ValueError(
            "Invalid type for calculate_set_of_players: " + type + ", choose either knapsack or brute_force.")


def get_starting_goalies(db, date_for_lineup):
    starting_goalies = []
    try:
        logging.info("Finding starting goalies...")
        url = "http://www2.dailyfaceoff.com/starting-goalies/" + str(date_for_lineup.year) + "/" + str(
            date_for_lineup.month) + "/" + str(date_for_lineup.day) + "/"
        soup = BeautifulSoup(urllib.request.urlopen(url).read(), "html.parser")
        # matchups = soup.find(id="matchups")
        for row in soup.find_all("div", "goalie"):
            if row.find("h5") != None:
                goalie_name = row.h5.a.string
                logging.info("Adding goalie: " + str(goalie_name))
                status = row.dl.dt.string
                logging.info("Status: " + str(status))

                starting_goalies.append(goalie_name)

            # Not currently needed, as only shows goalies which aren't confirmed
            # Else, we need to look at the document.write statement
            else:
                match = re.search(r"document\.write\(\"(.+)\"\)", str(row))
                goalie_info = BeautifulSoup(match.group(1), "html.parser")
                goalie_name = goalie_info.h5.a.string
                logging.info("Not adding goalie: " + str(goalie_name))
                status = goalie_info.dl.dt.string
                logging.info("Status: " + str(status))
                # starting_goalies.append(goalie_name)

        return starting_goalies

    except Exception as e:
        logging.error("Could not connect to dailyfaceoff to get starting goalies.")
        logging.error("Got the following error:")
        logging.error(e)
        # Roll back any change if something goes wrong
        # db.rollback()
        raise e

    return starting_goalies

def get_player_game_from_game_info(name, game_info):
    player = Player.objects.update_player(name)
    game = Game.objects.get_game(game_info)
    return PlayerGame(player=player, game=game, opponent=opponentId)

def get_player_data(db, date_for_lineup, force_update=False):  # , ir_players):
    players = []
    # Check if any IR players exist in database
    # if ir_players:
    #     logging.debug("Checking IR players")
    #     db.query("select exists(select 1 from player_draftkings_info where name = ?) irPlayerInfoExists",
    #               (ir_players[0],))
    #     if db.fetchone()['irPlayerInfoExists'] == 1:
    #         # Clear out table and recalculate values
    #         logging.info("Clearing out player info for IR for " + str(date_for_lineup))
    #         db.query("delete from player_draftkings_info where date(dateForLineup) = date(?)", (date_for_lineup,))
    #         db.commit()

    # Check if data already exists in database
    db.query("select exists(select 1 from player_draftkings_info where date(dateForLineup) = date(?)) playerInfoExists",
             (date_for_lineup,))
    if db.fetchone()['playerInfoExists'] == 1 and force_update != True:
        logging.info("Player information for DraftKings already exists, grabbing from database.")
        try:

            db.query('''select pdi.id,
                                pdi.name,
                                pdi.nameAndId,
                                pdi.playerId,
                                pdi.weight,
                                pdi.value,
                                pdi.position,
                                pdi.gameInfo,
                                pdi.opponentId,
                                pdi.gamePk,
                                pdi.teamAbbrev,
                                pdi.dateForLineup,
                                pdi.draftType
                        from player_draftkings_info pdi
                        where date(pdi.dateForLineup) = date(?)''', (date_for_lineup,))
            for pdi in db.fetchall():
                player_info = PlayerGameDraftKings(db,
                                                   pdi['nameAndId'],
                                                   pdi['name'],
                                                   pdi['id'],
                                                   pdi['weight'],
                                                   pdi['position'],
                                                   pdi['gameInfo'],
                                                   pdi['teamAbbrev'],
                                                   pdi['draftType'],
                                                   pdi['dateForLineup'])
                players.append(player_info)
            return players

        except Exception as e:
            logging.error("Could not find player info for DraftKings on " + str(date_for_lineup))
            logging.error("Got the following error:")
            logging.error(e)
            raise e

    # Doesn't, so check from file
    else:
        logging.info(
            "Player information for DraftKings doesn't exist, grabbing from csv file: DKSalaries_" + date_for_lineup.strftime(
                "%d%b%Y").upper() + ".csv")
        with open("../resources/DKSalaries_" + date_for_lineup.strftime("%d%b%Y").upper() + ".csv", "r") as csvfile:
            # Skip the first 7 lines, as it contains the format for uploading
            for i in range(7):
                next(csvfile)

            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row[' Name']
                # if name not in ir_players:
                player_info = PlayerGameDraftKings(get_player_game_from_game_info(row[' Name'], row['GameInfo']),
                                                   name_and_id=row['Name + ID'],
                                                   id=row[' ID'],
                                                   salary=int(int(row[' Salary']) / 100),
                                                   position=row['Position'],
                                                   draft_type="Standard",
                                                   date_for_lineup=date_for_lineup)
                logging.debug(player_info)
                players.append(player_info)
                player_info.insert_player_data()

            csvfile.close()
            return players


def get_entries(db, date_for_lineup):
    entries = []

    # Check if data already exists in database
    db.query("select exists(select 1 from daily_draftkings_entries where date(createdOn) = date(?)) entryExists",
             (date_for_lineup,))
    if db.fetchone()['entryExists'] == 1:
        logging.info("Entries for DraftKings already exists, grabbing from database.")
        try:

            db.query('''select dde.id,
                               dde.entryId,
                               dde.contestName,
                               dde.contestId,
                               dde.entryFee
                        from daily_draftkings_entries dde
                        where date(dde.createdOn) = date(?)''', (date_for_lineup,))
            for dde in db.fetchall():
                logging.debug(dde)
                entry_info = Entry(db,
                                   dde['entryId'],
                                   dde['contestName'],
                                   dde['contestId'],
                                   dde['entryFee'],
                                   dde['id'])
                entries.append(entry_info)
            return entries

        except Exception as e:
            logging.error("Could not find entries for DraftKings on " + str(date_for_lineup))
            logging.error("Got the following error:")
            logging.error(e)
            raise e

    # Doesn't, so check from file
    else:
        try:
            logging.info(
                "Entry information for DraftKings doesn't exist, trying to grab from csv file: DKEntries_" + date_for_lineup.strftime(
                    "%d%b%Y").upper() + ".csv")
            with open("../resources/DKEntries_" + date_for_lineup.strftime("%d%b%Y").upper() + ".csv", "r") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Entry ID']:
                        logging.debug(row)
                        entry_info = Entry(db,
                                           row['Entry ID'],
                                           row['Contest Name'],
                                           row['Contest ID'],
                                           row['Entry Fee']);
                        entries.append(entry_info)
                        entry_info.insert_entry()

                csvfile.close()
                return entries
        except FileNotFoundError as e:
            logging.info("Did not find entries, could be the initial lineup on " + str(date_for_lineup))
            logging.info("Got the following error:")
            logging.info(e)
            return None


def calculate_lineups(db, date_for_lineup, number_of_lineups, lineup_type="initial", lowering_value=-0.1, force_update=False):
    # Create lineups/entries for all combinations of top goalies (or chosen goalies) and top value/cost players
    # Write top lineups/entries to file
    if lineup_type == "initial":
        filename = "../resources/lineups/DKLineup_" + date_for_lineup.strftime("%Y%m%d-%H%M%S") + ".csv"
        header_row = ["C", "C", "W", "W", "W", "D", "D", "G", "UTIL"]
    elif lineup_type == "entry":
        filename = "../resources/lineups/DKEntries_" + date_for_lineup.strftime("%Y%m%d-%H%M%S") + ".csv"
        header_row = ["Entry ID", "Contest Name", "Contest ID", "Entry Fee", "C", "C", "W", "W", "W", "D", "D", "G",
                      "UTIL"]
    else:
        raise ValueError("Invalid entry for lineup_type.")

    with open(filename, "w") as csvfile:
        writer = csv.writer(csvfile, lineterminator='\n')
        writer.writerow(header_row)

        logging.debug("Starting creating lineups....")
        all_lineups = []

        logging.debug("Setting up players with ID and values....")
        players = get_player_data(db, date_for_lineup, force_update)
        if lineup_type == "entry":
            entries = get_entries(db, date_for_lineup)
        else:
            entries = None

        logging.debug("Finding starting goalies....")
        starting_goalies = get_starting_goalies(db, date_for_lineup)
        goalies = [item for item in players if item.get_name() in starting_goalies]
        if len(goalies) == 0:
            raise ValueError("Could not find any starting goalies.")

        # Sort list of players and remove any goalies and players with value less than 1.0 and weight 25 or under, or if not active
        # Choose one Util from the from of the list
        logging.debug("Finding skaters....")
        skaters = copy.deepcopy(players)
        active_players = get_all_active_player_ids(db)
        skaters = [item for item in skaters if
                   item.get_position() != "G" and
                   item.get_value() > 1.0 and
                   item.get_weight() > 25 and
                   item.get_player_id() != None and
                   item.get_player_id() in active_players]
        # for skater in skaters:
        #     logging.info(skater)
        #     logging.info(skater.get_player_id())

        limit = 500
        # for i in range(len(chosen_goalies)):
        # skaters = copy.deepcopy(players)
        # Use the following statements to check a specific player's value
        # ss_value = [item for item in skaters if item['nameAndId'] == 'Steven Stamkos (7723976)'][0]['value']
        # logging.debug("Steven Stamkos value: " + str(ss_value) + ", players length: " + str(len(players)))
        for i in range(number_of_lineups):
            # Find the chosen goalies
            # chosen_goalie = [item for item in players if item.get_name_and_id() == chosen_goalies[i]][0]

            # Add random noise in order to get varied results (as a factor of the value used to lower player values that
            # have been used in a previous lineup
            # for skater in skaters:
            #     skater.add_value(random.uniform(4 * lowering_value, -4 * lowering_value))

            # Choose a Util based on the best value
            skaters = sorted(skaters, key=lambda tup: tup.get_value(), reverse=True)
            chosen_util = skaters[0]

            # Remove Util from skaters (will be returned after calculating the set)
            skaters = [item for item in skaters if item.get_name_and_id() != chosen_util.get_name_and_id()]

            # skaters = [item for item in unused_players if item['position'] != "G"]
            logging.info("Getting lineup with " + chosen_util.get_name_and_id() + " as Util.")

            calculated_set_of_players = calculate_sets_of_players(skaters, goalies, chosen_util, limit)
            calculated_set_of_players = sorted(calculated_set_of_players, key=lambda tup: tup[10], reverse=True)
            calculated_lineup = Lineup(db, calculated_set_of_players[0])
            logging.debug(calculated_lineup)

            # Add Util back in for next loop
            skaters.append(chosen_util)

            # Lower value of non-chosen players in selected set (C,W,D), as they've already been selected
            for skater in skaters:
                if skater.get_name_and_id() in calculated_set_of_players[0]:
                    logging.info("Lowering value of " + str(skater.get_name_and_id()) + " by " + str(lowering_value) + ".")
                    skater.add_value(lowering_value)

            for goalie in goalies:
                if goalie.get_name_and_id() in calculated_set_of_players[0]:
                    logging.info("Lowering value of " + str(goalie.get_name_and_id()) + " by " + str(lowering_value) + ".")
                    goalie.add_value(lowering_value)

            # Add found lineup to all lineups
            logging.info("Lineup number " + str(i+1) + ":")
            logging.info(calculated_lineup)
            all_lineups.append(calculated_lineup)

            # Write top lineup to csv
            if lineup_type == "entry":
                entries[i].set_lineup(all_lineups[i])
                writer.writerow(entries[i].get_list()[:13])
            else:
                writer.writerow(calculated_set_of_players[0][:9])
            csvfile.flush()

            # Remove goalie from players
            # players = [item for item in players if item.get_name_and_id() != chosen_goalie.get_name_and_id()]

        csvfile.close()

    # Sort final lineups and print
    all_lineups = sorted(all_lineups, key=lambda tup: tup.get_total_value(), reverse=True)
    for s in range(len(all_lineups)):
        logging.info(all_lineups[s].get_list())

    # Write all lineups to database
    for lineup in all_lineups:
        lineup.insert_lineup()

    with open("../resources/lineups/DKAllLineups_" + date_for_lineup.strftime("%Y%m%d-%H%M%S") + ".csv",
              "w") as csvfile:
        writer = csv.writer(csvfile, lineterminator='\n')
        writer.writerow(["C", "C", "W", "W", "W", "D", "D", "G", "UTIL", "Weight", "Value"])
        for s in range(len(all_lineups)):
            writer.writerow(all_lineups[s].get_list())

        csvfile.close()
