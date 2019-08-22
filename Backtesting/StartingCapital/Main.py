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

    startingCapital = 9000

    with open('HistoricalWagers.csv', mode='r') as dataFile:
        backtest = pd.read_csv(dataFile, encoding='utf-8', index_col=0)
        backtest.index = backtest.index.astype(str)

    wagers = backtest['WagerReturns']
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

    print(str(datetime.datetime.now()) + ': Finished')
