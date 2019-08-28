import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime


'''
Author: Jonathan Chow
Date Modified: 2019-08-25
Python Version: 3.7

Bets against non-favourites that have not been rested adequately
'''


def getWinner(winnerSide, otWinnerSide, side):
    # Mapping for each row is: Win = 1, Tie = 0, Lose = -1
    if (winnerSide == 'home' and side == 1) or (winnerSide == 'away' and side == 0):
        winner = 1
    elif winnerSide == 'tie':
        if (otWinnerSide == 'home' and side == 1) or (otWinnerSide == 'away' and side == 0):
            winner = 1
        else:
            winner = 0.5
    else:
        winner = 0

    return winner


def calculateReturns(prediction, winner, currOdds, oppOdds, wager):
    if prediction == 0:
        return 0

    applicableOdds = currOdds if prediction == 1 else oppOdds

    if prediction == winner:
        return (applicableOdds - 1) * applicableOdds * wager
    else:
        return -applicableOdds * wager


def readHistoricalGameData(season):
    with open('HistoricalGameDataOT/Season' + str(season) + '.csv', mode='r') as dataFile:
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


def checkOnBubble(ranking, currGameHome, currGameAway):
    updatedRanking = ranking.copy()



    return 0, updatedRanking


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    # seasonList = [2013, 2014, 2015, 2016, 2017, 2018]
    seasonList = [2018]

    # Wager 100 * odds (CAD $)
    wagerAmount = 100

    # Being with 5000 (CAD $)
    initialNotional = 5000

    trainingData = pd.DataFrame()
    completeData = pd.DataFrame()

    trainingColumns = ['home', 'away',
                       'currTeam.odds', 'tie.odds', 'oppTeam.odds',
                       'game.date',
                       'game.type',
                       'conference.id', 'division.id',
                       'final.period',
                       'pulledGoalie', 'shootout',
                       'team.name', 'team.id',
                       'goals', 'game.winner', 'game.ot.winner']

    outputColumns = ['currTeam.odds', 'tie.odds', 'oppTeam.odds',
                     'game.date',
                     'gameTimeDiff',
                     'game.winner',
                     'predictions']

    acceptableBookmakers = ['bet365', 'William Hill', 'Bethard']

    for season in seasonList:
        try:
            trainingData = readHistoricalGameData(season)

            trainingData['game.date'] = pd.to_datetime(trainingData['game.date'], format='%Y-%m-%d %H:%M:%S')

            trainingData = mergeOdds(trainingData, getOdds(season), acceptableBookmakers)
            trainingData = trainingData[trainingColumns]
            trainingData.fillna(0, inplace=True)

            trainingData['game.winner'] = trainingData.apply(lambda row: getWinner(row['game.winner'], row['game.ot.winner'], row['home']), axis=1)

            # Remove redundant data and rows without odds available
            # trainingData = trainingData.loc[trainingData['currTeam.odds'] != 0]

            teamRanking = pd.DataFrame({team: {'Conference': (trainingData.loc[trainingData['team.id'] == team, 'conference.id']).iloc[0],
                                               'Division': (trainingData.loc[trainingData['team.id'] == team, 'division.id']).iloc[0],
                                               'Points': 0,
                                               'Wins': 0,
                                               'RemainingGames': 82,
                                               'PlayoffQualify': 0} for team in trainingData['team.id'].unique()}).transpose()

            # Generate running points
            trainingData = trainingData.sort_values(by='game.date', ascending=True)

            points = {}

            for teamId in trainingData['team.id'].unique():
                restricted = trainingData.loc[trainingData['team.id'] == teamId].copy()
                restricted['points'] = restricted['game.winner'] * 2
                restricted['points'] = restricted['points'].expanding().sum().shift(1)

                points.update(restricted['points'].to_dict())

            trainingData = pd.concat([trainingData, pd.DataFrame(points, index=['points']).transpose()], sort=True, ignore_index=False, axis=1)

            # Generate number of games won
            trainingData = trainingData.sort_values(by='game.date', ascending=True)

            gamesWon = {}

            for teamId in trainingData['team.id'].unique():
                restricted = trainingData.loc[trainingData['team.id'] == teamId].copy()
                restricted['gamesWon'] = restricted.apply(lambda row: 1 if row['game.winner'] == 1 and row['shootout'] == 0 else 0, axis=1)
                restricted['gamesWon'] = restricted['gamesWon'].expanding().sum().shift(1)

                gamesWon.update(restricted['gamesWon'].to_dict())

            trainingData = pd.concat([trainingData, pd.DataFrame(gamesWon, index=['gamesWon']).transpose()], sort=True, ignore_index=False, axis=1)

            # Calculate win rate for teams on the bubble
            trainingData = trainingData.sort_values(by='game.date', ascending=True)
            trainingData = trainingData.sort_index(level=[0, 1], ascending=[True, False])

            bubble = []

            for gameIndex in range(0, len(trainingData), 2):
                onBubble, teamRanking = checkOnBubble(teamRanking, trainingData.iloc[gameIndex], trainingData.iloc[gameIndex + 1])
                bubble += onBubble

            trainingData['onBubble'] = bubble

            # Sort dataframe to put home team first
            trainingData = trainingData.sort_index(level=[0, 1], ascending=[True, False])

            # Generate predictions
            predictions = []

            for gameIndex in range(0, len(trainingData), 2):
                if trainingData['onBubble'].iloc[gameIndex] == 1 and trainingData['onBubble'].iloc[gameIndex + 1] == 0:
                    predictions += [1]
                elif trainingData['onBubble'].iloc[gameIndex] == 0 and trainingData['onBubble'].iloc[gameIndex + 1] == 1:
                    predictions += [-1]
                else:
                    predictions += [0]

            # Remove redundancy
            # trainingData = trainingData[::2]
            trainingData['predictions'] = predictions
            # trainingData = trainingData.loc[trainingData['predictions'] != 0]

            # Concatenate results with other years
            completeData = pd.concat([completeData, trainingData[outputColumns]], sort=True, ignore_index=False)

            print(str(datetime.datetime.now()) + ': Finished ' + str(season))
        except FileNotFoundError:
            print(str(datetime.datetime.now()) + ': Error reading one or more files from season ' + str(season))

    # Calculate returns for each game
    completeData['WagerReturns'] = completeData.apply(lambda row: calculateReturns(row['predictions'],
                                                                                   row['game.winner'],
                                                                                   row['currTeam.odds'],
                                                                                   row['oppTeam.odds'],
                                                                                   wagerAmount), axis=1)

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
    plt.title('Worse Tired Model Cumulative Returns (2009-2018)')
    plt.savefig('Analysis/CumulativeReturns.png', dpi=500)

    # Print results
    with open('Analysis/HistoricalPerformanceRaw.csv', mode='w+') as dataFile:
        completeData.to_csv(dataFile, encoding='utf-8', index=True)

    print(str(datetime.datetime.now()) + ': Finished')
