from Strategies.PlayoffMark.Backtest.OddsPortalScraper.NHLScraper import NHLScraper

n = NHLScraper(seasonsToScrape=list(range(2002, 2020)),
               outputLoc='HistoricalOdds/')
n.scrape()
