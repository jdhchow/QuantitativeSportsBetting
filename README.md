# Attridge
Goal: To develop sports betting algorithms\
Stretch Goal: To setup a fund for the beginning of the 2019/2020 season

## 2019/2020 Season Schedules
| League         | Category       | Start Date | End Date   |
| -------------- | ---------------| ---------- | ---------- |
| Premier League | Regular Season | 2019-08-10 | 2020-05-17 |
| La Liga        | Regular Season | 2019-08-16 | 2020-05-24 |
| Bundesliga     | Regular Season | 2019-08-16 | 2020-05-16 |
| NFL            | Regular Season | 2019-09-05 | 2019-12-29 |
| NHL            | Regular Season | 2019-10-04 | 2020-04-11 |
| NBA            | Regular Season | 2019-10-XX | 2020-04-XX |
| ATP Tour       | Regular Season | 2020-01-03 | 2020-11-29 |
| NFL            | Playoffs       | 2020-01-04 | 2020-02-02 |
| NHL            | Playoffs       | 2020-04-XX | 2020-06-XX |
| NBA            | Playoffs       | 2020-04-XX | 2020-06-XX |

## Backtesting
The backtesting folder is further divided into sub-folders of type strategy,
data exploration, or portfolio management. Each should be self-contained and
used only for testing ideas, not to be relied on for the actual placing of
wagers.

We obey the following stylistic rules in case this repository is ever developed
by multiple people:
 1. All strategy backtests should contain an "Analysis" folder detailing all
 and only relevant information regarding the strategy performance.
 2. There should exist some explanation of each backtest in words to prevent
 people from having to dig through code to get a high-level understanding
 of how the strategy/data-gathering/etc works.

## Wager
The wager folder contains all production code to be run when actually placing
a wager. It is divided up by league and, for a given game, should output at
minimum: the amount(s) to wager, the teams to wager on, and the type of wager
to place.
