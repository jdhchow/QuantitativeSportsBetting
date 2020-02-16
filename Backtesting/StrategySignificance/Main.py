import numpy as np
import random
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.stats import ttest_1samp


'''
Author: Jonathan Chow
Date Modified: 2019-08-22
Python Version: 3.7

This program attempts to determine whether a strategy is statistically significant
'''


def calculateReturns(prediction, winner, currOdds, oppOdds, wager):
    applicableOdds = currOdds if prediction == 1 else oppOdds

    if prediction == winner:
        return (applicableOdds - 1) * wager
    else:
        return -wager


def testTeamSelection(backtest, samples=100, reps=1000):
    results = []

    for rep in range(0, reps):
        sampleResults = []

        for sample in range(0, samples):
            returns = []

            for gameId in backtest.index:
                randomPrediction = random.choice([-1, 1])
                wagerAmount = 100 * backtest['currTeam.odds'].loc[gameId] if randomPrediction == 1 else 100 * backtest['oppTeam.odds'].loc[gameId]

                returns.append(calculateReturns(randomPrediction,
                                                backtest['game.winner'].loc[gameId],
                                                backtest['currTeam.odds'].loc[gameId],
                                                backtest['oppTeam.odds'].loc[gameId],
                                                wagerAmount))

            sampleResults.append(np.mean(returns))

        results.append(max(sampleResults))

    return results


def testBetSizing(backtest, samples=100, reps=1000):
    results = []

    # This generates wagers uniformly between the min and max. It might be better to pull them from the same
    # distribution as they appear in the file?
    minWager = min(backtest['Wager'])
    maxWager = max(backtest['Wager'])
    genWager = lambda x: minWager + x * (maxWager - minWager)

    for rep in range(0, reps):
        sampleResults = []

        for sample in range(0, samples):
            returns = []

            for gameId in backtest.index:
                randomWager = genWager(random.uniform(0, 1))
                returns.append(calculateReturns(backtest['predictions'].loc[gameId],
                                                backtest['game.winner'].loc[gameId],
                                                backtest['currTeam.odds'].loc[gameId],
                                                backtest['oppTeam.odds'].loc[gameId],
                                                randomWager))

            sampleResults.append(np.mean(returns))

        results.append(max(sampleResults))

    return results


def graphHistogram(results, strategyReturn, attr):
    # Fit normal distribution to the returns
    P = norm.fit(results)

    # Test for strategy significance
    ttset, pval = ttest_1samp(results, strategyReturn)

    print(attr)
    print('Mean: ' + str(norm.mean(*P)))
    print('Standard Deviation: ' + str(norm.std(*P)))
    print('Strategy Return: ' + str(strategyReturn))
    print('P-Value: ' + str(pval))
    print('T Statistic: ' + str(ttset))

    # Plot histogram of returns
    plt.figure(figsize=(10, 5))
    plt.hist(results, bins=50, edgecolor='black', density=True)

    plt.plot([strategyReturn, strategyReturn], plt.ylim(), 'k-', color='red', lw=2)

    xmin, xmax = plt.xlim()
    rX = np.linspace(xmin, xmax, 100)
    rP = norm.pdf(rX, *P)
    plt.plot(rX, rP, color='black')

    plt.xlabel('Sample Expected Return per Wager (CAD $)')
    plt.ylabel('Probability (%)')
    plt.title('Histogram of Sample Expected Return Attributable to ' + attr + ' per Wager (' + strategy + ')\nMean = {:.3}, Std = {:.3}'.format(norm.mean(*P), norm.std(*P)))

    plt.savefig(attr + 'Significance.png', dpi=500)


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    strategy = 'PlayoffMarkEx'

    try:
        with open('Strategies/' + strategy + '.csv', mode='r') as dataFile:
            backtest = pd.read_csv(dataFile, encoding='utf-8', index_col=0)
            backtest.index = backtest.index.astype(str)
    except FileNotFoundError:
        print(str(datetime.datetime.now()) + ': Error reading ' + strategy + ' file')
        exit()

    sampleTeamSelection = testTeamSelection(backtest)
    sampleBetSizing = testBetSizing(backtest)

    graphHistogram(sampleTeamSelection, backtest['WagerReturns'].mean(), 'TeamSelection')
    graphHistogram(sampleBetSizing, backtest['WagerReturns'].mean(), 'BetSizing')

    print(str(datetime.datetime.now()) + ': Finished')
