__Author__ = 'XMY'

import tushare as ts
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


token = '3fe0d647a8bf07ea5c44586c84937da91ea4f8feb41ce5121cad408e'
ts.set_token(token)  # 设置token

pro = ts.pro_api()  # 初始化pro接口

fund_list = pro.fund_basic(market='E')  # 获取场内基金列表

white_wine = fund_list.loc[fund_list['name'].str.contains('白酒')]


# ==智能定投，T-1复权价与历史均线比较: 高位少买，低位多买
def intelligent_fixed_investment(df, fixed_investment, ma=500):
    df_ma = df['close_adj'].rolling(ma, min_periods=1).mean()
    # =高位少买：T-1复权价高于历史均线，
    # 0-15%：定投90%
    # 15-50%：定投80%
    # 50-100%：定投70%
    # >100%：定投60%
    # =低位多买：
    # 0-5%：160%
    # 5-10%：170%
    # 10-20%: 180%
    # 20-30%: 190%
    # 30-40%: 200%
    # >40%: 210%
    bins = [0, 0.6, 0.7, 0.8, 0.9, 0.95, 1, 1.15, 1.5, 2, 10]
    labels = 2.1, 2, 1.9, 1.8, 1.7, 1.6, 0.9, 0.8, 0.7, 0.6
    close_ma = df['close_adj']/df_ma  # 计算复权价与均线的比值
    invest_ratio_1 = pd.cut(close_ma, bins=bins, labels=labels)  # 利用区间统计计算定投比例

    # # 低位多买策略中，若10日振幅>5%实际扣款率：
    # # 计算10振幅
    # df_flunctuat = df['close_adj'].rolling(ma, min_periods=1).apply(lambda x: x.max()/x.min()-1)
    # # 0-5%，定投60%
    # # 5-10%：70%
    # # 10-20%: 80%
    # # 20-30%: 90%
    # # 30-40%: 100%
    # # >40%: 110%
    # var = close_ma[(df_flunctuat > 0.05) & (invest_ratio_1.astype(float)>1)]
    # if len(var) == 0:
    #     pass
    # else:
    #     bins = [0, 0.6, 0.7, 0.8, 0.9, 0.95, 1]
    #     labels = 1.1, 1, 0.9, 0.8, 0.7, 0.6
    #     invest_ratio_2 = pd.cut(var, bins=bins, labels=labels)
    # print(df)
    df['invest_ratio'] = invest_ratio_1.astype(float)
    # df.loc[invest_ratio_2.index, 'invest_ratio'] = invest_ratio_2.astype(float)
    return df


def calc_return(df, df_periods, fixed_investment=500, if_intelligent=False):
    df = df.copy()
    # 计算定投金额
    if if_intelligent:
        df_periods.loc[df_periods['ts_code'].notnull(), 'fixed_investment'] = fixed_investment * df_periods[
            'invest_ratio']
    else:
        df_periods.loc[df_periods['ts_code'].notnull(), 'fixed_investment'] = fixed_investment
    # 剔除含na值的行
    df_periods = df_periods.dropna()
    # 计算累积投资份额、累计投资金额
    df['fixed_investment'] = df_periods['fixed_investment']
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


periods = 'W-FRI'  # 每周五定投：W-FRI, 每月第一周周一定投：WOM-1MON
fixed_investment = 500
# 设置定投时间段
start_date = None
end_date = None

for ts_code, m_fee, c_fee in white_wine[['ts_code', 'm_fee', 'c_fee']].values:
    # 获取基金日行情数据、复权因子
    df_daily = pro.fund_daily(ts_code=ts_code)
    df_adj = pro.fund_adj(ts_code=ts_code)
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
    # 按周期进行定投
    df = intelligent_fixed_investment(df, fixed_investment=fixed_investment, ma=500)  # 智能定投计算
    df_periods = df.resample(periods).last()
    df_periods_cut = df_periods[start_date:end_date]  # 选定定投区间
    # 计算基金定投收益
    df[
        ['cum_investment', 'cum_buy_num', 'hold_fund_value', 'average_cost', 'return']
    ] = calc_return(df, df_periods_cut)

    # 智能定投：
    # 计算基金定投收益
    df['invest_ratio'] = df['invest_ratio'].shift()  # 找到T-1的定投因子
    df[
        ['i_cum_investment', 'i_cum_buy_num', 'i_hold_fund_value', 'i_average_cost', 'i_return']
    ] = calc_return(df, df_periods_cut, if_intelligent=True)

    df.loc[:, ['return', 'i_return']].plot()
    plt.show()

    # 保存数据
    df.to_csv(f'fund_{ts_code[:6]}_1.csv')




df_down = df.loc[start_date:end_date, ]
df_down['benchmark'] = df_down['close_adj']/df_down['close_adj'].iloc[0]
df_down


df[['return', 'i_return']].plot(figsize=(18, 8))
plt.show()
