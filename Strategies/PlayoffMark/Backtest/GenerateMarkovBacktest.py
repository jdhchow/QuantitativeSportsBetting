import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import datetime


'''
Author: Jonathan Chow
Date Modified: 2019-01-25
Python Version: 3.7

Each team at each side is a state (i.e. Boston Bruins Home, Boston Bruins Away, Ottawa Senators Home, ...). Calculate
the probability that the home team beats the away team, given that the previous game between the two had a goal
difference of x = home goals - away goals. Fit a function over these probabilities and use it to calculate transition
probabilities between states. Calculate steady-state for each team/side. Calculate the probability the home team wins
given the teams playing have an x = home steady-state - away steady-state difference. Use logistic regression to fit a
curve over this. Predict playoff games by calculating team steady states and plugging their difference into the curve.

Procedure follows the below paper very closely:
Kvam, Paul H. and Sokol, Joel, "A Logistic Regression/Markov Chain Model for NCAA Basketball" (2006). Math and Computer
Science Faculty Publications. 200. https://scholarship.richmond.edu/mathcs-faculty-publications/200
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


def calculateReturns(prediction, winner, currOdds, oppOdds, wager):
    applicableOdds = currOdds if prediction == 1 else oppOdds

    if prediction == winner:
        return (applicableOdds - 1) * applicableOdds * wager
    else:
        return -applicableOdds * wager


def readHistoricalGameData(season):
    with open('DataCollection/NHLAPIScraper/HistoricalGameData/Season' + str(season) + '.csv', mode='r') as dataFile:
        data = pd.read_csv(dataFile, encoding='utf-8', index_col=[0, 1])
        data.index = [data.index.get_level_values(0).astype(str), data.index.get_level_values(1)]

    return data


def getOdds(season):
    # Odds scraped from OddsPortal (e.g. http://www.oddsportal.com/hockey/usa/nhl-2015-2016/results/#/page/4/)
    bookmakerOdds = pd.read_json('DataCollection/OddsPortalScraper/HistoricalOdds/Season' + str(season) + '.json')
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

    # Wager 100 * odds (CAD $)
    wagerAmount = 100

    # Being with 2000 (CAD $)
    initialNotional = 2000

    trainingData = pd.DataFrame()
    completePlayoff = pd.DataFrame()

    trainingColumns = ['home', 'away',
                       'currTeam.odds', 'tie.odds', 'oppTeam.odds',
                       'game.type',
                       'team.name', 'team.id',
                       'goals', 'game.winner']

    outputColumns = ['currTeam.odds', 'tie.odds', 'oppTeam.odds',
                     'game.winner', 'predictions']

    acceptableBookmakers = ['bet365', 'William Hill', 'Bethard', 'bet-at-home', 'bwin', 'Unibet',
                            '1xBet', '18Bet', 'Marathonbet', 'Coolbet']

    for season in seasonList:
        try:
            trainingData = readHistoricalGameData(season)
            trainingData = mergeOdds(trainingData, getOdds(season), acceptableBookmakers)
            trainingData = trainingData[trainingColumns]
            trainingData.fillna(0, inplace=True)

            trainingData['game.winner'] = trainingData.apply(lambda row: getWinner(row), axis=1)

            # Remove rows without odds available (not needed for this model, but kept for consistency with others)
            trainingData = trainingData.loc[trainingData['currTeam.odds'] != 0]

            # Split data into regular season and playoffs
            reg, playoff = trainingData.loc[trainingData['game.type'] == 'R'].copy(), \
                           trainingData.loc[trainingData['game.type'] == 'P'].copy()

            # Get list of teams
            teamList = list(set(reg['team.id']))
            teamList.sort()

            # Calculate probability home team wins given some goal difference from previous encounter
            winProbDict = {}

            for regIter in range(0, len(reg), 2):
                regGameIds = [reg.iloc[regIter].name, reg.iloc[regIter + 1].name]
                regTeams = [reg.loc[regGameIds[0], 'team.id'], reg.loc[regGameIds[1], 'team.id']]
                goalDiff = reg.loc[regGameIds[0], 'goals'] - reg.loc[regGameIds[1], 'goals']

                # Take all games that occurred after the current game
                restricted = reg.loc[reg.index.get_level_values(0).astype(int) > int(regGameIds[0][0])]

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

            # Put data in DataFrame, with one row for each game (few differences, so weight common ones more)
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

            # Graph win by goal difference
            # plt.figure()
            #
            # curveColour = '#95D0FC'
            # scatterColour = '#5E819D'
            # curveXAxis = np.arange(-10, 10, 0.01)
            #
            # plt.plot(list(weightedWinProb['goalDiff']), list(weightedWinProb['winProb']), 'o', c=scatterColour)
            # plt.plot(curveXAxis, winProbFunc(curveXAxis, goalDiffWinParams[0], goalDiffWinParams[1]), c=curveColour)
            #
            # plt.xlabel('Previous Game Goal Difference')
            # plt.ylabel('Win Probability')
            # plt.title('Win Probability by Previous Game Goal Difference (2017)')
            # plt.show()

            # Construct transition probabilities matrix
            transitionProbs = [[0 for row in range(0, len(teamList) * 2)] for column in range(0, len(teamList) * 2)]
            gamesCount = [0 for row in range(0, len(teamList) * 2)]

            for regIter in range(0, len(reg), 2):
                regGameIds = [reg.iloc[regIter].name, reg.iloc[regIter + 1].name]
                regTeams = [reg.loc[regGameIds[0], 'team.id'], reg.loc[regGameIds[1], 'team.id']]
                goalDiff = reg.loc[regGameIds[0], 'goals'] - reg.loc[regGameIds[1], 'goals']
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

            for regIter in range(0, len(reg), 2):
                regGameIds = [reg.iloc[regIter].name, reg.iloc[regIter + 1].name]
                regTeams = [reg.loc[regGameIds[0], 'team.id'], reg.loc[regGameIds[1], 'team.id']]
                steadyDiff = steadyStateDict[regTeams[0]]['home'] - steadyStateDict[regTeams[1]]['away']

                try:
                    steadyWeightedWinProbDict[steadyDiff]['wins'] += (reg.loc[regGameIds[0], 'game.winner'] + 1) / 2
                    steadyWeightedWinProbDict[steadyDiff]['games'] += 1
                except KeyError:
                    steadyWeightedWinProbDict[steadyDiff] = {}
                    steadyWeightedWinProbDict[steadyDiff]['wins'] = (reg.loc[regGameIds[0], 'game.winner'] + 1) / 2
                    steadyWeightedWinProbDict[steadyDiff]['games'] = 1

            # Put data in DataFrame, with one row for each game (few differences, so weight common ones more)
            steadyWeightedWinProb = pd.DataFrame()

            for key in steadyWeightedWinProbDict:
                winTemp = pd.DataFrame({'steadyStateDiff': [key],
                                        'winProb': [steadyWeightedWinProbDict[key]['wins'] / steadyWeightedWinProbDict[key]['games']]})

                steadyWeightedWinProb = pd.concat([steadyWeightedWinProb, winTemp], sort=True, ignore_index=True)

            # Fit curve for win by steady-state difference
            steadyDiffWinParams, pcov = curve_fit(winProbFunc, steadyWeightedWinProb['steadyStateDiff'], steadyWeightedWinProb['winProb'])

            print(str(datetime.datetime.now()) + ': ' + str(season) +
                  ' season win by steady-state difference function is e^-(' + str(steadyDiffWinParams[0]) + 'x + ' +
                  str(steadyDiffWinParams[1]) + ')/(1 + e^-(' + str(steadyDiffWinParams[0]) + 'x + ' +
                  str(steadyDiffWinParams[1]) + '))')

            # Graph win by steady-state difference
            # plt.figure()
            #
            # curveColour = '#95D0FC'
            # scatterColour = '#5E819D'
            # curveXAxis = np.arange(0.00125, 0.0125, 0.001)
            #
            # plt.plot(list(steadyWeightedWinProb['steadyStateDiff']), list(steadyWeightedWinProb['winProb']), 'o', c=scatterColour)
            # plt.plot(curveXAxis, winProbFunc(curveXAxis, steadyDiffWinParams[0], steadyDiffWinParams[1]), c=curveColour)
            #
            # plt.xlabel('Steady-State Difference')
            # plt.ylabel('Win Probability')
            # plt.title('Win Probability by Steady-State Difference (2017)')
            # plt.show()

            # Generate predictions
            predictions = []

            for playoffIter in range(0, len(playoff), 2):
                playoffGameIds = [playoff.iloc[playoffIter].name, playoff.iloc[playoffIter + 1].name]
                playoffTeams = [playoff.loc[playoffGameIds[0], 'team.id'], playoff.loc[playoffGameIds[1], 'team.id']]
                steadyDiff = steadyStateDict[playoffTeams[0]]['home'] - steadyStateDict[playoffTeams[1]]['away']

                predWinner = 1 if winProbFunc(steadyDiff, steadyDiffWinParams[0], steadyDiffWinParams[1]) > 0.5 else -1

                predictions.append(predWinner)

            # Remove redundancy
            playoff = playoff[::2]
            playoff['predictions'] = predictions

            # Concatenate results with other years
            completePlayoff = pd.concat([completePlayoff, playoff[outputColumns]], sort=True, ignore_index=False)

            print(str(datetime.datetime.now()) + ': Finished ' + str(season))
        except FileNotFoundError:
            print(str(datetime.datetime.now()) + ': Error reading one or more files from season ' + str(season))

    # Calculate returns for each game
    completePlayoff['WagerReturns'] = completePlayoff.apply(lambda row: calculateReturns(row['predictions'],
                                                                                         row['game.winner'],
                                                                                         row['currTeam.odds'],
                                                                                         row['oppTeam.odds'],
                                                                                         wagerAmount), axis=1)

    # Add initial fund size and split returns by season
    cumulativeWagerReturns = [[initialNotional]]

    for season in seasonList:
        cumulativeWagerReturns.append(list(completePlayoff.loc[completePlayoff.index.get_level_values(0).str[:4].astype(int) == season, 'WagerReturns']))

    # Calculate cumulative returns
    for seasonIter in range(1, len(cumulativeWagerReturns)):
        cumulativeWagerReturns[seasonIter] = np.cumsum([cumulativeWagerReturns[seasonIter - 1][-1]] + cumulativeWagerReturns[seasonIter])

    # Graph returns over time
    plt.figure(figsize=(10, 8))

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
    with open('Analysis/HistoricalPerformance.csv', mode='w+') as dataFile:
        completePlayoff.to_csv(dataFile, encoding='utf-8', index=True)

    print(str(datetime.datetime.now()) + ': Finished')
