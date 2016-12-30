import logging

__author__ = "jaredg"

logger = logging.getLogger(__name__)

# Find up to max_size pairs of players with maximum value to weight ratio
def find_player_pair(players, position, max_set_size=200):
    players = [item for item in players if item.get_position() == position]
    logging.debug("Number of " + position + " being used in pairs: " + str(len(players)))
    set_of_players = []
    for i in range(0, len(players) - 1):
        for j in range(i + 1, len(players) - 1):
            player_pair = {"nameAndId": [players[i].get_name_and_id(), players[j].get_name_and_id()],
                           "weight": players[i].get_weight() + players[j].get_weight(),
                           "value": players[i].get_value() + players[j].get_value(),
                           "position": position}
            set_of_players.append(player_pair)

    # Take the max_size number of optimal value to weight ratio and the max_size number of highest value pairs of the rest left
    logging.debug("Total number of " + position + " pairs: " + str(len(set_of_players)))
    return set_of_players
    # sorted_set_of_players_optimal = sorted(set_of_players, key=lambda tup: tup['value'] / tup['weight'], reverse=True)
    # sorted_set_of_players_highest_value = sorted(sorted_set_of_players_optimal[max_set_size:], key=lambda tup: tup.get_value(),
    #                                              reverse=True)
    # return sorted_set_of_players_optimal[:max_set_size] + sorted_set_of_players_highest_value[:max_set_size]


def find_player_triples(players, position, max_triple_set_size=20000):
    players = [item for item in players if item.get_position() == position]
    logging.debug("Number of " + position + " being used in triples: " + str(len(players)))
    set_of_players = []
    for i in range(0, len(players) - 1):
        for j in range(i + 1, len(players) - 1):
            for k in range(i + j + 1, len(players) - 1):
                player_triple = {
                    "nameAndId": [players[i].get_name_and_id(), players[j].get_name_and_id(), players[k].get_name_and_id()],
                    "weight": players[i].get_weight() + players[j].get_weight() + players[k].get_weight(),
                    "value": players[i].get_value() + players[j].get_value() + players[k].get_value(), "position": position}
                set_of_players.append(player_triple)

    # Take the max_size number of optimal value to weight ratio and the max_size number of highest value triplets
    logging.debug("Total number of " + position + " triples: " + str(len(set_of_players)))
    return set_of_players
    # sorted_set_of_players_optimal = sorted(set_of_players, key=lambda tup: tup.get_value() / tup.get_weight(), reverse=True)
    # sorted_set_of_players_highest_value = sorted(sorted_set_of_players_optimal[max_triple_set_size:],
    #                                              key=lambda tup: tup.get_value(), reverse=True)
    # return sorted_set_of_players_optimal[:max_triple_set_size] + sorted_set_of_players_highest_value[
    #                                                              :max_triple_set_size]

# http://stackoverflow.com/questions/19389931/knapsack-constraint-python
def multi_choice_knapsack(goalies, util, defensemen, centres, wingers, limit):
    # Remove chosen G and W from limit
    limit -= util.get_weight()
    logging.debug("New limit, after removing chosen Util is: " + str(limit))

    # Run multiple-choice knapsack on the pairs of D, C, W, and a goalie
    positions = ["G", "C", "W", "D"]
    table = [[0 for w in range(limit + 1)] for j in range(len(positions) + 1)]
    player_added = [[0 for w in range(limit + 1)] for j in range(len(positions) + 1)]
    logging.debug("Knapsack: Going through all " + str(len(positions)) + " positions.")
    for i in range(1, len(positions) + 1):
        logging.debug("Multiple Choice Knapsack: Checking position " + str(positions[i - 1]))
        if positions[i - 1] == "W":
            current_player_set = wingers
        elif positions[i - 1] == "G":
            current_player_set = goalies
        elif positions[i - 1] == "D":
            current_player_set = defensemen
        elif positions[i - 1] == "C":
            current_player_set = centres
        else:
            logging.error("Unknown position!")

        for w in range(1, limit + 1):
            max_val_for_position = table[i - 1][w]
            for player in current_player_set:
                # Find the max for all player_set of that position
                weight = player['weight']
                nameAndId = player['nameAndId']
                value = player['value']
                position = player['position']

                if weight <= w and table[i - 1][w - weight] + value > max_val_for_position:
                    max_val_for_position = table[i - 1][w - weight] + value
                    player_added[i][w] = player
                    logging.debug(
                        "Adding player at (" + str(i) + "," + str(w) + "): " + str(nameAndId) + ", wt: " + str(
                            weight) + ", val: " + str(value) + ", position: " + str(
                            position))
            table[i][w] = max_val_for_position

    result = []
    w = limit
    logging.debug(table[2][w])
    total_value = 0
    total_weight = 0
    for i in range(len(positions), 0, -1):
        for j in range(w, 0, -1):
            was_added = table[i][j - 1] != table[i][j]

            if was_added:
                logging.debug(player_added[i][j])
                weight = player_added[i][j]['weight']
                value = player_added[i][j]['value']

                result.append(player_added[i][j])
                total_value += value
                total_weight += weight
                w -= weight
                break

    # Adding players names to a set of players, results added in reverse order (Util, D, W, C)
    logging.debug(result)
    total_weight += util.get_weight()
    total_value += util.get_value()
    logging.debug(total_value)
    full_set = [result[2]['nameAndId'][0],
                result[2]['nameAndId'][1],
                result[1]['nameAndId'][0],
                result[1]['nameAndId'][1],
                result[1]['nameAndId'][2],
                result[0]['nameAndId'][0],
                result[0]['nameAndId'][1],
                result[3]['nameAndId'],
                util.get_name_and_id(),
                total_weight,
                total_value]
    set_of_players = []
    set_of_players.append(full_set)
    logging.debug(set_of_players)
    return set_of_players


