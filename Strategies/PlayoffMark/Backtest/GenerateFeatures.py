from Jonathan.NHL.Strategies.GeneralIO import *
import json


'''
Author: Jonathan Chow
Date Modified: 2019-04-09
Python Version: 3.7

Code to extract features from statsapi.web.nhl.com/api/. Explanations for column header meanings can be found at
http://www.nhl.com/stats/glossary and API documentation can be found at https://gitlab.com/dword4/nhlapi.git.
'''


def getGameIds(season, isProduction):
    gameIds = []
    nhlUrl = getNHLURL(sArgs=['schedule'], qArgs=['season=' + str(season) + str(season + 1)])

    saveLoc = 'intermediate' if isProduction else 'permanent'
    responseCode, nhlJson = accessAPI(nhlUrl, saveLoc)

    if responseCode == 0:
        nhlDict = json.loads(nhlJson)

        for dates in nhlDict['dates']:
            for game in dates['games']:
                gameIds.append(str(game['gamePk']))

    if isProduction:
        # Keep only regular season games
        gameIds = [gameId for gameId in gameIds if int(gameId[5:6]) == 2]
    else:
        # Remove preseason and all-star games
        gameIds = [gameId for gameId in gameIds if 1 < int(gameId[5:6]) < 4]

    gameIds.sort(reverse=False)

    return gameIds


def getBaseGameInformation(gameId, isCurrent):
    baseInformation = pd.DataFrame()
    nhlUrl = getNHLURL(sArgs=['game', gameId, 'feed', 'live'])

    saveLoc = 'temporary' if isCurrent else 'permanent'
    responseCode, nhlJson = accessAPI(nhlUrl, saveLoc)

    if responseCode == 0:
        nhlDict = json.loads(nhlJson)

        baseInformation['game.type'] = [nhlDict['gameData']['game']['type']] * 2
        baseInformation['game.date'] = [datetime.datetime.strptime(nhlDict['gameData']['datetime']['dateTime'][:-4], '%Y-%m-%dT%H:%M')] * 2

        if not isCurrent:
            homeGoals = nhlDict['liveData']['boxscore']['teams']['home']['teamStats']['teamSkaterStats']['goals']
            awayGoals = nhlDict['liveData']['boxscore']['teams']['away']['teamStats']['teamSkaterStats']['goals']

            overtime = True if nhlDict['liveData']['linescore']['currentPeriod'] == 4 else False

            if not overtime:
                baseInformation['goals'] = [homeGoals, awayGoals]

                if homeGoals > awayGoals:
                    baseInformation['game.winner'] = ['home'] * 2
                elif homeGoals == awayGoals:
                    baseInformation['game.winner'] = ['tie'] * 2
                else:
                    baseInformation['game.winner'] = ['away'] * 2
            else:
                baseInformation['game.winner'] = ['tie'] * 2
                baseInformation['goals'] = [min(homeGoals, awayGoals)] * 2

        baseInformation['home'] = [1, 0]
        baseInformation['away'] = [0, 1]

        baseInformation['team.id'] = [str(nhlDict['gameData']['teams']['home']['id']),
                                      str(nhlDict['gameData']['teams']['away']['id'])]

        # Montreal Canadiens team name is not properly parsed
        baseInformation['team.name'] = [nhlDict['gameData']['teams']['home']['name'] if baseInformation.loc[0, 'team.id'] != '8' else 'Montreal Canadiens',
                                        nhlDict['gameData']['teams']['away']['name'] if baseInformation.loc[1, 'team.id'] != '8' else 'Montreal Canadiens']

        baseInformation.index = [[gameId] * 2, ['home', 'away']]

    return baseInformation


def getOdds():
    # Odds scraped from OddsPortal (e.g. http://www.oddsportal.com/hockey/usa/nhl-2015-2016/results/#/page/4/)
    bookmakerOdds = readJson('Strategies/Markov/Records/Features/BookmakersOdds')
    bookmakerOdds['date'] = pd.to_datetime(bookmakerOdds['day'] + ' ' + bookmakerOdds['time'], format='%d %b %Y %H:%M')
    bookmakerOdds.drop(['day', 'time'], axis=1, inplace=True)
    bookmakerOdds = bookmakerOdds.loc[bookmakerOdds['pre-season'] == False]

    return bookmakerOdds


def mergeOdds(trainingData, bookmakerOdds):
    oddsDict = {'currTeam.odds': [], 'oppTeam.odds': [], 'tie.odds': [], 'currTeam.oddsMax': [], 'oppTeam.oddsMax': [],
                'tie.oddsMax': []}

    teamTable = pd.concat([trainingData['team.name'].rename('home'), trainingData['team.name'].shift(-1).rename('away'),
                           trainingData['game.date']], axis=1).iloc[::2, :]

    for key in list(oddsDict.keys()):
        oddsDict[key] = list(teamTable.apply(lambda row: mergeOddsHelper(row, bookmakerOdds, key), axis=1))
        oddsDict[key] = [item for sublist in oddsDict[key] for item in sublist]

        trainingData[key] = oddsDict[key]

    return trainingData


def mergeOddsHelper(row, odds, side):
    restricted = odds.loc[(odds['home'] == row['home']) & (odds['away'] == row['away']) &
                          ((odds['date'] + datetime.timedelta(hours=10)) >= row['game.date']) &
                          ((odds['date'] - datetime.timedelta(hours=10)) <= row['game.date'])]

    suffix = side.split('.')[1]
    prefix = side.split('.')[0]

    if prefix == 'currTeam':
        euroOdd = [restricted['home.' + suffix].iloc[0] if not restricted.empty else 0]
        euroOdd = euroOdd + [restricted['away.' + suffix].iloc[0] if not restricted.empty else 0]
    elif prefix == 'oppTeam':
        euroOdd = [restricted['away.' + suffix].iloc[0] if not restricted.empty else 0]
        euroOdd = euroOdd + [restricted['home.' + suffix].iloc[0] if not restricted.empty else 0]
    else:
        euroOdd = [restricted['tie.' + suffix].iloc[0] if not restricted.empty else 0] * 2

    if len(restricted) > 1:
        writeLog(str(datetime.datetime.now()) + ': Merging by time and teams not unique on ' + str(row['game.date']))

    return euroOdd
