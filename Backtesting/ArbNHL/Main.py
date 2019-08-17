import numpy as np
import pandas as pd
from scipy.optimize import linprog
import matplotlib.pyplot as plt
import datetime


'''
Author: Jonathan Chow
Date Modified: 2019-08-17
Python Version: 3.7

Reads in maximum odds are determines whether there is arbitrage potential.
'''


def getWinner(data):
    # Mapping for each row is: Win = 1, Tie = 0, Lose = -1
    if (data['game.winner'] == 'home' and data['home'] == 1) or (data['game.winner'] == 'away' and data['home'] == 0):
        winner = 1
    elif data['game.winner'] == 'tie':
        winner = 0
    else:
        winner = -1

    return winner


def readHistoricalGameData(season):
    with open('HistoricalGameData/Season' + str(season) + '.csv', mode='r') as dataFile:
        data = pd.read_csv(dataFile, encoding='utf-8', index_col=[0, 1])
        data.index = [data.index.get_level_values(0).astype(str), data.index.get_level_values(1)]

    return data


def getOdds(season):
    # Odds scraped from OddsPortal (e.g. http://www.oddsportal.com/hockey/usa/nhl-2015-2016/results/#/page/4/)
    bookmakerOdds = pd.read_json('HistoricalOdds/Season' + str(season) + '.json')
    bookmakerOdds['date'] = pd.to_datetime(bookmakerOdds['day'] + ' ' + bookmakerOdds['time'], format='%d %b %Y %H:%M')
    bookmakerOdds.drop(['day', 'time'], axis=1, inplace=True)
    bookmakerOdds = bookmakerOdds.loc[bookmakerOdds['pre-season'] == False]

    return bookmakerOdds


def mergeOdds(trainingData, bookmakerOdds, allowedBookmakers):
    oddsDict = {'currTeam.odds': [], 'oppTeam.odds': [], 'tie.odds': []}

    teamTable = pd.concat([trainingData['team.name'].rename('home'), trainingData['team.name'].shift(-1).rename('away'),
                           trainingData['game.date']], axis=1).iloc[::2, :]

    for key in list(oddsDict.keys()):
        oddsDict[key] = list(teamTable.apply(lambda row: mergeOddsHelper(row, bookmakerOdds, key, allowedBookmakers), axis=1))
        oddsDict[key] = [item for sublist in oddsDict[key] for item in sublist]

        trainingData[key] = oddsDict[key]

    return trainingData