def knapsack(skaters, goalies, util, limit, max_set_size=2000, max_triple_set_size=400000):
    defensemen = find_player_pair(skaters, "D", max_set_size)
    centres = find_player_pair(skaters, "C", max_set_size)
    wingers = find_player_triples(skaters, "W", max_triple_set_size)

    logging.debug("Number of D pairs being checked: " + str(len(defensemen)))
    logging.debug("Number of C pairs being checked: " + str(len(centres)))
    logging.debug("Number of W pairs being checked: " + str(len(wingers)))

    return multi_choice_knapsack(goalies, util, defensemen, centres, wingers, limit)


def brute_force(skaters, goalies, util, limit, max_set_size=2000):
    defensemen = find_player_pair(skaters, "D", max_set_size)
    centres = find_player_pair(skaters, "C", max_set_size)
    wingers = find_player_triples(skaters, "W", max_set_size)

    logging.info("Number of D pairs being checked: " + str(len(defensemen)))
    logging.info("Number of C pairs being checked: " + str(len(centres)))
    logging.info("Number of W pairs being checked: " + str(len(wingers)))

    set_of_players = []
    index = 0

    logging.info(
        "Potential number of combinations: " + str(len(centres) * len(defensemen) * len(wingers)))
    for i in range(0, len(goalies)-1):
        for j in range(len(centres)):
            for k in range(len(defensemen)):
                for l in range(len(wingers)):
                    # for m in range(len(skaters)):
                    #     if skaters[m]['nameAndId'] not in centres[j]['nameAndId'] and skaters[m]['nameAndId'] not in defensemen[k]['nameAndId'] and skaters[m][
                    #         0] not in wingers[l]['nameAndId'] and skaters[m]['nameAndId'] != winger['nameAndId']:
                    weight = goalies[i]['weight'] + centres[j]['weight'] + defensemen[k]['weight'] + wingers[l]['weight'] + \
                             util['weight']
                    value = goalies[i]['value'] + centres[j]['value'] + defensemen[k]['value'] + wingers[l]['value'] + util[
                        'value']
                    index += 1

                    if index % 10000 == 0:
                        # Only keep the top 100 sets of players
                        set_of_players = sorted(set_of_players, key=lambda tup: tup[10], reverse=True)
                        set_of_players = set_of_players[:10]

                    if index % 10000000 == 0:
                        logging.info("Number of sets checked: " + str(index) + ", top set:")
                        logging.info(set_of_players[0])

                    if weight <= limit:
                        full_set = [centres[j]['nameAndId'][0],
                                    centres[j]['nameAndId'][1],
                                    wingers[l]['nameAndId'][0],
                                    wingers[l]['nameAndId'][1],
                                    wingers[l]['nameAndId'][2],
                                    defensemen[k]['nameAndId'][0],
                                    defensemen[k]['nameAndId'][1],
                                    goalies[i]['nameAndId'],
                                    util['nameAndId'],
                                    weight,
                                    value]
                        set_of_players.append(full_set)

    logging.debug("Number of sets checked: " + str(index))
    return set_of_players