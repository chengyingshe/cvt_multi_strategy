import configparser
import glob
import os
import re
import pandas as pd

has_err = False


def check_path_exists(path, err, new=False, need_have_err=True):
    global has_err
    if not new:
        if not os.path.exists(path):
            print(err)
            has_err = need_have_err
    else:
        if not os.path.exists(path):
            print(f'路径 {path} 不存在，自动创建该路径')
            os.mkdir(path)

atgo_dir = ''
ato_dir = ''
atx_dir = ''
atable = ''
mapping_broker_dir = ''
output_dir = ''

def get_config():  # 解析配置文件
    global atgo_dir, atx_dir, ato_dir, atable, mapping_broker_dir, output_dir
    config_file_path = './config.ini'
    if not os.path.exists(config_file_path):
        raise Exception('当前路径下不存在配置文件 config.ini')
    config = configparser.ConfigParser()
    config.read(config_file_path, encoding='utf-8')
    atgo_dir = config.get('Config', 'ATGO')
    check_path_exists(atgo_dir, 'ATGO结算文件路径错误（忽略）', need_have_err=False)
    ato_dir = config.get('Config', 'ATO')
    check_path_exists(ato_dir, 'ATO结算文件路径错误（忽略）', need_have_err=False)
    atx_dir = config.get('Config', 'ATX')
    check_path_exists(atx_dir, 'ATX结算文件路径错误（忽略）', need_have_err=False)
    atable = config.get('Config', 'client_broker_association_table')
    check_path_exists(atable, '客户-券商关联表文件不存在')
    mapping_broker_dir = config.get('Config', 'Mapping_A_B_Broker_Dir')
    check_path_exists(mapping_broker_dir, 'Mapping_A_B_Broker文件夹路径错误')
    output_dir = config.get('Config', 'output_dir')
    check_path_exists(output_dir, '', True, need_have_err=False)
    if has_err:
        raise Exception('配置文件异常')

# 获取路径中所有的excel文件路径
def get_all_excel_path(pdir):
    excel_files = glob.glob(os.path.join(pdir, "*.xlsx"))  # 获取所有后缀为xlsx的文件
    excel_files.extend(glob.glob(os.path.join(pdir, "*.xls")))  # 获取所有后缀为xls的文件
    excel_files.extend(glob.glob(os.path.join(pdir, "*.csv")))
    return excel_files

# 从df数据中获取origin_cname列，然后生成new_cname列
# new_cdata_cvt_fun为转换function   要写转换函数
def cvt_col_from_to(df, origin_cname, new_cname, new_cdata_cvt_fun=None):
    clist = df[origin_cname].values
    if new_cdata_cvt_fun:
        clist = [new_cdata_cvt_fun(c) for c in clist]
    cdata = pd.DataFrame({new_cname: clist})
    return cdata

market_type = ['无效', '深交所', '上交所', '中金所', '上期所', '大商所', '郑商所', '能源交易所', '北交所', '港股通(深)', '港股通(沪)', '港交所']
order_type = ['无效', '限价委托', '即时成交剩余转撤销', '最优五档即时成交剩余转限价', '最优五档即时成交剩余转撤销', '全部成交或撤销', '本方最优价格', '对方最优价格', '期权限价申报FOK',
              '盘后固定价格', '最新价', '昨收价', '涨停价', '跌停价', '买1', '买2', '买3', '买4', '买5', '卖1', '卖2', '卖3', '卖4', '卖5']
side = ['无效', '买入', '卖出', '买劵还劵', '融券卖出', '卖券还款', '直接还款', '直接还券', '融券回购（逆回购）', '新股申购', '新债申购', '大宗买入', '大宗卖出']
order_status = ['无效', '未报', '已报', '部成', '已成', '已撤', '待撤', '废单', '部撤', '内部废单', '内部撤单', '待报', '撤单拒绝']
glob_date = ''


def get_index_from_list(li, v, not_found=0):
    if v in li:
        return li.index(v)
    return not_found


def get_excel_path_list_from_dir(file_dir, date, *args):  # 传入不定长（正则表达式）
    # [[file11, file21,...],[file21, file22,...],...]
    # ex: [[委托查询 成交查询 绩效查询]]
    all_list = []
    li = os.listdir(file_dir)


def get_client_broker_map(file_path):
    df = pd.read_excel(file_path)
    account_user = df['account_user'].values
    code = df['券商编号'].values
    return dict(zip(account_user, code))


