import json
import requests
import time
import pandas as pd
import datetime


'''
Author: Jonathan Chow
Date Modified: 2019-04-09
Python Version: 3.7

Code to extract features from statsapi.web.nhl.com/api/. Explanations for column header meanings can be found at
http://www.nhl.com/stats/glossary and API documentation can be found at https://gitlab.com/dword4/nhlapi.git.
'''


def accessAPI(url, attempts):
    if attempts > 5:
        print(str(datetime.datetime.now()) + ': Attempt limit exceeded to ' + url)
        return -1, ''
    else:
        try:
            request = requests.get(url)

            if 200 <= request.status_code < 300:
                # Success
                status = 0
                webText = request.text
            elif request.status_code == 429:
                # Sent too many requests too quickly
                print(str(datetime.datetime.now()) + ': Too many requests to ' + url)
                time.sleep(300)
                status, webText = accessAPI(url, attempts + 1)
            else:
                print(str(datetime.datetime.now()) + ': Received HTTP response code ' + str(request.status_code) + ' from ' + url)
                time.sleep(300)
                status, webText = accessAPI(url, attempts + 1)
        except ConnectionResetError:
            print(str(datetime.datetime.now()) + ': Connection to ' + url + ' reset by peer')
            status, webText = accessAPI(url, attempts + 1)
        except ConnectionAbortedError:
            print(str(datetime.datetime.now()) + ': Connection to ' + url + ' aborted (likely lost wifi connection)')
            time.sleep(3600)
            status, webText = accessAPI(url, attempts + 1)

        return status, webText


def getGameIds(season):
    gameIds = []
    nhlUrl = 'https://statsapi.web.nhl.com/api/v1/schedule?season=' + str(season) + str(season + 1)

    responseCode, nhlJson = accessAPI(nhlUrl, 1)

    if responseCode == 0:
        nhlDict = json.loads(nhlJson)

        for dates in nhlDict['dates']:
            for game in dates['games']:
                gameIds.append(str(game['gamePk']))

    # Remove preseason and all-star games
    gameIds = [gameId for gameId in gameIds if 1 < int(gameId[5:6]) < 4]

    gameIds.sort(reverse=False)

    return gameIds


def getBaseGameInformation(gameId):
    baseInformation = pd.DataFrame()
    nhlUrl = 'https://statsapi.web.nhl.com/api/v1/game/' + gameId + '/feed/live'

    responseCode, nhlJson = accessAPI(nhlUrl, 1)

    if responseCode == 0:
        nhlDict = json.loads(nhlJson)

        baseInformation['game.type'] = [nhlDict['gameData']['game']['type']] * 2
        baseInformation['game.date'] = [datetime.datetime.strptime(nhlDict['gameData']['datetime']['dateTime'][:-4], '%Y-%m-%dT%H:%M')] * 2

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
