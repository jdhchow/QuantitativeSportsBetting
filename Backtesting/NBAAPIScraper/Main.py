from Backtesting.NBAAPIScraper.APIScraper import *


'''
Author: Jonathan Chow
Date Modified: 2020-01-11
Python Version: 3.7

Code to extract features from data.nba.net. A simple guide can be found at
https://github.com/kashav/nba.js/blob/master/docs/api/DATA.md.
'''


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    # seasonList = [2015, 2016, 2017, 2018]
    seasonList = [2017, 2016, 2015]

    for season in seasonList:
        gameList = getGameIdDicts(season)
        gameData = pd.DataFrame()

        for gameIdDict in gameList:
            gameData = pd.concat([gameData, getBaseGameInformation(gameIdDict)], sort=True, ignore_index=False)

        with open('HistoricalGameData_WithOT/Season' + str(season) + '.csv', mode='w+') as dataFile:
            gameData.to_csv(dataFile, encoding='utf-8', index=True)

        print(str(datetime.datetime.now()) + ': Finished ' + str(season))

    print(str(datetime.datetime.now()) + ': Finished')
