import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import f_oneway
import datetime


'''
Author: Jonathan Chow
Date Modified: 2019-08-24
Python Version: 3.7

Exploration of long-shot bias in NHL odds
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


def calculateReturns(side, winner, odds):
    if side == 'favourite':
        applicableOdds = min(odds[0], odds[2])
    elif side == 'nonfavourite':
        applicableOdds = max(odds[0], odds[2])
    else:
        applicableOdds = odds[1]

    if 1 - odds.index(applicableOdds) == winner:
        return applicableOdds - 1
    else:
        return -1


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

    trainingData = pd.DataFrame()
    completeData = pd.DataFrame()

    trainingColumns = ['home', 'away',
                       'currTeam.odds', 'tie.odds', 'oppTeam.odds',
                       'game.type',
                       'team.name', 'team.id',
                       'goals', 'game.winner']

    outputColumns = ['currTeam.odds', 'tie.odds', 'oppTeam.odds',
                     'game.winner']

    acceptableBookmakers = ['bet365', 'William Hill', 'Bethard']

    for season in seasonList:
        try:
            trainingData = readHistoricalGameData(season)
            trainingData = mergeOdds(trainingData, getOdds(season), acceptableBookmakers)
            trainingData = trainingData[trainingColumns]
            trainingData.fillna(0, inplace=True)

            trainingData['game.winner'] = trainingData.apply(lambda row: getWinner(row), axis=1)

            # Remove redundant data, inconclusive data, and rows without odds available
            trainingData = trainingData.loc[trainingData['currTeam.odds'] != 0]
            trainingData = trainingData.loc[trainingData['currTeam.odds'] != trainingData['oppTeam.odds']]
            trainingData = trainingData[::2]

            # Concatenate results with other years
            completeData = pd.concat([completeData, trainingData[outputColumns]], sort=True, ignore_index=False)

            print(str(datetime.datetime.now()) + ': Finished ' + str(season))
        except FileNotFoundError:
            print(str(datetime.datetime.now()) + ': Error reading one or more files from season ' + str(season))

    # Calculate returns for each game for each side
    for side in ['favourite', 'tie', 'nonfavourite']:
        completeData[side + '.WagerReturns'] = completeData.apply(lambda row: calculateReturns(side,
                                                                                       row['game.winner'],
                                                                                       [row['currTeam.odds'], row['tie.odds'], row['oppTeam.odds']]), axis=1)

    # Compute anova of the means
    ftest, pval = f_oneway(completeData['favourite.WagerReturns'],
                           completeData['tie.WagerReturns'],
                           completeData['nonfavourite.WagerReturns'])

    print('P-Value: ' + str(pval))
    print('F-Statistic: ' + str(ftest))

    # Graph mean of wager returns (expected return per wager)
    fig = plt.plot()
    plt.title('Expected Return Betting on Favourite/Tie/Non-Favourite\np < {:.3}, SEM Error Bars'.format(pval))
    plt.ylabel('Expected Return per Wager (CAD $)')

    x = np.array(['Favourite', 'Tie', 'Non-Favourite'])
    y = np.array([completeData['favourite.WagerReturns'].mean(),
                  completeData['tie.WagerReturns'].mean(),
                  completeData['nonfavourite.WagerReturns'].mean()])
    e = np.array([np.std(completeData['favourite.WagerReturns']),
                  np.std(completeData['tie.WagerReturns']),
                  np.std(completeData['nonfavourite.WagerReturns'])])

    plt.errorbar(x, y, e, linestyle='None', capsize=5, marker='o')
    plt.tight_layout()

    plt.savefig('ExpectedReturnPlot.png', dpi=500)

    # Print results
    with open('HistoricalPerformanceRaw.csv', mode='w+') as dataFile:
        completeData.to_csv(dataFile, encoding='utf-8', index=True)

    print(str(datetime.datetime.now()) + ': Finished')
