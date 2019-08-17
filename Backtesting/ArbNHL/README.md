# ArbNHL (Strategy)

## About
Calculates arbitrage potential among NHL game odds. Returns per wager are
less than 1% and there is insufficient volume to take advantage of the risk free
return. Annualized returns are below 1% as well.

Let the home, tie, and away team odds be O_h, O_t, O_a respectively. We must
decide how much to wager on each outcome (W_h, W_t, W_a) given a certain
starting capital to maximize our payout regardless of the outcome. We solve the
solving linear program:

```
Max: x

Subject to:
      W_h + W_t + W_a <= Starting Capital
      (O_h * W_h) - W_t - W_a = x
      - W_h + (O_t * W_t) - W_a = x
      - W_h - W_t + (O_a * W_a) = x
      W_h, W_t, W_a, x >= 0
```
