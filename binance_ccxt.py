import ccxt
from typing import Union
from datetime import datetime
from features import add_feature
import joblib
from google.cloud import storage


def binance_init(api_key: str, api_secret: str, trade_type: str = 'spot', test_flag: bool = True):
    """
      Four kinds of logging way to binance. (default spot testing account)
      1. trade_type: spot / future
      2. account: test / real

      # example
      binanceSpotTest = binance_init(test_spot_api_key,test_spot_api_secret)
      binanceFutureTest = binance_init(test_future_api_key,test_future_api_secret,'future')
      binanceSpot = binance_init(trade_api_key,trade_api_secret,'spot',False)
      binanceFuture = binance_init(trade_api_key,trade_api_secret,'future',False)
      print("測試現貨: ",binanceSpotTest.fetch_balance()["USDT"])
      print("測試合約: ",binanceFutureTest.fetch_balance()["USDT"])
      print("實際現貨: ",binanceSpot.fetch_balance()["USDT"])
      print("實際合約: ",binanceFuture.fetch_balance()["USDT"])
    """
    exchange_id = 'binance'
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'apiKey': api_key,
        'secret': api_secret,
        'options': {
            'defaultType': trade_type,
        }
    })
    exchange.set_sandbox_mode(test_flag)
    # 可察看各貨幣對資訊，如exchange.markets["BTC/USDT"]。也用來檢查訂單合法性
    exchange.load_markets(True)
    return exchange

def get_balance(exchange):
    """
    
    
    """
    balance = exchange.fetch_balance()['info']['totalWalletBalance']
    return balance

def get_positions(exchange):
    """
    
    
    """
    positions = exchange.fetch_balance()['info']['positions']
    # active position
    positions = [i for i in positions if i['initialMargin'] != '0']
    
    # simplified the positions
    positions = [{'symbol': i['symbol'],'positionAmt':i['positionAmt'], 'notional': i['notional'], 'unrealizedProfit': i['unrealizedProfit']} for i in positions]

    return positions


def predict(exchange):
    """ Load trained model from bucket and predict.
    
    Return: 
        For Example: ['BTCUSDT', 'ETHUSDT', 'DOTUSDT'] 
    
    """
    # get raw data
    raw_data = {}
    currency_pairs = ["BTC","ETH","BNB","XRP","DOGE","ADA","MATIC","DOT","LTC","1000SHIB"]
    for symbol in currency_pairs:
        symbol = symbol + "USDT"
        params = {'timeframe':'1m', 'limit':600}
        ohlcv = exchange.fetch_ohlcv(symbol, **params)
        raw_data[symbol] = ohlcv

    # calculate features
    feature_data = add_feature(raw_data)

    # load model from GCS
    model = load_model('model-weight', 'lightgbm_model.pkl')

    # predict
    feature_data['predict'] = model.predict(feature_data)
    target_list = list(feature_data.sort_values(by=['predict'], ascending=False).head(3).index)

    return target_list

def load_model(bucket_name, model_filename):

    # Download the model weights from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(model_filename)
    blob.download_to_filename(f'/tmp/{model_filename}')  

    # Load the model weights
    model = joblib.load(f'/tmp/{model_filename}')
    return model

def get_target_position(target_list, total_fund)-> dict[str, float]:  
    """ Set position for each target currency pair (equal weight)

    Input : ['BTC', 'ETH', 'DOT', 'LTC', 'SHIB'], 1000
    Return: {'BTC': 200.0, 'ETH': 200.0, 'DOT': 200.0, 'LTC': 200.0, 'SHIB': 200.0}

    """
    target_dict = {}
    position_per_target = total_fund / len(target_list)

    for i in target_list:
        target_dict[i] = position_per_target

    return target_dict

def calculate_order(exchange,positions,target_position):
    """ calculate the difference between target position and current position
    
    
    """
    # change target_position from {symbol: fund} to {symbol: amount}
    order_dict = {symbol:fund/exchange.fetch_ticker(symbol)['last']  for symbol,fund in target_position.items()}

    # subtract those from current_position
    for position in positions:
        symbol, position_amount = position['symbol'], float(position['positionAmt'])
        if symbol in order_dict:
            order_dict[symbol] -= position_amount
        else:
            order_dict[symbol] = -position_amount

    return order_dict

def make_order(exchange, order_dict):

    # according to order_dict, place order
    msg = ""
    for symbol, amount in order_dict.items():
        try:
            if amount > 0:
                order_msg = exchange.create_market_buy_order(symbol, amount)
            else:
                order_msg = exchange.create_market_sell_order(symbol, -amount)
            info = order_msg['info']
            cumQuote, avgPrice = "{:.4g}".format(float(info['cumQuote'])), round(float("{:.5g}".format(float(info['avgPrice']))),2)
            # cumQuote, avgPrice = round(float(info['cumQuote']),2), round(float(info['avgPrice']),2)
            side = "B" if info['side'] == 'BUY' else "S"
            symbol = info['symbol'][4:] if info['symbol'][:4] == '1000' else info['symbol']
            msg += f"\n{side} {symbol}@{avgPrice}～{cumQuote}U"
        except:
            msg += f"\nF {symbol} FAILED."
    
    return msg

