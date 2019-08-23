import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import expon
import datetime


'''
Author: Jonathan Chow
Date Modified: 2019-08-11
Python Version: 3.7

This program determines an upper bound for the probability of ruin over a finite time period given some starting
capital.
'''


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    startingCapital = 15000

    strategies = ['PlayoffMarkEx', 'StreakBreaker', 'ArbNHL']

    stratFrame = pd.DataFrame()

    for strategy in strategies:
        try:
            with open('Strategies/' + strategy + '.csv', mode='r') as dataFile:
                backtest = pd.read_csv(dataFile, encoding='utf-8', index_col=0)
                backtest.index = backtest.index.astype(str)
                backtest.columns = [strategy]

                stratFrame = pd.concat([stratFrame, backtest], sort=True, ignore_index=False, axis=1)
        except FileNotFoundError:
            print(str(datetime.datetime.now()) + ': Error reading ' + strategy + ' file')

    stratFrame['WagerReturns'] = stratFrame.sum(axis=1)

    wagers = stratFrame['WagerReturns']
    maxLosses = []
    cumSum = 0
    losses = []

    # Generate list of max losses before break even
    for wagerIndex in range(0, len(wagers)):
        losses += [wagers[wagerIndex]]
        cumSum += wagers[wagerIndex]

        if cumSum >= 0:
            losses = np.cumsum(losses)
            maxLosses += [min(losses)]

            losses = []
            cumSum = 0

    maxLosses = [abs(loss) for loss in maxLosses if loss < 0]

    P = expon.fit(maxLosses)

    pRuin = 1 - np.power(expon.cdf(startingCapital, *P), len(maxLosses))

    print(maxLosses)
    print('Location: ' + str(P[0]))
    print('Scale: ' + str(P[1]))
    print('P(ruin over same period as backtest): ' + str(pRuin))

    # Plot histogram of losses
    plt.figure(figsize=(10, 5))
    plt.hist(maxLosses, bins=30, edgecolor='black', density=True)

    xmin, xmax = plt.xlim()
    rX = np.linspace(xmin, xmax, 100)
    rP = expon.pdf(rX, *P)
    plt.plot(rX, rP, color='black')

    plt.xlabel('Notional Loss Before Break Even (CAD $)')
    plt.ylabel('Probability (%)')
    plt.title('Histogram of Loss Before Break Even\nP(ruin in period) < {:.3} with Starting Notional = {}'.format(pRuin, startingCapital))

    plt.savefig('LossBeforeBreakEven.png', dpi=500)

    # Add initial fund size and split returns by season
    cumulativeWagerReturns = [[startingCapital]]

    # Remove games that are not wagered on
    stratFrame = stratFrame.loc[stratFrame['WagerReturns'] != 0]

    seasonList = list(stratFrame.index.str[:4].astype(int).unique())

    for season in seasonList:
        cumulativeWagerReturns.append(list(stratFrame.loc[stratFrame.index.str[:4].astype(int) == season, 'WagerReturns']))

    # Calculate cumulative returns
    for seasonIter in range(1, len(cumulativeWagerReturns)):
        cumulativeWagerReturns[seasonIter] = np.cumsum(
            [cumulativeWagerReturns[seasonIter - 1][-1]] + cumulativeWagerReturns[seasonIter])

    # Graph returns over time
    plt.figure(figsize=(10, 5))

    xAxisCounter = 0
    colourList = ['#015482', '#95D0FC', '#5E819D'] * int(np.ceil(len(seasonList) / 3))

    for returnIter in range(1, len(cumulativeWagerReturns)):
        plt.plot(list(range(xAxisCounter, xAxisCounter + len(cumulativeWagerReturns[returnIter]))),
                 cumulativeWagerReturns[returnIter], c=colourList[returnIter - 1])

        xAxisCounter += len(cumulativeWagerReturns[returnIter]) - 1

    plt.xlabel('Game Number')
    plt.ylabel('Notional (CAD $)')
    plt.title('NHL Strategies Cumulative Return (2009-2018)')
    plt.savefig('CumulativeReturns.png', dpi=500)

    print(str(datetime.datetime.now()) + ': Finished')
