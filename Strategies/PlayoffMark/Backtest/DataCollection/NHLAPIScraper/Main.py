from Strategies.PlayoffMark.Backtest.DataCollection.NHLAPIScraper.APIScraper import *


'''
Author: Jonathan Chow
Date Modified: 2018-04-09
Python Version: 3.7

Scrapes NHL API for the required data for the model
'''


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    # No games in 2004, shorter season in 2013
    seasonList = [2002, 2003, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]

    for season in seasonList:
        gameList = getGameIds(season)
        gameData = pd.DataFrame()

        for gameId in gameList:
            gameData = pd.concat([gameData, getBaseGameInformation(gameId)], sort=True, ignore_index=False)

        with open('HistoricalGameData/Season' + str(season) + '.csv', mode='w+') as dataFile:
            gameData.to_csv(dataFile, encoding='utf-8', index=True)

        print(str(datetime.datetime.now()) + ': Finished ' + str(season))

    print(str(datetime.datetime.now()) + ': Finished')