def close_all_positions(exchange):
    """
        clear all position
    """
    
    for position in get_positions(exchange):
        if float(position['positionAmt']) > 0:
            exchange.create_market_sell_order(position['symbol'], float(position['positionAmt']))
        else:
            exchange.create_market_buy_order(position['symbol'], -float(position['positionAmt']))
    
    return

def get_trade_records(exchange,symbols=['BTCUSDT',"ETHUSDT"], start_time="2022-12-27", end_time="2022-12-27", timeZone = 8):
    """
        Binance datetime is UTC+0, so we need to add 8 hours to get the correct time (UTC+8)
    """
    day = 24 * 60 * 60 * 1000
    trade_records = []
    original_start_time = exchange.parse8601(f'{start_time}T00:00:00') - timeZone * 60 * 60 * 1000
    original_end_time = exchange.parse8601(f'{end_time}T00:00:00') - timeZone * 60 * 60 * 1000
    now = exchange.milliseconds()
    for symbol in symbols:
        start_time = original_start_time
        while (start_time < now) and (start_time <= original_end_time):
            next_time = start_time + day
            trades = exchange.fetch_my_trades(symbol, start_time, None, {'endTime': next_time,})
            if len(trades):
                last_trade = trades[len(trades) - 1]
                start_time = last_trade['timestamp'] + 1
                trade_records = trade_records + trades
            else:
                start_time = next_time
    
    return trade_records


def get_closed_trade_records(exchange,symbols, start_time, end_time, timeZone = 8):
    """    
    filter the closed trade records, and simplified the data to be sent by line-notify later
    """
    # get all trade records
    trade_records = get_trade_records(exchange, symbols, start_time, end_time,timeZone)
    
    # datetime.fromtimestamp will automatically convert the timestamp to UTC+8
    closed_trade_records = [{'datetime':datetime.fromtimestamp(trade['timestamp']/1000),'symbol':trade['symbol'],'price':trade['price'],'qty':trade['info']['qty'],'realizedPnl':trade['info']['realizedPnl'], } for trade in trade_records if trade['side'] == 'sell']

    return closed_trade_records

def get_current_account_info(exchange):

    # get current balance
    balance = round(float(get_balance(exchange)),2)
    balance_msg = f"\n\n《總資產》\n  {balance} USDT"

    # get current positions
    positions = get_positions(exchange)
    position_msg = f"\n\n《目前持倉》\n{'交易對'.center(5)}|{'持倉金額'.center(5)}|{'未實現損益'.center(5)}\n" + "-"*30

    for i in positions:
        # if start with 1000, then remove 1000
        if i['symbol'][:4] == '1000':
            symbol = i['symbol'][4:]
        else:
            symbol = i['symbol']
        notional, unrealizedProfit = str(round(float(i['notional']),0)), str(round(float(i['unrealizedProfit']),2))
        position_msg += f"\n{symbol.center(10)}|{notional.center(10)}|{unrealizedProfit.center(10)}"

    return {"balance_msg": balance_msg, "position_msg": position_msg}



# ================================== Future Work ==================================

def order_with_sl_tp(symbol: str, type: str, side: str, amount: Union[int, float], price: Union[int, float], stop_loss: float = None, take_profit: float = None) -> list[str]:
    """
        create an order with stop loss & take profit, SL & TP will be OCO.
        return list of orders -> to create an OCO detector
    """

    pass


def pred_to_order(pred_side: int, pred_prob: float):
    """
        turn model output to order, using order_with_sl_tp
    """

    pass


def check_oco(order_pair: list[str]):
    """
        input: order_pair(id), usually for SL & TP

        If an order is filled, cancel the other one, return True.
        Otherwise(both order remain open), return False
    """

    pass


# 最小市價單問題待處理!!

def is_order_valid() -> bool:
    """
    priority low (binance will check and return message error)

    ref: https://docs.ccxt.com/en/latest/manual.html?highlight=amount_to_precision#precision-and-limits

    Must satisfy following condition:
        + Order amount >= limits['amount']['min']
        + Order amount <= limits['amount']['max']
        + Order price >= limits['price']['min']
        + Order price <= limits['price']['max']
        + Order cost (amount * price) >= limits['cost']['min']
        + Order cost (amount * price) <= limits['cost']['max']
        + Precision of amount must be <= precision['amount']
        + Precision of price must be <= precision['price']
    """
    pass


def get_market_order_qty(symbol: str, amount: Union[int, float] = 10) -> Union[int, float]:
    """
        Calculate  market order qty.
        Amount divide avgPrice, considering precision, min notation.
        Return: the qty of market order.

        ref: https://docs.ccxt.com/en/latest/manual.html?highlight=amount_to_precision#precision-and-limits
    """

    pass
