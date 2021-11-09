# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
# freqtrade hyperopt --hyperopt-loss SharpeHyperOptLoss --spaces  roi trailing --strategy NNStraBBRSI

import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import logging

logger = logging.getLogger(__name__)

# This class is a sample. Feel free to customize it.
class NNStraBBRSI(IStrategy):
    """
    This is a sample strategy to inspire you.
    More information in https://www.freqtrade.io/en/latest/strategy-customization/
    You can:
        :return: a Dataframe with all mandatory indicators for the strategies
    - Rename the class name (Do not forget to update class_name)
    - Add any methods you want to build your strategy
    - Add any lib you need to build your strategy
    You must keep:
    - the lib in the section "Do not remove these libs"
    - the methods: populate_indicators, populate_buy_trend, populate_sell_trend
    You should keep:
    - timeframe, minimal_roi, stoploss, trailing_*
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 2




    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
     # ROI table:
    minimal_roi = {
        # "0": 0.159,
        # "34": 0.051,
        # "63": 0.028,
        # "143": 0.01
        "0": 0.015,
    }

    # Stoploss:
    stoploss = -0.99

    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.028
    trailing_stop_positive_offset = 0.109
    trailing_only_offset_is_reached = False

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
            'ema5': {'color': 'yellow'},
            'ema15': {'color': 'orange'},
            'ema30': {'color': 'red'},
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

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:

        df['rsi'] = ta.RSI(df, timeperiod=14)
        bollinger_1sd = qtpylib.bollinger_bands(qtpylib.typical_price(df), window=20, stds=1)
        df['bb_lowerband_1sd'] = bollinger_1sd['lower']
        df['bb_middleband_1sd'] = bollinger_1sd['mid']
        df['bb_upperband_1sd'] = bollinger_1sd['upper']
        df['adx'] = ta.ADX(df)

        stoch_rsi = ta.STOCHRSI(df)
        df['fastd_rsi'] = stoch_rsi['fastd']
        df['fastk_rsi'] = stoch_rsi['fastk']

        df['rsi_compare'] = (df['fastd_rsi'] > df['fastk_rsi'])
        df['bb'] = (df['close'].shift(1) > df['bb_lowerband_1sd'])

        # get distance to the bottom
        timeframe = 24
        lookback_hr = 1
        window_value = int((60/timeframe) * lookback_hr)
        df['top'] = df['close'].rolling(window=window_value).max().shift(1)
        df['bottom'] = df['close'].rolling(window=window_value).min().shift(1)
        df['distance_top'] = df['top'].shift(1)-df['close'].shift(1)
        df['distance_bottom'] = df['close'].shift(1) - df['bottom'].shift(1)

        df['ema100'] = ta.EMA(df, timeperiod=100)
        df['price_ema'] = df['close'] - df['ema100']

        # From God Strategy
        df['minusdi'] = ta.MINUS_DI(df, timeperiod=50)
        df['line'] =  ta.LINEARREG_INTERCEPT(df, timeperiod=55)


        final_df = df[['close','rsi','adx','rsi_compare','minusdi','line','bb','distance_top','distance_bottom','price_ema']]
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(final_df)
        #print(final_df)

        import tensorflow as tf
        from tensorflow import keras
        model = keras.models.load_model("/freqtrade/user_data/model-crypto-bbrsi.h5")
        results = model.predict(scaled_data)
        #print("NN Prediction Complete .... ")
        #print("########## NN prediction result ############")
        # for i in range(len(results)):
        #     print(results[:,0])

        df['profit'] = pd.Series(results[:,0], index=df.index)
        #print(df['profit'].iloc[100:200])
        #print("########## NN prediction result ############")
        return df

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:


        dataframe.loc[
            (
                (dataframe['profit'].shift(1) > 0.9)
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