def get_algo_type(account_user, symbol, client_broker_map, mapping_broker_dir, date):
    # symbol：证券代码
    if account_user not in client_broker_map:
        return 103
    broker_code = client_broker_map[account_user]
    broker_mapping_file_path = f'broker_mapping_{date}.csv'
    if not os.path.exists(os.path.join(mapping_broker_dir, broker_mapping_file_path)):
        return 103
    broker_mapping_df = pd.read_excel(broker_mapping_file_path)
    stgroute = broker_mapping_df[broker_mapping_df['BrokerNo'] == broker_code]['StgRoute'].values
    if stgroute.empty:  # 未找到对应的策略
        return 103
    stg_df = pd.read_csv(stgroute[0])  # 读取策略文件
    has_accountS = (stg_df['accountS'] == account_user).values
    has_symbol = [s != '-1' and s.split('.')[0] == symbol for s in stg_df['symbol'].values]
    if not stg_df[has_accountS and has_symbol].empty:
        return 107
    if not stg_df[has_accountS].empty:
        return 104
    return 103

def save_csv_to(df, type=0):  # 0->子单，1->母单
    output_file_name = 'ActualOrder.csv' if type == 0 else 'AlgoOrder.csv'
    df.to_csv(os.path.join(output_dir, output_file_name), index=False)

def time_apppend(df, origin_date_name, original_time_name, target_date_name):  # return一个20230504123800的dataFrame
    date = df[origin_date_name].values
    time = df[original_time_name].values
    dt = []
    for i in range(len(date)):
        dt.append(date[i].replace('/', '') + time[i].replace(':', ''))
    result = pd.DataFrame({target_date_name: dt})
    return result

def cvt_ato_actualorder_0(df):
    global glob_date
    suanfazidanbianhao = cvt_col_from_to(df, '算法子单编号', '算法子单编号')
    suanfamudanbianhao = cvt_col_from_to(df, '母单序号', '算法母单编号')
    jiaoyiriqi = cvt_col_from_to(df, '委托日期', '交易日期', lambda x: x.replace('/', ''))
    shichangleibie = cvt_col_from_to(df, '交易市场', '市场类别', lambda x: get_index_from_list(market_type, x))
    zijinzhanghumingcheng = cvt_col_from_to(df, '资产账户名称', '资金账户名称')
    # 算法类型
    suanfaleixing = cvt_col_from_to(df, '资产账户名称', '算法类型', lambda x: 0)  # 固定拆单0
    # 算法供应商
    suanfagongyingshang = cvt_col_from_to(df, '资产账户名称', '算法供应商', lambda x: '多策略')  # 固定多策略
    zhengquandaima = cvt_col_from_to(df, '证券代码', '证券代码')
    weituoleixing = cvt_col_from_to(df, '价格类型', '委托类型', lambda x: get_index_from_list(order_type, x))
    maimaifangxiang = cvt_col_from_to(df, '买卖方向', '买卖方向', lambda x: get_index_from_list(side, x))
    weituojiage = cvt_col_from_to(df, '委托价格(港股通单位为港币)', '委托价格')
    weituoshuliang = cvt_col_from_to(df, '委托数量', '委托数量')
    # 委托时间
    date = df['委托日期'].values
    time = df['委托时间'].values
    glob_date = date[0].replace('/', '')
    dt = []
    for i in range(len(date)):
        dt.append(date[i].replace('/', '') + time[i].replace(':', ''))
    weituoshijian = pd.DataFrame({'委托时间': dt})
    chengjiaojiage = cvt_col_from_to(df, '成交均价(港股通单位为港币)', '成交价格')
    chengjiaoshuliang = cvt_col_from_to(df, '成交数量', '成交数量')
    # 成交时间（使用委托时间）
    chengjiaoshijian = pd.DataFrame({'成交时间': dt})
    weituozhuangtai = cvt_col_from_to(df, '委托状态', '委托状态', lambda x: get_index_from_list(order_status, x))
    shouxufei = cvt_col_from_to(df, '总费用', '手续费')
    # 算法实例
    '''
    m = get_client_broker_map(atable)
    account_user_list = df['资产账户名称'].values
    symbol_list = df['证券代码'].values
    algo_list = []
    for i in range(len(account_user_list)):
        algo_list.append(get_algo_type(account_user_list[i], symbol_list[i], m, mapping_broker_dir, glob_date))
    suanfashili = pd.DataFrame({'算法实例': algo_list})
    '''
    suanfashili = pd.DataFrame({'算法实例': [103] * len(weituoshijian)})
    return pd.concat(
        [suanfazidanbianhao, suanfamudanbianhao, jiaoyiriqi, shichangleibie, zijinzhanghumingcheng, suanfaleixing,
         suanfashili, suanfagongyingshang, zhengquandaima, weituoleixing, maimaifangxiang, weituojiage,
         weituoshuliang, weituoshijian, chengjiaojiage, chengjiaoshuliang, chengjiaoshijian, weituozhuangtai, shouxufei], axis=1)


