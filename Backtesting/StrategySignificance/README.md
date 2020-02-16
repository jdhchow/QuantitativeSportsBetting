# Strategy Significance (Portfolio Management)

## Purpose
This program attempts to determine whether a strategy is statistically
significant. We want to be certain that a strategy is legitimate and not
exploiting a pattern specific to the backtest data.

We test the following two hypotheses:
 1. The returns attributable to the strategy's team selection in a given
 game is 0.
 2. The returns attributed to the strategy's bet sizing is 0.

## Method
To test 1, we take the games that the strategy wagers on and randomly
predict the winner. We then simulate placing a wager using the strategy's
bet sizing method and record the profit. We repeat this process 100
times, giving 100 "strategies", and record the maximum profit. Plotting
a histogram of these maximums gives us a distribution of returns against
which we can compare the strategy. We select the maximum of a sample of
random strategies to simulate the actual strategy selection process where
we only choose the best candidate.

To test hypothesis 2, we apply a similar procedure. We bet a random size
(between the minimum and maximum used by the strategy) on the team the
strategy has selected.

Ideally, we would simulate all possible combinations; however, if a strategy
wagers on 1000 games over 10 years, each of which can end in a win, loss, or
tie, there are 3^1000 possible combinations. Hence, we sample randomly from
this set.

## Results/Status
The only real way to know if a strategy is significant is by splitting the data
into a training and testing set. This evaluation is pretty useless.

## Potential Issues
I am not confident this method is optimal. Further investigation is required.
 1. We randomly select win/loss/tie from the games the strategy wagers on.
 Should we instead randomly pick win/loss/tie/no-bet from all games?
 2. We generate a random sample to test significance, improvements in
 sampling size or method are likely possible.
