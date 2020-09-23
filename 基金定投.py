__Author__ = 'XMY'

import tushare as ts
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


token = 'your token'  # 注册tushare pro账户（https://tushare.pro/register?reg=368740），并获取token
ts.set_token(token)  # 设置token

pro = ts.pro_api()  # 初始化pro接口

fund_list = pro.fund_basic(market='E')  # 获取场内基金列表

white_wine = fund_list.loc[fund_list['name'].str.contains('白酒')]  # 获取白酒相关的基金列表



def calc_return(df, period_type='W', start_date=None, end_date=None, fixed_investment=500, if_intelligent=False):
    '''
    基金定投收益
    :param df: 基金原始数据
    :param period_type: 定投周期，默认为周"W"
    :param start_date: 基金定投起始日期，默认为None
    :param end_date: 基金定投结束日期，默认为None
    :param fixed_investment: 定投金额，默认为500
    :param if_intelligent: 是否智能定投，默认为False
    :return: 基金定投金额
    '''
    df_periods = df.resample(period_type).last()
    df_periods_cut = df_periods[start_date:end_date]  # 选定定投区间
    df = df.copy()
    # 计算定投金额
    if if_intelligent:
        df_periods_cut.loc[
            df_periods_cut['ts_code'].notnull(), 'fixed_investment'
        ] = fixed_investment * df_periods_cut['invest_ratio']
    else:
        df_periods_cut.loc[df_periods_cut['ts_code'].notnull(), 'fixed_investment'] = fixed_investment
    # 剔除含na值的行
    df_periods_cut = df_periods_cut.dropna()
    # 计算累积投资份额、累计投资金额
    df['fixed_investment'] = df_periods_cut['fixed_investment']
    df['cum_investment'] = df['fixed_investment'].cumsum()
    df['buy_num'] = df['fixed_investment'] / df['close_adj']  # 计算购买份额
    df['cum_buy_num'] = df['buy_num'].cumsum()
    # na值处理
    df[['cum_investment', 'cum_buy_num']] = df[['cum_investment', 'cum_buy_num']].ffill()
    df[['fixed_investment', 'buy_num']] = df[['fixed_investment', 'buy_num']].fillna(0)
    # 计算持有基金价值
    df['hold_fund_value'] = df['cum_buy_num']*df['close_adj']
    df['average_cost'] = df['cum_investment']/df['cum_buy_num']
    # 计算收益率
    df['return'] = df['hold_fund_value'] / df['cum_investment']
    return df[['cum_investment', 'cum_buy_num', 'hold_fund_value', 'average_cost', 'return']]


period_type = 'W-FRI'  # 每周五定投：W-FRI, 每月第一周周一定投：WOM-1MON
fixed_investment = 500
# 设置定投时间段
start_date = None
end_date = None

for ts_code, m_fee, c_fee in white_wine[['ts_code', 'm_fee', 'c_fee']].values:
    # 获取基金日行情数据、复权因子
    df_daily = pro.fund_daily(ts_code=ts_code, start_date='20160801', end_date='20200901')
    df_adj = pro.fund_adj(ts_code=ts_code, start_date='20160801')
    # 设置为时间序列
    df_daily['trade_date'] = pd.to_datetime(df_daily['trade_date'])
    df_adj['trade_date'] = pd.to_datetime(df_adj['trade_date'])
    df_daily.set_index('trade_date', inplace=True)
    df_adj.set_index('trade_date', inplace=True)
    # 合并日行情和复权因子表
    df = pd.merge(df_daily, df_adj['adj_factor'], left_index=True, right_index=True, how='inner')
    # 计算复权_收盘价
    df['close_adj'] = df['close']*df['adj_factor']
    df.sort_values(by='trade_date', inplace=True)
    # 绘制曲线图
    # df[['close_adj']].plot()
    # plt.show()
    
    # 计算基金定投收益
    df[
        ['cum_investment', 'cum_buy_num', 'hold_fund_value', 'average_cost', 'return']
    ] = calc_return(df, period_type=period_type, start_date=start_date, end_date=end_date)

    
    # 保存数据
    df.to_csv(f'fund_{ts_code[:6]}.csv')


