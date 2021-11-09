# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
import tensorflow as tf
from tensorflow import keras
from datetime import timedelta

from sklearn.preprocessing import MinMaxScaler

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


# This class is a sample. Feel free to customize it.
class RNNStra(IStrategy):

    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 2

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
     # ROI table:
     # ROI table:
    minimal_roi = {
        # "0": 0.159,
        # "34": 0.051,
        # "63": 0.028,
        # "143": 0.01
        "0": 0.01,
    }

    # Stoploss:
    stoploss = -0.99

    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.028
    trailing_stop_positive_offset = 0.109
    trailing_only_offset_is_reached = False


    # Hyperoptable parameters
    buy_rsi = IntParameter(low=1, high=50, default=30, space='buy', optimize=True, load=True)
    sell_rsi = IntParameter(low=50, high=100, default=70, space='sell', optimize=True, load=True)

    # Optimal timeframe for the strategy.
    timeframe = '5m'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the "ask_strategy" section in the config.
    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Optional order type mapping.
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
    }

    plot_config = {
        'main_plot': {
            'prediction': {'color': 'blue'},
        },
        'subplots': {
            "MACD": {
                'macd': {'color': 'blue'},
                'macdsignal': {'color': 'orange'},
            },
            "RSI": {
                'rsi': {'color': 'red'},
            }
        }
    }

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        ## load data and scale
        time_steps = 50
        future_candle = 10
        data = dataframe['close'].values
        date = dataframe['date'].iloc[-1]

        #print("################################ populate_indicators() called ")
        print("Processing data length:",len(data))
        print("latest time", date);
        shaped_data = np.reshape(data, (-1,1))

        #print(dataframe.columns)
        scaler = MinMaxScaler(feature_range=(0,1))

        scaler.fit(shaped_data)
        scaled_data = scaler.transform(shaped_data)

        # create sequence
        X = []
        y = []
        for i in range(time_steps, len(scaled_data)):
            X.append(scaled_data[i-time_steps:i,0])
            y.append(scaled_data[i, 0])
        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))

        prev_X = X#X[-50:]
        print("1st input: ",len(prev_X))
        # Start prediction
        model = keras.models.load_model("model-lstm.h5")

        results = model.predict(prev_X)
        pred_price = np.reshape(results, (-1,1))
        #print(pred_price)
        #predict next 5 candles
        pred_ft_price = pred_price
        prediction = []
        for i in range(future_candle):
            if i!=0:
                invert_ft_price = scaler.inverse_transform(pred_ft_price)
                prediction.append(invert_ft_price[-1][0])

            newseq = []
            newseq.append(prev_X[-1][1:len(prev_X[-1])].tolist())
            #print("predicted: ",pred_ft_price[-1])
            newseq[0].append(pred_ft_price[-1])
            #print( np.array(newseq))
            #print("--------------------------------------")
            prev_X = np.append(prev_X,(np.array(newseq)),axis=0)
            #print("new rec: ",prev_X)
            #print("predicting :",len(prev_X))
            results = model.predict(prev_X)
            pred_ft_price = np.reshape(results, (-1,1))

            #print(prev_X)
        #print("prediction:",prediction)
        invert_price = scaler.inverse_transform(pred_price)

        #prepend the empty prediction in the first 50 rows of result
        for i in range(time_steps):
            invert_price = np.insert(invert_price,0,-99)

        #add prediction column in dataframe

        dataframe['prediction'] = pd.Series(invert_price, index=dataframe.index)

        # add five candle in the future
        final_time = date
        n = 5
        for i in range(len(prediction)):
            #print("future: ",prediction[i])
            pred_val = prediction[i]
            final_time = final_time + timedelta(minutes=n)
            future_price = pd.DataFrame({"date":[final_time],"prediction":[pred_val]})
            dataframe = dataframe.append(future_price,ignore_index=True)

        dataframe['future_price'] = dataframe['prediction'].shift(-(future_candle-1))
        dataframe['future_change'] = 0
        dataframe.loc[((dataframe['future_price']>0) & (dataframe['prediction']>0)), 'future_change']  = (dataframe['future_price'] - dataframe['prediction'].shift(-1))/ dataframe['prediction'].shift(-1)
        dataframe = dataframe[:-len(prediction)]

        #print("predicted price --->")
        #print(dataframe['prediction'].iloc[-20:])
        #print("predicted change --->")
        #print(dataframe['future_change'].iloc[-20:])
        #print("########## NN prediction result ############")
        # for i in range(len(results)):
        #     print(results[:,0])

        #dataframe['profit'] = pd.Series(results[:,0], index=dataframe.index)
        #print(dataframe['profit'].iloc[100:200])

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:


        dataframe.loc[
            (
                dataframe['future_change'] > 0.01
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
        #        (dataframe['rsi'] > 83) &  # Signal: RSI is greater 83
        #        (dataframe['close'] > dataframe['bb_upperband_1sd']) # Signal: price is greater than mid bb
            ),
            'sell'] = 0
        return dataframe
