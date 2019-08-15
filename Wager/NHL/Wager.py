import datetime
import pandas as pd
import numpy as np
import requests
import json
from scipy.optimize import curve_fit


'''
Author: Jonathan Chow
Date Modified: 2019-08-12
Python Version: 3.7

Generate wager for Markov playoff strategy (See PlayoffMarkEx in Attridge/Backtesting). Only manual requirement are
maximum regular time odds (from legitimate bookmakers) for the game.

Allowed Bookmakers:
    - William Hill
    - Bet365
    - BetHard

Starting Capital: $6000
'''


# Activation function used in paper
def winProbFunc(x, a, b):
    return np.exp(-a * x - b) / (1 + np.exp(-a * x - b))


def getWinner(data):
    # Mapping for each row is: Win = 1, Tie = 0, Lose = -1
    if (data['game.winner'] == 'home' and data['home'] == 1) or (data['game.winner'] == 'away' and data['home'] == 0):
        winner = 1
    elif data['game.winner'] == 'tie':
        winner = 0
    else:
        winner = -1

    return winner


def accessAPI(url):
    try:
        request = requests.get(url)

        if 200 <= request.status_code < 300:
            # Success
            return request.text
        elif request.status_code == 429:
            # Sent too many requests too quickly
            print(str(datetime.datetime.now()) + ': Too many requests to ' + url)
        else:
            print(str(datetime.datetime.now()) + ': Received HTTP response code ' + str(request.status_code) + ' from ' + url)
    except ConnectionResetError:
        print(str(datetime.datetime.now()) + ': Connection to ' + url + ' reset by peer')
    except ConnectionAbortedError:
        print(str(datetime.datetime.now()) + ': Connection to ' + url + ' aborted (likely lost wifi connection)')

    # No time to retry if connection fails in production, just rerun code
    print(str(datetime.datetime.now()) + ': Finished as unable to connect to API (on first attempt)')
    exit()


def getGameIds(season):
    gameIds = []
    nhlUrl = 'https://statsapi.web.nhl.com/api/v1/schedule?season=' + str(season) + str(season + 1)

    nhlJson = accessAPI(nhlUrl)

    nhlDict = json.loads(nhlJson)

    for dates in nhlDict['dates']:
        for game in dates['games']:
            gameIds.append(str(game['gamePk']))

    # Only keep regular season games
    gameIds = [gameId for gameId in gameIds if int(gameId[5:6]) == 2]

    gameIds.sort(reverse=False)

    return gameIds


def getBaseGameInformation(gameId, isCurrent):
    baseInformation = pd.DataFrame()
    nhlUrl = 'https://statsapi.web.nhl.com/api/v1/game/' + gameId + '/feed/live'

    nhlJson = accessAPI(nhlUrl)

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


