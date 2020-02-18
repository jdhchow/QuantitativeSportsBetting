import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import ast
import copy

from Backtesting.SyntheticControl.tslib.src import tsUtils
from Backtesting.SyntheticControl.tslib.src.synthcontrol.multisyntheticControl import MultiRobustSyntheticControl
from Backtesting.SyntheticControl.tslib.src.synthcontrol.syntheticControl import RobustSyntheticControl


'''
Author: Jonathan Chow
Date Modified: 2020-02-16
Python Version: 3.7

Predicts the final score of the NBA playoff games after the first quarter using synthetic control.
'''


def arbRoundDown(x, base):
    return x // base * base


def readHistoricalGameData(season):
    with open('HistoricalGameData_WithOT/Season' + str(season) + '.csv', mode='r') as dataFile:
        data = pd.read_csv(dataFile, encoding='utf-8', index_col=[0, 1])
        data.index = [data.index.get_level_values(0).astype(str), data.index.get_level_values(1)]

    return data


def checkMatrixRank(keyId, trainingDF, graphId):
    # Check matrix is low rank
    (U, s, Vh) = np.linalg.svd((trainingDF) - np.mean(trainingDF))
    s2 = np.power(s, 2)
    spectrum = np.cumsum(s2) / np.sum(s2)

    plt.figure(figsize=(8, 6), dpi=100)
    plt.plot(spectrum)
    plt.grid()
    plt.xlabel("Ordered Singular Values")
    plt.ylabel("Energy Proportion")
    plt.title("Cumulative Energy")
    plt.savefig('Analysis/SVD/' + str(keyId) + '_' + graphId + 'CumulativeEnergy.png')
    plt.clf()
    plt.close()

    plt.figure(figsize=(8, 6), dpi=100)
    plt.plot(s2)
    plt.grid()
    plt.xlabel("Ordered Singular Values")
    plt.ylabel("Energy")
    plt.title("Singular Value Spectrum")
    plt.savefig('Analysis/SVD/' + str(keyId) + '_' + graphId + 'SingularValueSpectrum.png')
    plt.clf()
    plt.close()


def filterGames(numControls, keyId, homePoints, awayPoints):
    keyCurve = homePoints[keyId] - awayPoints[keyId]

    colNames = list(homePoints.columns)
    colNames.remove(keyId)

    errorList = []

    for colName in colNames:
        currCurve = homePoints[colName] - awayPoints[colName]
        error = np.sqrt(((keyCurve - currCurve) ** 2).mean())

        errorList += [(colName, error)]

    errorList.sort(key=lambda x: x[1])

    # print(str(datetime.datetime.now()) + ': Keeping ' + str(numControls) + ' controls (RMSE: ' +
    #       str(errorList[0][1]) + ' - ' + str(errorList[numControls][1]) + ')')

    controlsToKeep = [errorTuple[0] for errorTuple in errorList][:numControls]

    return controlsToKeep


