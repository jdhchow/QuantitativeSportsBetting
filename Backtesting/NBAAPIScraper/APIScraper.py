import json
import requests
import time
import pandas as pd
import datetime


'''
Author: Jonathan Chow
Date Modified: 2020-01-11
Python Version: 3.7

Code to extract features from data.nba.net. A simple guide can be found at
https://github.com/kashav/nba.js/blob/master/docs/api/DATA.md.
'''


# Breaks if periods are not 20min (with 5min overtime)
def calcGameTime(eventTime, perNum):
    rawTime = eventTime.split(':')
    timeInPeriod = float(rawTime[0]) * 60.0 + float(rawTime[1])
    timeInPeriod = 720.0 - timeInPeriod if perNum < 5 else 300.0 - timeInPeriod
    gameTime = sum([720.0 if per < 5 else 300.0 for per in range(1, perNum)]) + timeInPeriod

    return gameTime


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


def getGameIdDicts(season):
    gameIdDicts = []
    nbaUrl = 'http://data.nba.net/data/10s/prod/v1/' + str(season) + '/schedule.json'

    responseCode, nbaJson = accessAPI(nbaUrl, 1)

    if responseCode == 0:
        nbaDict = json.loads(nbaJson)

        for game in nbaDict['league']['standard']:
            if game['seasonStageId'] == 2 or game['seasonStageId'] == 4:  # Only add regular season and playoff games
                gameIdDicts.append({'id': str(game['gameId']),
                                    'type': 'R' if game['seasonStageId'] == 2 else 'P',
                                    'date': str(game['gameUrlCode']).split('/')[0],
                                    'periods': int(game['period']['current']),
                                    'hteam.id': str(game['hTeam']['teamId']),
                                    'vteam.id': str(game['vTeam']['teamId'])})  # Specific games are references by id and date

    gameIdDicts.sort(key=lambda x: x['id'], reverse=False)

    return gameIdDicts


def getBaseGameInformation(gameIdDict):
    baseInformation = pd.DataFrame()

    baseInformation['home'] = [1, 0]
    baseInformation['away'] = [0, 1]

    baseInformation['final.period'] = [gameIdDict['periods']] * 2
    baseInformation['game.date'] = [gameIdDict['date']] * 2
    baseInformation['game.type'] = [gameIdDict['type']] * 2
    baseInformation['team.id'] = [gameIdDict['hteam.id'], gameIdDict['vteam.id']]

    baseInformation.index = [[gameIdDict['id']] * 2, ['home', 'away']]

    hPoints = []
    vPoints = []

    for period in range(1, gameIdDict['periods'] + 1):
        nbaPeriodUrl = 'http://data.nba.net/data/10s/prod/v1/' + gameIdDict['date'] + '/' + gameIdDict['id'] + '_pbp_' + str(period) + '.json'

        responseCode, nbaJson = accessAPI(nbaPeriodUrl, 1)

        if responseCode == 0:
            nbaDict = json.loads(nbaJson)

            for play in nbaDict['plays']:
                if len(hPoints) == 0 or hPoints[-1][1] != int(play['hTeamScore']):
                    hPoints.append((calcGameTime(play['clock'], period), int(play['hTeamScore'])))

                if len(vPoints) == 0 or vPoints[-1][1] != int(play['vTeamScore']):
                    vPoints.append((calcGameTime(play['clock'], period), int(play['vTeamScore'])))

    baseInformation['running.points'] = [hPoints, vPoints]

    return baseInformation