def generateBettingMatrix(season):
    gameList = getGameIds(season)
    trainingData = pd.DataFrame()

    for gameId in gameList:
        trainingData = pd.concat([trainingData, getBaseGameInformation(gameId, False)], sort=True, ignore_index=False)

    trainingData['game.winner'] = trainingData.apply(lambda row: getWinner(row), axis=1)

    # Get list of teams
    teamList = list(set(trainingData['team.id']))
    teamList.sort()

    # Calculate probability home team wins given some goal difference from previous encounter
    winProbDict = {}

    for trainingDataIter in range(0, len(trainingData), 2):
        regGameIds = [trainingData.iloc[trainingDataIter].name, trainingData.iloc[trainingDataIter + 1].name]
        regTeams = [trainingData.loc[regGameIds[0], 'team.id'], trainingData.loc[regGameIds[1], 'team.id']]
        goalDiff = trainingData.loc[regGameIds[0], 'goals'] - trainingData.loc[regGameIds[1], 'goals']

        # Take all games that occurred after the current game
        restricted = trainingData.loc[trainingData.index.get_level_values(0).astype(int) > int(regGameIds[0][0])]

        for restrictedIter in range(0, len(restricted), 2):
            if restricted['team.id'].iloc[restrictedIter] == regTeams[0] and restricted['team.id'].iloc[restrictedIter + 1] == regTeams[1]:
                # Win = 1, Tie = 0.5, Lose = 0 so that the sum of wins/ties/loses of all teams equals games played
                winProb = (restricted['game.winner'].iloc[restrictedIter] + 1) / 2

                try:
                    winProbDict[goalDiff]['wins'] += winProb
                    winProbDict[goalDiff]['games'] += 1
                except KeyError:
                    winProbDict[goalDiff] = {}
                    winProbDict[goalDiff]['wins'] = winProb
                    winProbDict[goalDiff]['games'] = 1

                # Removing the break statement changes the probability to be the home team winning all future
                # games given a goal difference. It weights later games more and favours teams that improve but
                # empirically, there seems to be no difference
                break

    # Put data in DataFrame, with one row for each game
    weightedWinProb = pd.DataFrame()

    for key in winProbDict:
        winTemp = pd.DataFrame({'goalDiff': [key],
                                'winProb': [winProbDict[key]['wins'] / winProbDict[key]['games']]})

        weightedWinProb = pd.concat([weightedWinProb, winTemp], sort=True, ignore_index=True)

    # Fit curve for win by goal difference
    goalDiffWinParams, pcov = curve_fit(winProbFunc, weightedWinProb['goalDiff'], weightedWinProb['winProb'])

    print(str(datetime.datetime.now()) + ': ' + str(season) +
          ' season win by goal difference function is e^-(' + str(goalDiffWinParams[0]) + 'x + ' +
          str(goalDiffWinParams[1]) + ')/(1 + e^-(' + str(goalDiffWinParams[0]) + 'x + ' +
          str(goalDiffWinParams[1]) + '))')

    # Construct transition probabilities matrix
    transitionProbs = [[0 for row in range(0, len(teamList) * 2)] for column in range(0, len(teamList) * 2)]
    gamesCount = [0 for row in range(0, len(teamList) * 2)]

    for trainingDataIter in range(0, len(trainingData), 2):
        regGameIds = [trainingData.iloc[trainingDataIter].name, trainingData.iloc[trainingDataIter + 1].name]
        regTeams = [trainingData.loc[regGameIds[0], 'team.id'], trainingData.loc[regGameIds[1], 'team.id']]
        goalDiff = trainingData.loc[regGameIds[0], 'goals'] - trainingData.loc[regGameIds[1], 'goals']
        winProb = winProbFunc(goalDiff, goalDiffWinParams[0], goalDiffWinParams[1])

        # Matrix is filled such that the 2k^th row is for team k at home and 2k+1 for team k away
        transitionIndices = [teamList.index(regTeams[0]) * 2, teamList.index(regTeams[1]) * 2 + 1]

        # Need to update transition probabilities from: home->home, away->away, home->away, away->home
        for row in transitionIndices:
            for column in transitionIndices:
                transitionProbs[row][column] += (1 - winProb) if column == transitionIndices[1] else winProb

            gamesCount[row] += 1

    for row in range(0, len(transitionProbs)):
        for column in range(0, len(transitionProbs)):
            transitionProbs[row][column] /= gamesCount[row]

    # Calculate steady-state probabilities via: v*T = v and sum(v) = 1
    for row in range(0, len(transitionProbs)):
        # Subtract 1 from diagonals so right side of function is constant
        transitionProbs[row][row] -= 1

    # Format the matrix as system of equations for numpy's linear algebra solver
    A = np.array(transitionProbs).transpose()

    # Drop the last row so matrix is square
    A = A[:-1]

    # Combine the two equations
    A = np.append(A, [[1 for column in range(0, len(transitionProbs))]], axis=0)
    b = np.array([0 for column in range(0, len(transitionProbs) - 1)] + [1])

    rawSteadyStates = np.linalg.solve(A, b)

    # Label the steady-states
    steadyStateDict = {}
    for team in teamList:
        steadyStateDict[team] = {}

        for side in ['home', 'away']:
            sideCount = 0 if side == 'home' else 1
            steadyStateDict[team][side] = rawSteadyStates[teamList.index(team) * 2 + sideCount]

    # Calculate probability home team wins given steady state difference
    steadyWeightedWinProbDict = {}

    for trainingDataIter in range(0, len(trainingData), 2):
        regGameIds = [trainingData.iloc[trainingDataIter].name, trainingData.iloc[trainingDataIter + 1].name]
        regTeams = [trainingData.loc[regGameIds[0], 'team.id'], trainingData.loc[regGameIds[1], 'team.id']]
        steadyDiff = steadyStateDict[regTeams[0]]['home'] - steadyStateDict[regTeams[1]]['away']

        try:
            steadyWeightedWinProbDict[steadyDiff]['wins'] += (trainingData.loc[regGameIds[0], 'game.winner'] + 1) / 2
            steadyWeightedWinProbDict[steadyDiff]['games'] += 1
        except KeyError:
            steadyWeightedWinProbDict[steadyDiff] = {}
            steadyWeightedWinProbDict[steadyDiff]['wins'] = (trainingData.loc[regGameIds[0], 'game.winner'] + 1) / 2
            steadyWeightedWinProbDict[steadyDiff]['games'] = 1

    # Put data in DataFrame, with one row for each game
    steadyWeightedWinProb = pd.DataFrame()

    for key in steadyWeightedWinProbDict:
        winTemp = pd.DataFrame({'steadyStateDiff': [key],
                                'winProb': [steadyWeightedWinProbDict[key]['wins'] / steadyWeightedWinProbDict[key]['games']]})

        steadyWeightedWinProb = pd.concat([steadyWeightedWinProb, winTemp], sort=True, ignore_index=True)

    # Fit curve for win by steady-state difference
    steadyDiffWinParams, pcov = curve_fit(winProbFunc, steadyWeightedWinProb['steadyStateDiff'],
                                          steadyWeightedWinProb['winProb'])

    print(str(datetime.datetime.now()) + ': ' + str(season) +
          ' season win by steady-state difference function is e^-(' + str(steadyDiffWinParams[0]) + 'x + ' +
          str(steadyDiffWinParams[1]) + ')/(1 + e^-(' + str(steadyDiffWinParams[0]) + 'x + ' +
          str(steadyDiffWinParams[1]) + '))')

    betMatrix = pd.DataFrame(0, index=[teamNum + '_home' for teamNum in teamList],
                             columns=[teamNum + '_away' for teamNum in teamList])

    for column in teamList:
        teamSSDiffs = [steadyStateDict[teamNum]['home'] - steadyStateDict[column]['away'] for teamNum in teamList]

        betMatrix[column + '_away'] = [winProbFunc(diff, steadyDiffWinParams[0], steadyDiffWinParams[1]) for diff in teamSSDiffs]

    return betMatrix


