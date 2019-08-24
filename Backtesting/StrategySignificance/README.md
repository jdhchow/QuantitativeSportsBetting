# Strategy Significance (Portfolio Management)

## About
This program determines whether a strategy or strategies are statistically
significant. We want to be certain that a strategy is legitimate and not
a pattern specific to the backtest data.

We proceed by taking the games that the strategy wagers on and randomly
predicting the winner. We then place a wager with the same method as the
strategy and record the final profit. Repeating this process repeatedly,
we can create a distribution of possible returns and ensure that the returns
generated by the strategy are statistically significant.

Ideally, we would the set of all possible returns; however, if a strategy
wagers on 1000 games over 10 years, each of which can end in a win, loss, or
tie, there are 3^1000 possible combinations which cannot be computed. Hence,
we sample randomly from this set.

## Potential Issues
 1. This checks that a given strategy produces statistically significant returns
 but we would expect to eventually find a pattern in the data that does not
 exist beyond the backtest. This check does not account for this.
 2. We generate a random sample to test significance, improvements in sampling
 size or method are likely possible.
 3. Ultimately, we do not care if the prediction more accurate than random, only
 if the strategy is more profitable than randomly betting. However, it might
 be worthwhile to write a test that the prediction does contain information.
 4. We place our sample bets with the same method as the strategy and only
 predict randomly. Is this the best method? Should the wagers be randomized
 within some range as well?