def predictPointDiff(keyId, homePoints, awayPoints, timeBuckets, singularVals):
    trainQtr = 1
    metrics = 2
    weights = [1, 1]
    controlNum = 1000

    trainSeconds = trainQtr * 12 * 60  # Will break if training includes overtime

    # Select only games that have similar 1st qtr for the synthetic control
    otherKeys = filterGames(controlNum, playoffGame, copy.deepcopy(homePoints.loc[:trainSeconds]), copy.deepcopy(awayPoints.loc[:trainSeconds]))

    homePoints = homePoints[otherKeys + [keyId]]
    awayPoints = awayPoints[otherKeys + [keyId]]

    trainArray = [homePoints.loc[:trainSeconds],
                  awayPoints.loc[:trainSeconds]]

    testArray = [homePoints.loc[trainSeconds + timeBuckets:],
                 awayPoints.loc[trainSeconds + timeBuckets:]]

    plt.figure(figsize=(8, 6), dpi=100)

    ########### Multi-dimensional robust synthetic control ##########
    mrscModel = MultiRobustSyntheticControl(metrics, weights, keyId, singularVals, len(trainArray[0]),
                                            probObservation=1.0, modelType='svd', svdMethod='numpy',
                                            otherSeriesKeysArray=otherKeys)

    mrscModel.fit(trainArray)
    predictions = mrscModel.predict(testArray)

    denoisedDF = mrscModel.model.denoisedDF()
    denoisedSeries = denoisedDF[keyId].iloc[:int(len(denoisedDF)/2)] - denoisedDF[keyId].iloc[int(len(denoisedDF)/2):].values
    fullSeries = np.append(denoisedSeries, predictions[0] - predictions[1], axis=0)

    # Point Difference
    plt.plot(list(homePoints.index), homePoints[keyId] - awayPoints[keyId], color='tomato', label='Observations')
    plt.plot(list(homePoints.index), fullSeries, color='darkblue', label='Predictions')

    # Home Points
    # plt.plot(list(homePoints.index), homePoints[keyId], color='tomato', label='Observations')
    # plt.plot(list(homePoints.index), np.append(denoisedDF[keyId].iloc[:int(len(denoisedDF)/2)], predictions[0], axis=0),color='darkblue', label='Predictions')

    # Away Points
    # plt.plot(list(homePoints.index), awayPoints[keyId], color='tomato', label='Observations')
    # plt.plot(list(homePoints.index), np.append(denoisedDF[keyId].iloc[int(len(denoisedDF)/2):], predictions[1], axis=0), color='darkblue', label='Predictions')
    #################################################################

    ############### Singular robust synthetic control ###############
    # rscModel = RobustSyntheticControl(keyId, singularVals, len(homePoints.loc[:trainSeconds]),
    #                                   probObservation=1.0, modelType='svd', svdMethod='numpy',
    #                                   otherSeriesKeysArray=otherKeys)
    #
    # rscModel.fit(homePoints.loc[:trainSeconds])
    # denoisedDF = rscModel.model.denoisedDF()
    # predictions = rscModel.predict(homePoints.loc[trainSeconds + timeBuckets:])
    # fullSeries = np.append(denoisedDF[keyId], predictions, axis=0)
    #
    # plt.plot(list(homePoints.index), homePoints[keyId], color='tomato', label='Observations')
    # plt.plot(list(homePoints.index), np.append(denoisedDF[keyId], predictions, axis=0), color='darkblue', label='Predictions')
    #################################################################

    plt.axvline(x=trainSeconds - 1, linewidth=1, color='black', label='Intervention')

    # Lines to mark end of regular time and overtime
    plt.axvline(x=2880, linewidth=1, linestyle='--', color='black', label='Potential End of Game')
    plt.axvline(x=3180, linewidth=1, linestyle='--', color='black')
    plt.axvline(x=3480, linewidth=1, linestyle='--', color='black')
    plt.axvline(x=3780, linewidth=1, linestyle='--', color='black')

    # plt.legend(loc='upper left')
    plt.xlabel("Time (Seconds)")
    plt.ylabel("Running Point Difference (Home - Away)")
    plt.title('Point Difference Prediction for ' + str(keyId))
    plt.savefig('Analysis/' + str(keyId) + '_' + 'PointDiffPrediction.png')
    plt.clf()
    plt.close()

    return fullSeries


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    # seasonList = [2015, 2016, 2017, 2018]
    seasonList = [2018]

    timeGran = 60  # Buckets (seconds) in which points are recorded

    regSeasonHomePointsDF = pd.DataFrame()
    regSeasonAwayPointsDF = pd.DataFrame()

    playoffHomePointsDF = pd.DataFrame()
    playoffAwayPointsDF = pd.DataFrame()

    completeDataDict = {'game.id': [],
                        'regPredPointDiff': [], 'regActPointDiff': [],
                        'ot1PredPointDiff': [], 'ot1ActPointDiff': [],
                        'ot2PredPointDiff': [], 'ot2ActPointDiff': [],
                        'ot3PredPointDiff': [], 'ot3ActPointDiff': []}

    trainingColumns = ['home', 'away',
                       'game.type',
                       'team.id',
                       'final.period',
                       'running.points']

    for season in seasonList:
        try:
            historicalGameData = readHistoricalGameData(season)
            historicalGameData = historicalGameData[trainingColumns]

            # This is dangerous, but I control what is written and am lazy so who cares
            historicalGameData['running.points'] = [ast.literal_eval(pointsTuple) for pointsTuple in historicalGameData['running.points']]

            for gameIndex in range(0, len(historicalGameData), 2):
                gameDF = pd.DataFrame()

                for side in [0, 1]:
                    tempDF = pd.DataFrame(historicalGameData['running.points'].iloc[gameIndex + side], columns=['Time', 'RunningPoints' + str(side)])
                    tempDF['Time'] = [arbRoundDown(int(gtime), timeGran) for gtime in tempDF['Time']]
                    tempDF = tempDF.loc[~tempDF['Time'].duplicated(keep='last')]

                    tempDF = tempDF.set_index('Time')
                    tempDF = tempDF.reindex(range(0, ((4 * 12) + (3 * 5)) * 60 + timeGran, timeGran), fill_value=np.NaN)  # Assumes no basketball game goes beyond triple overtime
                    tempDF = tempDF.fillna(method='ffill')  # Potentially problematic: if 2nd/3rd/etc quarter missing from API, code will not notice

                    gameDF['RunningPoints' + str(side)] = tempDF['RunningPoints' + str(side)]

                # Ignore games (including game 0021800018) which are missing 1st quarter data
                if gameDF.isnull().values.any():
                    print(str(datetime.datetime.now()) + ': Skipping game ' + historicalGameData.index.get_level_values(0)[gameIndex] + ' as it is missing the 1st quarter')
                    continue

                if historicalGameData['game.type'].iloc[gameIndex] == 'R':
                    regSeasonHomePointsDF[historicalGameData.index.get_level_values(0)[gameIndex]] = gameDF['RunningPoints0']
                    regSeasonAwayPointsDF[historicalGameData.index.get_level_values(0)[gameIndex]] = gameDF['RunningPoints1']
                else:
                    playoffHomePointsDF[historicalGameData.index.get_level_values(0)[gameIndex]] = gameDF['RunningPoints0']
                    playoffAwayPointsDF[historicalGameData.index.get_level_values(0)[gameIndex]] = gameDF['RunningPoints1']

            for playoffGame in playoffHomePointsDF.columns:
                trainingHomePointsDF = copy.deepcopy(regSeasonHomePointsDF)
                trainingHomePointsDF[playoffGame] = playoffHomePointsDF[playoffGame]

                trainingAwayPointsDF = copy.deepcopy(regSeasonAwayPointsDF)
                trainingAwayPointsDF[playoffGame] = playoffAwayPointsDF[playoffGame]

                # checkMatrixRank(playoffGame, trainingHomePointsDF, 'HomePoints')
                # checkMatrixRank(playoffGame, trainingAwayPointsDF, 'AwayPoints')
                sVals = 4  # Based on the above checkMatrixRank

                # Synthetic Control comprised of all regular season games, not just team of interest, due to Stein's Paradox
                predDiffTemp = predictPointDiff(playoffGame, trainingHomePointsDF, trainingAwayPointsDF, timeGran, sVals)

                completeDataDict['game.id'] += [playoffGame]
                completeDataDict['regPredPointDiff'] += [predDiffTemp[int(2880 / timeGran)]]
                completeDataDict['ot1PredPointDiff'] += [predDiffTemp[int(3180 / timeGran)]]
                completeDataDict['ot2PredPointDiff'] += [predDiffTemp[int(3480 / timeGran)]]
                completeDataDict['ot3PredPointDiff'] += [predDiffTemp[int(3780 / timeGran)]]

                completeDataDict['regActPointDiff'] += [trainingHomePointsDF[playoffGame].loc[2880] - trainingAwayPointsDF[playoffGame].loc[2880]]
                completeDataDict['ot1ActPointDiff'] += [trainingHomePointsDF[playoffGame].loc[3180] - trainingAwayPointsDF[playoffGame].loc[3180]]
                completeDataDict['ot2ActPointDiff'] += [trainingHomePointsDF[playoffGame].loc[3480] - trainingAwayPointsDF[playoffGame].loc[3480]]
                completeDataDict['ot3ActPointDiff'] += [trainingHomePointsDF[playoffGame].loc[3780] - trainingAwayPointsDF[playoffGame].loc[3780]]

        except FileNotFoundError:
            print(str(datetime.datetime.now()) + ': Error reading one or more files from season ' + str(season))

    completeData = pd.DataFrame(completeDataDict)

    # Print results
    with open('Analysis/HistoricalPerformanceRaw.csv', mode='w+') as dataFile:
        completeData.to_csv(dataFile, encoding='utf-8', index=True)

    print(str(datetime.datetime.now()) + ': Finished')