def getWager(odds, wagerMultiplier):
    currentGameId = odds.index.get_level_values(0)[0]
    season = int(currentGameId[:4])
    modelFileName = 'BetMatrix' + str(season) + '.csv'

    # If game is not a playoff game, we do not wager on it
    if int(currentGameId[4:6]) != 3:
        return ['', -1, '', 0, 'RegularTime']

    # Format odds file for processing
    odds.loc[(currentGameId, 'away'), :] = [odds.loc[(currentGameId, 'home'), 'oppTeam.odds'],
                                            odds.loc[(currentGameId, 'home'), 'tie.odds'],
                                            odds.loc[(currentGameId, 'home'), 'currTeam.odds']]

    try:
        with open(modelFileName, mode='r') as dataFile:
            betMatrix = pd.read_csv(dataFile, encoding='utf-8', index_col=0)
            betMatrix.index = betMatrix.index.astype(str)
    except FileNotFoundError:
        betMatrix = generateBettingMatrix(season)

        # Print results
        with open(modelFileName, mode='w+') as dataFile:
            betMatrix.to_csv(dataFile, encoding='utf-8', index=True)

    gameData = pd.concat([odds, getBaseGameInformation(currentGameId, True)], axis=1)

    homeWinProb = betMatrix[gameData['team.id'][1] + '_away'][gameData['team.id'][0] + '_home']

    # Calculate the pseudo expected return
    ex = [homeWinProb * gameData.loc[(currentGameId, 'home'), 'currTeam.odds'] - 1,
          (1 - homeWinProb) * gameData.loc[(currentGameId, 'home'), 'oppTeam.odds'] - 1]

    if ex[0] >= ex[1] > 0:
        return [gameData.loc[(currentGameId, 'home'), 'team.name'],
                gameData.loc[(currentGameId, 'home'), 'team.id'],
                'away',
                gameData.loc[(currentGameId, 'home'), 'currTeam.odds'] * wagerMultiplier,
                'RegularTime']
    elif ex[1] > ex[0] > 0:
        return [gameData.loc[(currentGameId, 'away'), 'team.name'],
                gameData.loc[(currentGameId, 'away'), 'team.id'],
                'away',
                gameData.loc[(currentGameId, 'home'), 'oppTeam.odds'] * wagerMultiplier,
                'RegularTime']
    else:
        return ['', -1, '', 0, 'RegularTime']


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    with open('GameOdds.csv', mode='r') as dataFile:
        gameOdds = pd.read_csv(dataFile, encoding='utf-8', index_col=[0, 1])
        gameOdds.index = [gameOdds.index.get_level_values(0).astype(str), gameOdds.index.get_level_values(1)]

    teamName, teamId, side, wagerNotional, wagerType = getWager(gameOdds, 100)

    print(teamName + ' (' + side + ')')
    print(wagerNotional)

    print(str(datetime.datetime.now()) + ': Finished')