def cvt_ato_algoorder_0(df):  # 拆单 母单
    # global glob_date
    sfmdbh = cvt_col_from_to(df, '母单编号', '算法母单编号')
    jyrq = cvt_col_from_to(df, '交易日期', '交易日期', lambda x: x.replace('/', ''))
    zjzhmc = cvt_col_from_to(df, '资产账户名称', '资金账户名称')
    sflx = cvt_col_from_to(df, '母单状态', '算法类型', lambda x: 0)  # 固定拆单0
    ### 算法实例
    sfsl = cvt_col_from_to(df, '母单状态', '算法实例', lambda x: '103')
    sfgys = cvt_col_from_to(df, '母单状态', '算法供应商', lambda x: '多策略')  # 固定多策略
    rws = cvt_col_from_to(df, '母单数量', '任务数')
    zqdm = cvt_col_from_to(df, '证券代码', '证券代码')
    jylb = cvt_col_from_to(df, '交易市场', '市场类别', lambda x: get_index_from_list(market_type, x))
    mdfx1 = cvt_col_from_to(df, '母单方向', '买卖方向1', lambda x: get_index_from_list(side, x))
    mdfx2 = cvt_col_from_to(df, '母单方向', '买卖方向2', lambda x: '')
    kssj = time_apppend(df, '交易日期', '母单开始时间', '开始时间')
    jssj = time_apppend(df, '交易日期', '母单结束时间', '结束时间')
    xdsj = time_apppend(df, '交易日期', '母单开始时间', '下单时间')

    merged_df = pd.concat([sfmdbh, jyrq, zjzhmc, sflx, sfsl, sfgys, rws, zqdm, jylb,
                           mdfx1, mdfx2, kssj, jssj, xdsj], axis=1)
    return merged_df


def cvt_ato_algoorder_1(df):  # T0 母单
    sfmdbh = cvt_col_from_to(df, '母单编号', '算法母单编号')
    jyrq = cvt_col_from_to(df, '交易日期', '交易日期', lambda x: x.replace('/', ''))
    zjzhmc = cvt_col_from_to(df, '资产账户名称', '资金账户名称')
    sflx = cvt_col_from_to(df, '产品名称', '算法类型', lambda x: 1)  # 固定T0  是1
    ### 算法实例
    sfsl = cvt_col_from_to(df, '产品名称', '算法实例', lambda x: '103')
    sfgys = cvt_col_from_to(df, '产品名称', '算法供应商', lambda x: '多策略')  # 固定 多策略
    rws = cvt_col_from_to(df, '任务数量', '任务数')
    zqdm = cvt_col_from_to(df, '证券代码', '证券代码')
    jylb = cvt_col_from_to(df, '交易市场', '市场类别', lambda x: get_index_from_list(market_type, x))
    mdfx1 = cvt_col_from_to(df, '买入方向', '买卖方向1', lambda x: get_index_from_list(side, x))
    mdfx2 = cvt_col_from_to(df, '卖出方向', '买卖方向2', lambda x: get_index_from_list(side, x))
    kssj = cvt_col_from_to(df, '开始时间', '开始时间', lambda x: pd.to_datetime(x).strftime('%Y%m%d%H%M%S'))
    jssj = cvt_col_from_to(df, '结束时间', '结束时间', lambda x: pd.to_datetime(x).strftime('%Y%m%d%H%M%S'))
    xdsj = cvt_col_from_to(df, '开始时间', '下单时间', lambda x: pd.to_datetime(x).strftime('%Y%m%d%H%M%S'))

    merged_df = pd.concat([sfmdbh, jyrq, zjzhmc, sflx, sfsl, sfgys, rws, zqdm, jylb,
                           mdfx1, mdfx2, kssj, jssj, xdsj], axis=1)
    return merged_df

# 主函数
def cvt():
    # ATO
    get_config()
    ato_path = '.\各产品线结算格式\ATO/委托查询_20230614.xlsx'
    df = pd.read_excel(ato_path)
    new_df = cvt_ato_actualorder_0(df)
    save_csv_to(new_df, type=0)


if __name__ == '__main__':
    cvt()
