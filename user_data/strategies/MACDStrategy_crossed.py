
# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import CategoricalParameter, IntParameter,DecimalParameter
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class MACDStrategy_crossed(IStrategy):
    """
        buy:
            MACD crosses MACD signal above
            and CCI < -50
        sell:
            MACD crosses MACD signal below
            and CCI > 100
    """

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
         "0": 0.015,
    #    "0": 0.159,
    #    "34": 0.051,
    #    "63": 0.028,
    #    "143": 0.01
    }

    # Stoploss:
    stoploss = -0.99

    # Trailing stop:
    trailing_stop = False
    trailing_stop_positive = 0.023
    trailing_stop_positive_offset = 0.109
    trailing_only_offset_is_reached = False


    # Optimal timeframe for the strategy
    timeframe = '5m'

    cci_buy_param = IntParameter(-700,0, default=-50, space='buy', optimize=True)
    cci_sell_param = IntParameter(0, 700, default=100, space='sell', optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['cci'] = ta.CCI(dataframe)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe['macd'], dataframe['macdsignal']) &
                (dataframe['cci'] <= self.cci_buy_param.value)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                qtpylib.crossed_below(dataframe['macd'], dataframe['macdsignal']) &
                (dataframe['cci'] >= self.cci_sell_param.value)
            ),
            'sell'] = 1

        return dataframe