def mergeOddsHelper(row, odds, side, allowedBookmakers):
    restricted = odds.loc[(odds['home'] == row['home']) & (odds['away'] == row['away']) &
                          ((odds['date'] + datetime.timedelta(hours=10)) >= row['game.date']) &
                          ((odds['date'] - datetime.timedelta(hours=10)) <= row['game.date'])]

    if restricted.empty:
        return [0, 0]

    if 'currTeam' in side:
        euroOdd = [max([0] + [value['home.odds'] for key, value in (restricted['odds'].iloc[0]).items() if key in allowedBookmakers])]
        euroOdd = euroOdd + [max([0] + [value['away.odds'] for key, value in (restricted['odds'].iloc[0]).items() if key in allowedBookmakers])]
    elif 'oppTeam' in side:
        euroOdd = [max([0] + [value['away.odds'] for key, value in (restricted['odds'].iloc[0]).items() if key in allowedBookmakers])]
        euroOdd = euroOdd + [max([0] + [value['home.odds'] for key, value in (restricted['odds'].iloc[0]).items() if key in allowedBookmakers])]
    else:
        euroOdd = [max([0] + [value['tie.odds'] for key, value in (restricted['odds'].iloc[0]).items() if key in allowedBookmakers])] * 2

    if len(restricted) > 1:
        print(str(datetime.datetime.now()) + ': Merging by time and teams not unique on ' + str(row['game.date']))

    return euroOdd


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    # seasonList = [2002, 2003, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]
    seasonList = [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]

    # Being with 5000 (CAD $)
    initialNotional = 5000

    trainingData = pd.DataFrame()
    completeData = pd.DataFrame()

    trainingColumns = ['home', 'away',
                       'currTeam.odds', 'tie.odds', 'oppTeam.odds',
                       'game.type',
                       'team.name', 'team.id',
                       'goals', 'game.winner']

    outputColumns = ['currTeam.odds', 'tie.odds', 'oppTeam.odds',
                     'game.winner',
                     'currTeam.wager', 'tie.wager', 'oppTeam.wager',
                     'WagerReturns']

    acceptableBookmakers = ['bet365', 'William Hill', 'Bethard']

    for season in seasonList:
        try:
            trainingData = readHistoricalGameData(season)
            trainingData = mergeOdds(trainingData, getOdds(season), acceptableBookmakers)
            trainingData = trainingData[trainingColumns]
            trainingData.fillna(0, inplace=True)

            trainingData['game.winner'] = trainingData.apply(lambda row: getWinner(row), axis=1)

            # Remove redundant data and rows without odds available
            trainingData = trainingData[::2]
            trainingData = trainingData.loc[trainingData['currTeam.odds'] != 0]

            # Generate predictions
            wagers = {}
            c = [0, 0, 0, -1]
            b = [0, 0, 0, 0, 0, 0, initialNotional]
            xi_bounds = (0, None)

            trainingDataDict = trainingData.to_dict(orient='index')

            for key, value in trainingDataDict.items():
                A = [[(value['currTeam.odds'] - 1), -1, -1, -1],
                     [-(value['currTeam.odds'] - 1), 1, 1, 1],
                     [-1, (value['tie.odds'] - 1), -1, -1],
                     [1, -(value['tie.odds'] - 1), 1, 1],
                     [-1, -1, (value['oppTeam.odds'] - 1), -1],
                     [1, 1, -(value['oppTeam.odds'] - 1), 1],
                     [1, 1, 1, 0]]

                res = linprog(c, A_ub=A, b_ub=b, bounds=[xi_bounds, xi_bounds, xi_bounds, xi_bounds])

                wagers[key] = {'WagerReturns': -res['fun']}
                wagers[key]['currTeam.wager'], wagers[key]['tie.wager'], wagers[key]['oppTeam.wager'] = res['x'][:3]

            trainingData = pd.concat([trainingData, pd.DataFrame(wagers).transpose()], sort=True, ignore_index=False, axis=1)

            # Concatenate results with other years
            completeData = pd.concat([completeData, trainingData[outputColumns]], sort=True, ignore_index=False)

            print(str(datetime.datetime.now()) + ': Finished ' + str(season))
        except FileNotFoundError:
            print(str(datetime.datetime.now()) + ': Error reading one or more files from season ' + str(season))

    # Add initial fund size and split returns by season
    cumulativeWagerReturns = [[initialNotional]]

    for season in seasonList:
        cumulativeWagerReturns.append(list(completeData.loc[completeData.index.get_level_values(0).str[:4].astype(int) == season, 'WagerReturns']))

    # Calculate cumulative returns
    for seasonIter in range(1, len(cumulativeWagerReturns)):
        cumulativeWagerReturns[seasonIter] = np.cumsum([cumulativeWagerReturns[seasonIter - 1][-1]] + cumulativeWagerReturns[seasonIter])

    # Graph returns over time
    plt.figure(figsize=(10, 5))

    xAxisCounter = 0
    colourList = ['#015482', '#95D0FC', '#5E819D'] * int(np.ceil(len(seasonList) / 3))

    for returnIter in range(1, len(cumulativeWagerReturns)):
        plt.plot(list(range(xAxisCounter, xAxisCounter + len(cumulativeWagerReturns[returnIter]))), cumulativeWagerReturns[returnIter], c=colourList[returnIter - 1])

        xAxisCounter += len(cumulativeWagerReturns[returnIter]) - 1

    plt.xlabel('Game Number')
    plt.ylabel('Notional (CAD $)')
    plt.title('Markov Chain Model Cumulative Returns (2009-2018)')
    plt.savefig('Analysis/CumulativeReturns.png', dpi=500)

    # Print results
    with open('Analysis/HistoricalPerformanceRaw.csv', mode='w+') as dataFile:
        completeData.to_csv(dataFile, encoding='utf-8', index=True)

    print(str(datetime.datetime.now()) + ': Finished')
