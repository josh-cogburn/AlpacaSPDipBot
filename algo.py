import alpaca_trade_api as tradeapi
import pandas as pd
import time
import logging

from universe import Universe

api = tradeapi.REST(
    key_id='<REPLACE>',
    secret_key='<REPLACE>',
    base_url='https://paper-api.alpaca.markets')

logger = logging.getLogger(__name__)
logging.basicConfig(level = logging.DEBUG)

NY = 'America/NY'

#Trading Logic
def get_prices(symbols, end_dt, max=5):
    start_dt = end_dt - pd.Timedelta('100 days')
    start = start_dt.strftime('%Y-%-m-%-d')
    end = end_dt.strftime('%Y-%-m-%-d')

    def get_barset(symbols):
        return api.get_barset(symbols, 'day', limit = 50, start = start, end = end)

    barset = None
    idx = 0
    while idx <= len(symbols) - 1:
        if barset is None:
            barset = get_barset(symbols[idx:idx+200])
        else:
            barset.update(get_barset(symbols[idx:idx+200]))
        idx += 200

    return barset.df

def prices(symbols):
    now = pd.Timestamp.now(tz=NY)
    end_dt = now
    if now.time() >= pd.Timestamp('09:30', tz=NY).time():
        end_dt = now - pd.Timedelta(now.strftime('%H:&M:%S')) - pd.Timedelta('1 minute')
    return get_prices(symbols, end_dt)

def scores(price_df, dayindex = -1):
    diffs = {}
    param = 10
    for symbol in price_df.columns.levels[0]:
        df = price_df[symbol]
        if len(df.close.values) <= param:
            continue
        exmavg = df.close.ewm(span = param).mean()[dayindex]
        last = df.close.values[dayindex]
        diff = (last - exmavg) / last
        diffs[symbol] = diff

    return sorted(diffs.items(), key = lambda x: x[1])

def build_orders(api, price_df, position_size = 100, max_pos = 5):
    #Rack and Stack
    ranked = scores(price_df)
    to_buy = set()
    to_sell = set()
    account = api.get_account()

    #Gets top 1/20 rankings, excluding stocks I can't afford

    for symbol, _ in ranked[:len(ranked) // 20]:
        price = float(price_df[symbol].close.values[-1])
        if price > float(account.cash):
            continue
        to_buy.add(symbol)

    positions = api.list_positions()
    logger.info(positions)
    holdings = {p.symbol : p for p in positions}
    holding_symbol = set(holdings.keys())
    to_sell = holding_symbol - to_buy
    to_buy = to_buy - holding_symbol
    orders =[]

    #If there is a stock in our portfolio that is
    #not in our optimal portfolio composition
    #sell that stock
    for symbol in to_sell:
        shares = holdings[symbol].qty
        orders.append({'symbol' : symbol,
                       'qty': shares,
                       'side': 'sell',})
        logger.info(f'order(sell): {symbol} for {shares}')

    #If there is a stock in our desired portfolio
    #that is not in our actual portfolio, buy

    max_buy = max_pos - (len(positions) - len(to_sell))
    for symbol in to_buy:
        if max_buy <= 0:
            break
        shares = position_size // float(price_df[symbol].close.values[-1])
        if shares == 0.0:
            continue
        orders.append({
            'symbol': symbol,
            'qty': shares,
            'side': 'buy',
        })
        logger.info(f'order(buy): {symbol} for {shares}')
        max_buy = -1
    return orders

#Placing Orders
def trade(orders, wait = 30):
    #Sell order First
    sells = [o for o in orders if o['side'] == 'sell']
    for order in sells:
        try:
            logger.info(f'submit(sell): {order}')
            api.submit_order(
                symbol = order['symbol'],
                qty = order['qty'],
                side = 'sell',
                type = 'market',
                time_in_force= 'day',)
        except Exception as e:
            logger.error(e)
    count = wait
    while count > 0:
        pending = api.list_orders()
        if len(pending) == 0:
            logger.info(f'all sell orders done')
            break
        logger.info(f'{len(pending)} sell orders pending')
        time.sleep(1)
        count -= 1

    #Buy Orders Next
    buys = [o for o in orders if o['side'] == 'buy']
    for order in buys:
        try:
            logger.info(f'submit(buy): {order}')
            api.submit_order(
                symbol = order['symbol'],
                qty=order['qty'],
                side='buy',
                type='market',
                time_in_force='day', )
        except Exception as e:
            logger.error(e)
    count = wait
    while count > 0:
        pending = api.list_orders()
        if len(pending) == 0:
            logger.info(f'all buy orders done')
            break
        logger.info(f'{len(pending)} buy orders pending')
        time.sleep(1)
        count -= 1


#Setting up the loop
def main():
    done = None
    logging.info('Running...')
    while True:
        clock = api.get_clock()
        now = clock.timestamp
        if clock.is_open and done != now.strftime('%Y-%m-%d'):
            price_df = prices(Universe)
            orders = build_orders(api, price_df)
            trade(orders)
            done = now.strftime('%Y-%m-%d')
            logger.info(f'done for {done}')

        time.sleep(1)

