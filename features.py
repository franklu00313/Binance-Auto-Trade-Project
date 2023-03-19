import pandas as pd
import talib

def add_feature(raw_data):

    # first 
    for symbol in raw_data:
        ohlcv = raw_data[symbol]
        df = pd.DataFrame(ohlcv).set_index(0)
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        df.index = pd.to_datetime(df.index,unit='ms')
        df.index.name = 'datetime'
        raw_data[symbol] = df

    # calculate the features(talib)

    for symbol in raw_data:
        for i in [1,2,4]:
            df = raw_data[symbol]
            raw_data[symbol]['ADXR'+str(i)] = talib.ADXR(df['high'], df['low'], df['close'], timeperiod=14*i)
            raw_data[symbol]['MACD'+str(i)], raw_data[symbol]['MACDsignal'+str(i)], raw_data[symbol]['MACDhist'+str(i)] = talib.MACD(df['close'], fastperiod=12*i, slowperiod=26*i, signalperiod=9*i)


    # calculate the features (handmade)
    features = {}
    for col in raw_data[symbol].columns:
        
        # concat all df with same col
        features[col] = pd.concat([raw_data[i][col] for i in raw_data.keys()],axis=1)
        features[col].columns = raw_data.keys()
        
        # set df name to col name
        features[col].name = col

    # calculate indicator features

    close = features['close']
    def bias(n):
        return close / close.rolling(n, min_periods=1).mean()

    def acc(n):
        return close.shift(n) / (close.shift(2*n) + close) * 2

    def rsv(n):
        l = close.rolling(n, min_periods=1).min()
        h = close.rolling(n, min_periods=1).max()
        return (close - l) / (h - l)

    indicator_features = {
        # bias
        'bias5': bias(5),
        'bias10': bias(10),
        'bias20': bias(20),
        
        # acc
        'acc5': acc(5),
        'acc10': acc(10),
        'acc20': acc(20),
        
        # rsv
        'rsv5': rsv(5),
        'rsv10': rsv(10),
        'rsv20': rsv(20),
    }

    features = {**indicator_features, **features}
    features

    for name, f in features.items():
        features[name] = f.unstack()

    dataset = pd.DataFrame(features)
    dataset = dataset.drop(columns=['open',	'high',	'low','close','volume'])
    dataset.index.names = ['symbol', 'datetime']
    
    return dataset.groupby('symbol').last()