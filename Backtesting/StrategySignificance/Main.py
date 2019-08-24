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

This program determines whether a strategy is statistically significant
'''


# This must be changed depending on the betting method employed by each strategy
def calculateReturns(prediction, winner, currOdds, oppOdds, wager):
    applicableOdds = currOdds if prediction == 1 else oppOdds

    if prediction == winner:
        return (applicableOdds - 1) * applicableOdds * wager
    else:
        return -applicableOdds * wager


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    strategy = 'PlayoffMarkEx'

    samples = 5000
    wagerAmount = 100

    try:
        with open('Strategies/' + strategy + '.csv', mode='r') as dataFile:
            backtest = pd.read_csv(dataFile, encoding='utf-8', index_col=0)
            backtest.index = backtest.index.astype(str)
    except FileNotFoundError:
        print(str(datetime.datetime.now()) + ': Error reading ' + strategy + ' file')
        exit()

    sampleResults = []

    for trial in range(0, samples):
        trialResults = []

        for gameId in backtest.index:
            samplePrediction = random.randint(-1, 1)
            sampleReturn = calculateReturns(samplePrediction, backtest['game.winner'].loc[gameId],
                                            backtest['currTeam.odds'].loc[gameId], backtest['oppTeam.odds'].loc[gameId],
                                            wagerAmount)
            trialResults.append(sampleReturn)

        sampleResults.append(np.mean(trialResults))

    # Fit normal distribution to the returns
    P = norm.fit(sampleResults)

    # Test for strategy significance
    strategyReturn = backtest['WagerReturns'].mean()
    ttset, pval = ttest_1samp(sampleResults, strategyReturn)

    print('Mean: ' + str(norm.mean(*P)))
    print('Standard Deviation: ' + str(norm.std(*P)))
    print('Strategy Return: ' + str(strategyReturn))
    print('P-Value: ' + str(pval))
    print('T Statistic: ' + str(ttset))

    # Plot histogram of returns
    plt.figure(figsize=(10, 5))
    plt.hist(sampleResults, bins=50, edgecolor='black', density=True)

    plt.plot([strategyReturn, strategyReturn], plt.ylim(), 'k-', color='red', lw=2)

    xmin, xmax = plt.xlim()
    rX = np.linspace(xmin, xmax, 100)
    rP = norm.pdf(rX, *P)
    plt.plot(rX, rP, color='black')

    plt.xlabel('Sample Expected Return per Wager (CAD $)')
    plt.ylabel('Probability (%)')
    plt.title('Histogram of Sample Expected Return per Wager (' + strategy + ')\nMean = {:.3}, Std = {:.3}'.format(norm.mean(*P), norm.std(*P)))

    plt.savefig('StrategySignificance.png', dpi=500)

    print(str(datetime.datetime.now()) + ': Finished')
