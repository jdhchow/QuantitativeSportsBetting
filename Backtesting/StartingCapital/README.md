# Starting Capital (Portfolio Management)

## Purpose
This program determines an upper bound for the probability of ruin over a finite
time period given some starting capital.

## Method
It takes a list of wagers in HistoricalWagers.csv as input and proceeds as
follows:
 1. Iterate though the wagers generating non-overlapping subsequences which
    1. Begin with a loss
    2. Have positive sum
 2. Take the cumulative sum of each subsequence
 3. Calculate the minimum of these cumulative sums
 The end result of this process is a list of maximum losses incurred before
 returning to a break even state (MLBBE). These events are independent and
 identically distributed over the backtest.

We then produce a histogram of these MLBBEs. We fit an exponential distribution
on the histogram.

Let our backtest last y years and say that we observe m MLBBEs. If we choose to
begin with $N,

P(ruin over the next y years) < 1 - P(MLBBE < N)^s

We heuristically select a starting capital such that this value is low.

## Results/Status
Initial version complete. Project likely needs refinement. See below for more
information.

## Potential Issues
 1. There are a very low number (10s) of MLBBEs generated. A sample is likely
 to under-represent large losses. It might be possible to adjust the
 distribution to account for this.
 2. The calculation provides an upper bound but not an exact probability. If the
 expected return is positive, we would expect to be able to lose more without
 ruin as time goes on. This is not considered and may be impactful in the
 analysis.
 3. For the starting capital required to run multiple strategies on the same
 game, the .csv file will simply contain the result of both strategies run
 concurrently. It implicitly considers the correlation between strategies, but
 it is possible that the loss profiles differ. There might be a better way to
 combine them.
 4. For strategies run on different leagues, we simply sum the starting capital
 for each to get fund level starting capital. There may be better ways to do
 this.
