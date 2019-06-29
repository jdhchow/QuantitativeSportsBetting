# Scraping from OddsPortal

## Overview

Odds portal made it annoying to scrape data because they send all of their data over websocket, so I've had to create a selenium script to grab it from them. There's a comment at the top of Scraper.py that outlines the interface and what you need to implement in order to make your own.

## Getting started

First of all, you'll need to install the Python libraries. Luckily the list is pretty short and I took the 30 seconds to make a requirements file so just kinda run:

`pip install -r requirements.txt`

from the root directory.

You'll need Firefox (because I like firefox and have declared we will use firefox), so go ahead and install that.

Finally, you need to install geckodriver from Mozilla and add it to your PATH. Download the latest version for your system [here](https://github.com/mozilla/geckodriver/releases). Extract it, then add the folder that contains the executable to your PATH.

Now you're all ready to go!
