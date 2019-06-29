from Strategies.PlayoffMark.Development.OddsPortalScraper.scraper import Scraper
from bs4 import BeautifulSoup
import json
import re
import time

def format_page_string(page_num):
    return "#/" if page_num == 1 else "#/page/{0}/".format(page_num)

def extract_page_num(string):
    search = re.search('#/page/([^/]*)/?', string)
    return int(search.group(1)) if search else 1

class NHLScraper(Scraper):
    def __init__(self, dump_file):
        self.partial_store = {}
        self.reset_state()
        self.dump_file = dump_file
        super().__init__("https://www.oddsportal.com/hockey/usa/nhl/results/", "https://www.oddsportal.com")

    def reset_state(self):
        self.state = {
            "pre-season": False,
            "regular-season": True,
            "playoffs": False,
            "day": None,
        }
    
    def setup(self):
        print("Setting up NHL scraper -- changing odds format")
        self.browser.execute_script("changeOddsFormat(1)")
        time.sleep(10)

    # String is in the format date (- (pre-season|playoffs))?
    def update_state_from_string(self, string):
        if "-" in string:
            self.state['day'] = string[:string.find("-")].strip()
            if "season" in string:
                self.state['pre-season'] = True
                self.state['regular-season'] = False
                self.state['playoffs'] = False
            else:
                self.state['pre-season'] = False
                self.state['regular-season'] = False
                self.state['playoffs'] = True

        else:
            self.state['day'] = string
            self.state['pre-season'] = False
            self.state['regular-season'] = True
            self.state['playoffs'] = False


    def get_url_list(self):
        html = self.browser.find_elements_by_class_name('main-filter')[1].get_attribute('innerHTML')
        soup = BeautifulSoup(html, "html.parser")
        urls = [self.relative_path(a['href']) for a in soup.find_all("a", href=True) if a['href'] != "/hockey/usa/nhl/results/"]
        return urls

    def extract_from_urls(self, urls):
        for url in urls:
            print("Starting extraction for: {0}".format(url))
            self.reset_state()
            self.extract_from_url(url)
            print("Finished extraction for: {0}".format(url))
            print("Writing results to store...")
            self.dump_to_store()
            print("Writing complete")


    def extract_from_url(self, url):
        individual_urls = []
        self.browser.get(url)
        try:
            soup = BeautifulSoup(self.get_lazy_element_by_id("pagination").get_attribute('innerHTML'), "html.parser")
            max_page = extract_page_num(soup.find_all("a")[-1]['href'])
        except:
            # what can you do ¯\_(ツ)_/¯
            return 

        for i in range(1, max_page + 1):
            path = self.relative_path(format_page_string(i), url)
            self.browser.get(path)
            self.extract_from_page()

    def extract_from_page(self):
        html = self.get_lazy_element_by_id("tournamentTable").get_attribute('innerHTML')
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")[1:]
        links_to_follow = []
        for row in rows:
            if 'table-dummyrow' in row['class']:
                continue
            if len(row.contents) == 5:
                # update state
                self.update_state_from_string(row.find('th').get_text())
            else:
                # found game
                time, teams = [t for t in row.find_all("td")[:2]]
                time = time.get_text()
                link = self.relative_path(teams.find("a")['href'])
                teams = teams.get_text()
                home, away = [s.strip() for s in teams.split(" - ")]

                self.partial_store[link] = {}
                for key in self.state:
                    self.partial_store[link][key] = self.state[key]
                self.partial_store[link]['home'] = home
                self.partial_store[link]['away'] = away

                links_to_follow.append(link)

        for link in links_to_follow:
            self.complete_link(link)

    def complete_link(self, link):
        try:
            self.browser.get(link)
            partial = self.partial_store.pop(link)
            html = self.get_lazy_element_by_id('odds-data-table').get_attribute("innerHTML")
            soup = BeautifulSoup(html, "html.parser")
            highest = soup.find("tr", {"class": "highest"})
            average = soup.find("tr", {"class": "aver"})
            _, day, time = [s.strip() for s in self.browser.find_element_by_class_name("date").get_attribute("innerHTML").split(",")]

            homeMax, tieMax, awayMax = [float(t.get_text()) for t in highest.find_all("td")[1:4]]
            home, tie, away = [float(t.get_text()) for t in average.find_all("td")[1:4]]

            partial['home.oddsMax'] = homeMax
            partial['tie.oddsMax'] = tieMax
            partial['away.oddsMax'] = awayMax

            partial['home.odds'] = home
            partial['tie.odds'] = tie
            partial['away.odds'] = away

            partial['day'] = day
            partial['time'] = time
            print(partial)
            self.store.append(partial)
        except:
            print('Unable to extract odds from: ' + link)

    def dump_to_store(self):
        with open(self.dump_file, 'w') as fp:
            json.dump(self.store, fp)
