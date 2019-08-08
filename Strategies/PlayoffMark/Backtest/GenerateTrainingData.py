from Jonathan.NHL.Strategies.Markov.GenerateFeatures import *


'''
Author: Jonathan Chow
Date Modified: 2018-04-09
Python Version: 3.7

Produces training data
'''


########################################################################################################################
if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    # No games in 2004, shorter season in 2013
    seasonList = [2002, 2003, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]

    for seasonIndex in range(0, len(seasonList)):
        gameList = getGameIds(seasonList[seasonIndex], False)
        trainingData = pd.DataFrame()

        for gameId in gameList:
            trainingData = pd.concat([trainingData, getBaseGameInformation(gameId, False)], sort=True, ignore_index=False)

        trainingData = mergeOdds(trainingData, getOdds())

        writeDataFrame(trainingData, 'Strategies/Markov/Records/TrainingData/TrainingData' + str(seasonList[seasonIndex]))

        print(str(datetime.datetime.now()) + ': Finished ' + str(seasonList[seasonIndex]))

    print(str(datetime.datetime.now()) + ': Finished')
