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


def predictPointDiff(keyId, homePoints, pointDiff, timeBuckets, singularVals):
    trainQtr = 1
    metrics = 2
    weights = [0.25, 0.75]

    trainSeconds = trainQtr * 12 * 60  # Will break if training includes overtime

    otherKeys = list(homePoints.columns)
    otherKeys.remove(keyId)

    trainArray = [homePoints.loc[:trainSeconds],
                  pointDiff.loc[:trainSeconds]]

    testArray = [homePoints.loc[trainSeconds + timeBuckets:],
                 pointDiff.loc[trainSeconds + timeBuckets:]]

    plt.figure(figsize=(8, 6), dpi=100)

    ########### Multi-dimensional robust synthetic control ##########
    mrscModel = MultiRobustSyntheticControl(metrics, weights, keyId, singularVals, len(trainArray[0]),
                                            probObservation=1.0, modelType='svd', svdMethod='numpy',
                                            otherSeriesKeysArray=otherKeys)

    mrscModel.fit(trainArray)
    denoisedDF = mrscModel.model.denoisedDF()
    predictions = mrscModel.predict(testArray)

    plt.plot(list(pointDiff.index), pointDiff[keyId], color='tomato', label='Observations')
    plt.plot(list(pointDiff.index), np.append(denoisedDF[keyId][int(len(denoisedDF)/2):], predictions[1], axis=0), color='darkblue', label='Predictions')
    #################################################################

    ############### Singular robust synthetic control ###############
    # rscModel = RobustSyntheticControl(keyId, singularVals, len(pointDiff.loc[:trainSeconds]),
    #                                   probObservation=1.0, modelType='svd', svdMethod='numpy',
    #                                   otherSeriesKeysArray=otherKeys)
    #
    # rscModel.fit(pointDiff.loc[:trainSeconds])
    # denoisedDF = rscModel.model.denoisedDF()
    # predictions = rscModel.predict(pointDiff.loc[trainSeconds + timeBuckets:])
    #
    # plt.plot(list(pointDiff.index), pointDiff[keyId], color='tomato', label='Observations')
    # plt.plot(list(pointDiff.index), np.append(denoisedDF[keyId], predictions, axis=0), color='darkblue', label='Predictions')
    #################################################################

    plt.axvline(x=trainSeconds - 1, linewidth=1, color='black', label='Intervention')

    # Lines to mark end of regular time and overtime
    plt.axvline(x=2880, linewidth=1, linestyle='--', color='black', label='Potential End of Game')
    plt.axvline(x=3180, linewidth=1, linestyle='--', color='black')
    plt.axvline(x=3480, linewidth=1, linestyle='--', color='black')
    plt.axvline(x=3780, linewidth=1, linestyle='--', color='black')

    plt.legend(loc='upper left')
    plt.title('Goal Difference (Home - Away) Prediction for ' + str(keyId))
    plt.savefig('Analysis/' + str(keyId) + '_' + 'PointDiffPrediction.png')
    plt.clf()
    plt.close()


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    # seasonList = [2015, 2016, 2017, 2018]
    seasonList = [2018]

    timeGran = 15  # Buckets (seconds) in which points are recorded

    regSeasonHomePointsDF = pd.DataFrame()
    regSeasonPointDiffDF = pd.DataFrame()

    playoffHomePointsDF = pd.DataFrame()
    playoffPointDiffDF = pd.DataFrame()

    trainingColumns = ['home', 'away',
                       'game.type',
                       'team.id',
                       'final.period',
                       'running.points']

    outputColumns = ['game.winner', 'point.difference',
                     'prediction.game.winner', 'prediction.point.difference']

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
                    regSeasonPointDiffDF[historicalGameData.index.get_level_values(0)[gameIndex]] = gameDF['RunningPoints0'] - gameDF['RunningPoints1']
                else:
                    playoffHomePointsDF[historicalGameData.index.get_level_values(0)[gameIndex]] = gameDF['RunningPoints0']
                    playoffPointDiffDF[historicalGameData.index.get_level_values(0)[gameIndex]] = gameDF['RunningPoints0'] - gameDF['RunningPoints1']

            for playoffGame in playoffHomePointsDF.columns:
                trainingHomePointsDF = copy.deepcopy(regSeasonHomePointsDF)
                trainingHomePointsDF[playoffGame] = playoffHomePointsDF[playoffGame]

                trainingPointDiffDF = copy.deepcopy(regSeasonPointDiffDF)
                trainingPointDiffDF[playoffGame] = playoffPointDiffDF[playoffGame]

                # checkMatrixRank(playoffGame, trainingHomePointsDF, 'HomePoints')
                # checkMatrixRank(playoffGame, trainingPointDiffDF, 'PointDiff')
                sVals = 50  # Based on the above checkMatrixRank

                # Synthetic Control comprised of all regular season games, not just team of interest, due to Stein's Paradox
                predictPointDiff(playoffGame, trainingHomePointsDF, trainingPointDiffDF, timeGran, sVals)

        except FileNotFoundError:
            print(str(datetime.datetime.now()) + ': Error reading one or more files from season ' + str(season))

    # # Print results
    # with open('Analysis/HistoricalPerformanceRaw.csv', mode='w+') as dataFile:
    #     completeData.to_csv(dataFile, encoding='utf-8', index=True)

    print(str(datetime.datetime.now()) + ': Finished')
