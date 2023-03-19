import os
from binance_ccxt import *
from dotenv import load_dotenv
from line_notify import lineNotifyMessage

def rebalance_weight(request):
    """
    Automatically Called by Cloud Function every hour
    
    """


    # ====================== load env variable ======================

    load_dotenv(override=True)
    test_future_api_key =os.getenv("TEST_FUTURE_API_KEY")
    test_future_api_secret = os.getenv("TEST_FUTURE_API_SECRET")
    total_fund = float(os.getenv("TOTAL_FUND"))
    line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")
    line_picture_url = os.getenv("LINE_PICTURE_URL")

    # ========================== make order ==========================

    # login to binance account
    exchange = binance_init(test_future_api_key, test_future_api_secret, 'future', True)

    # get current positions
    current_positions = get_positions(exchange)

    # get target positions (load model and predict)
    target_list = predict(exchange)
    target_position = get_target_position(target_list, total_fund)

    # calculate order_dict
    order_dict = calculate_order(exchange, current_positions,target_position)

    # make order
    order_placed_msg = make_order(exchange, order_dict)

    # =========================== line notify ===========================

    # message init
    message = "\n\n《下單通知》"

    # get order_placed_msg
    message += order_placed_msg

    # get current account info
    account_msg = get_current_account_info(exchange)
    message += account_msg['balance_msg']
    message += account_msg['position_msg']

    # send line message
    res_status_code = lineNotifyMessage(line_notify_token, message,True,line_picture_url,line_picture_url)
    log = "Line Notify messages sent." if res_status_code == 200 else "Line Notify Crashed."

    return {"message": message, "log": log}


def send_daily_report(request):
    """
    Automatically Called by Cloud Function at 23:55:00 UTC+8
    """

    # =============================== load env variable ===============================

    load_dotenv(override=True)
    test_future_api_key =os.getenv("TEST_FUTURE_API_KEY")
    test_future_api_secret = os.getenv("TEST_FUTURE_API_SECRET")
    line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")
    line_picture_url = os.getenv("LINE_PICTURE_URL")
    symbols = ["BTC","ETH","BNB","XRP","DOGE","ADA","MATIC","DOT","LTC","1000SHIB"]
    symbols = [i + "USDT" for i in symbols]

    # ============================ get today closed trades ============================

    # login to binance account
    exchange = binance_init(test_future_api_key, test_future_api_secret, 'future', True)

    # get today closed trades

    start_date, end_date = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d")
    today_closed_trades = get_closed_trade_records(exchange,symbols, start_date, end_date, timeZone=8)

    closed_trades_msg = ""
    for trade in today_closed_trades:
        time = f"{trade['datetime'].hour}:{trade['datetime'].minute}"
        symbol = trade['symbol'][4:] if trade['symbol'][:4] == '1000' else trade['symbol']
        realizedPnl = str(round(float(trade['realizedPnl']),2))
        realizedPnl = '0.00' if (realizedPnl == '-0.0') or realizedPnl=='0.0' else realizedPnl
        closed_trades_msg += f"\n{time.center(5)} S {symbol.center(10)} {realizedPnl.center(5)}U"

    # get today total pnl
    total_pnl = round(sum([float(i['realizedPnl']) for i in today_closed_trades]),2)

    # =============================== line notify ===============================

    # get total pnl
    message = f"\n\n《本日已實現損益》\n{total_pnl}U"

    # message init
    message += f"\n\n《本日已實現明細》\n{'時間'.center(5)}|{'交易對'.center(7)}|{'已實現損益'.center(7)}\n" + "-"*30

    # get closed trades msg
    message += closed_trades_msg

    # send line message
    res_status_code = lineNotifyMessage(line_notify_token, message,True,line_picture_url,line_picture_url)
    log = "Line Notify messages sent." if res_status_code == 200 else "Line Notify Crashed."
    
    return {"message": message, "log": log}