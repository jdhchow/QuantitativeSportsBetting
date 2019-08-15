import datetime
import pandas as pd


'''
Author: Jonathan Chow
Date Modified: 2019-08-12
Python Version: 3.7

Generate wager for Markov playoff strategy. Only manual requirement are maximum odds (from legitimate bookmakers) for
the game.

It would probably beneficial to force attributes of the production and backtest code to be the same (i.e. which
bookmakers are considered legitimate, starting capital, ...)

Allowed Bookmakers:
    - William Hill
    - Bet365
    - BetHard

Starting Capital: $6000
'''


def getWager(odds):
    currentGameId = odds.index[0]
    season = int(currentGameId[:4])
    modelFileName = 'BetMatrix' + str(season) + '.csv'

    try:
        with open(modelFileName, mode='r') as dataFile:
            betMatrix = pd.read_csv(dataFile, encoding='utf-8', index_col=0)
    except FileNotFoundError:

    gameData = pd.concat([gameData, getBaseGameInformation(currentGameId, True)], axis=1)

    homeWinProb = betMatrix[gameData['team.id'][1] + '_away'][gameData['team.id'][0] + '_home']

    if homeWinProb > 0.5:
        return ['home', gameData['team.id'][0], gameData['currTeam.oddsMax'][0]]
    else:
        return ['away', gameData['team.id'][1], gameData['oppTeam.oddsMax'][0]]



if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    with open('GameOdds.csv', mode='r') as dataFile:
        gameOdds = pd.read_csv(dataFile, encoding='utf-8', index_col=0)

    teamName, teamId, side, wagerNotional = getWager(gameOdds)

    print(teamName + ' (' + side + ')')
    print(wagerNotional)
