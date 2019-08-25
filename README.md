AlpacaSPDipBot
This is the first algotrading bot written using the Alpaca Trading API.
Program is intended to explore functionality only, and not intended to be reflective of actual trading strategies
The algorithm is based on the assumption of mean-reversion, wherein a stock's price will gradually revert to the average price overtime.
This algorithm ranks stocks based on how big the spread is from the EMA(Exponential Moving Average), and current price.
When the price is below the EMA, the algorithm will buy. 
The alogorithm will constantly be ranking the stocks, and will only keep the most oversold stocks.
