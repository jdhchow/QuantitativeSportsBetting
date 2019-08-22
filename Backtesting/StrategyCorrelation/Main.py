import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt


'''
Author: Jonathan Chow
Date Modified: 2019-08-11
Python Version: 3.7

This program calculates the correlation between strategies
'''


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

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

    # Generate correlation matrix
    corr = stratFrame.corr()

    print(corr)

    fig = plt.figure()

    ax = fig.add_subplot(1, 1, 1)
    cax = ax.matshow(corr, cmap='coolwarm', vmin=-1, vmax=1)
    fig.colorbar(cax)

    ticks = np.arange(0, len(stratFrame.columns), 1)
    ax.set_xticks(ticks)
    plt.xticks(rotation=90)
    ax.set_yticks(ticks)
    ax.set_xticklabels(stratFrame.columns)
    ax.set_yticklabels(stratFrame.columns)
    plt.tight_layout()

    plt.savefig('StrategyCorrelation.png', dpi=500)

    print(str(datetime.datetime.now()) + ': Finished')
