from Strategies.PlayoffMark.Backtest.OddsPortalScraper.NHLScraper import NHLScraper
import datetime


if __name__ == '__main__':
    print(str(datetime.datetime.now()) + ': Started')

    n = NHLScraper(seasonsToScrape=list(range(2002, 2012)),
                   outputLoc='HistoricalOdds/')
    n.scrape()

    print(str(datetime.datetime.now()) + ': Finished')
