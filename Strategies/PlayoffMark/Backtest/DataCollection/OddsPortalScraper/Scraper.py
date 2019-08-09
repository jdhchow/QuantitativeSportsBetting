from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


'''
Scraper interface for pulling from OddsPortal

Scraper functions as follows:
 - webpage at entry_url will be opened
 - scraper.setup will be called
 - scraper.get_url_list will be called
 - scraper.extract_from_urls will be called (on the resulting list)
'''


class Scraper(object):
    def __init__(self, entry_url, root_url, store=[]):
        self.entry_url = entry_url
        self.root_url = root_url
        self.store = store
        self._browser = None

    @property
    def browser(self):
        if self._browser is None:
            self._browser = webdriver.Firefox()
        return self._browser

    def get_url_list(self):
        raise NotImplementedError("get_url_list is required on type Scraper")

    def extract_from_urls(self, urls_to_scrape):
        raise NotImplementedError("extract_from_urls is required on type Scraper")

    def setup(self):
        raise NotImplementedError("setup is required on type Scraper")

    def relative_path(self, path, root=None):
        if root is None:
            root = self.root_url
        return root + path

    def get_lazy_element_by_id(self, _id, timeout=15):
        return WebDriverWait(self.browser, timeout).until(
            EC.presence_of_element_located((By.ID, _id))
        )

    def scrape(self):
        try:
            self.browser.get(self.entry_url)
            self.setup()
            urls_to_scrape = self.get_url_list()
            self.extract_from_urls(urls_to_scrape)
        finally:
            self.browser.close()
