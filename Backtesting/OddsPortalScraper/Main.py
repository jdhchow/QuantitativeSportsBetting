from Backtesting.OddsPortalScraper.NHLScraper import NHLScraper
import datetime


'''
Author: Jonathan Chow & Alex Foley
Date Modified: 2019-08-14
Python Version: 3.7
'''


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    seasonList = [2002, 2003, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]

    n = NHLScraper(seasonsToScrape=seasonList,
                   outputLoc='HistoricalOdds/')
    n.scrape()

    print(str(datetime.datetime.now()) + ': Finished')
