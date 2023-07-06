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


def get_client_broker_map(file_path):
    df = pd.read_excel(file_path)
    account_user = df['account_user'].values
    code = df['券商编号'].values
    return dict(zip(account_user, code))


def get_algo_instance(account_user, symbol, client_broker_map, mapping_broker_dir, date):
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
    if not os.path.exists(stgroute[0]):
        return 103
    stg_df = pd.read_csv(stgroute[0])  # 读取策略文件
    has_accountS = (stg_df['accountS'] == account_user).values
    has_symbol = [s != '-1' and s.split('.')[0] == symbol for s in stg_df['symbol'].values]
    if not stg_df[has_accountS and has_symbol].empty:
        return 107
    if not stg_df[has_accountS].empty:
        return 104
    return 103


# type : 0->子单，1->母单
# sys_type : 0->ato, 1->atx, 2->atgo
def save_csv_to(df, type, sys_type, algo_type):
    output_file_name = 'ActualOrder' if type == 0 else 'AlgoOrder'
    if sys_type == 0:
        output_file_name += '_ATO'
    elif sys_type == 1:
        output_file_name += '_ATX'
    else:
        output_file_name += '_ATGO'
    output_file_name += '_拆单.csv' if algo_type == 0 else '_T0.csv'
    output_file_path = os.path.join(output_dir, output_file_name)
    df.to_csv(output_file_path, index=False)
    print(f'成功生成文件 {output_file_path}')


def time_apppend(df, origin_date_name, original_time_name, target_date_name):  # return一个20230504123800的dataFrame
    date = df[origin_date_name].values
    time = df[original_time_name].values
    dt = []
    for i in range(len(date)):
        dt.append(date[i].replace('/', '') + time[i].replace(':', ''))
    result = pd.DataFrame({target_date_name: dt})
    return result


def get_excel_path_list_from_dir(file_dir, pat):  # pat为正则表达式数组 定长2
    matching_files = []
    # 按照pat中元素顺序 遍历文件夹中的所有文件
    for file_name in os.listdir(file_dir):
        if re.match(pat[0], file_name) :
            file_path = os.path.join(file_dir,file_name)
            matching_files.append(file_path)
            break
    for file_name in os.listdir(file_dir):
        if re.match(pat[1], file_name) :
            file_path = os.path.join(file_dir,file_name)
            matching_files.append(file_path)
            break
    return matching_files


def get_algo_instance_df(df, account_cname, symbol_cname, algo_type_cname):  # 资产账户名称 证券代码
    m = get_client_broker_map(atable)
    account_user_list = df[account_cname].values
    symbol_list = df[symbol_cname].values
    algo_list = []
    for i in range(len(account_user_list)):
        algo_list.append(get_algo_instance(account_user_list[i], symbol_list[i], m, mapping_broker_dir, glob_date))
    suanfashili = pd.DataFrame({algo_type_cname: algo_list})
    return suanfashili


def cvt_ato_actualorder_0(df):  # ATO 拆单 子单
    global glob_date
    suanfazidanbianhao = cvt_col_from_to(df, '算法子单编号', '算法子单编号')
    suanfamudanbianhao = cvt_col_from_to(df, '母单序号', '算法母单编号')
    jiaoyiriqi = cvt_col_from_to(df, '委托日期', '交易日期', lambda x: x.replace('/', ''))
    glob_date = jiaoyiriqi.iloc[0].values[0]
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
    weituoshijian = time_apppend(df, '委托日期', '委托时间', '委托时间')
    chengjiaojiage = cvt_col_from_to(df, '成交均价(港股通单位为港币)', '成交价格')
    chengjiaoshuliang = cvt_col_from_to(df, '成交数量', '成交数量')
    # 成交时间（使用委托时间）
    chengjiaoshijian = weituoshijian
    weituozhuangtai = cvt_col_from_to(df, '委托状态', '委托状态', lambda x: get_index_from_list(order_status, x))
    shouxufei = cvt_col_from_to(df, '总费用', '手续费')
    # 算法实例
    # suanfashili = get_algo_instance_df(df, '资产账户名称', '证券代码', '算法实例')
    suanfashili = pd.DataFrame({'算法实例': [103] * len(weituoshijian)})
    return pd.concat(
        [suanfazidanbianhao, suanfamudanbianhao, jiaoyiriqi, shichangleibie, zijinzhanghumingcheng, suanfaleixing,
         suanfashili, suanfagongyingshang, zhengquandaima, weituoleixing, maimaifangxiang, weituojiage,
         weituoshuliang, weituoshijian, chengjiaojiage, chengjiaoshuliang, chengjiaoshijian, weituozhuangtai,
         shouxufei], axis=1)


def cvt_ato_actualorder_1(df):  # ATO T0 子单
    global glob_date
    suanfazidanbianhao = cvt_col_from_to(df, '委托序号', '算法子单编号')
    suanfamudanbianhao = cvt_col_from_to(df, '母单序号', '算法母单编号')
    jiaoyiriqi = cvt_col_from_to(df, '日期', '交易日期', lambda x: x.replace('/', ''))
    glob_date = jiaoyiriqi.iloc[0].values[0]
    shichangleibie = cvt_col_from_to(df, '交易市场', '市场类别', lambda x: get_index_from_list(market_type, x))
    zijinzhanghumingcheng = cvt_col_from_to(df, '资产账户', '资金账户名称')
    # 算法类型
    suanfaleixing = cvt_col_from_to(df, '资产账户', '算法类型', lambda x: 1)  # 固定拆单0
    # 算法供应商
    suanfagongyingshang = cvt_col_from_to(df, '资产账户', '算法供应商', lambda x: '多策略')  # 固定多策略
    zhengquandaima = cvt_col_from_to(df, '证券代码', '证券代码')
    weituoleixing = cvt_col_from_to(df, '价格类型', '委托类型', lambda x: get_index_from_list(order_type, x))
    maimaifangxiang = cvt_col_from_to(df, '买卖方向', '买卖方向', lambda x: get_index_from_list(side, x))
    weituojiage = cvt_col_from_to(df, '委托价格(港股通单位为港币)', '委托价格')
    weituoshuliang = cvt_col_from_to(df, '委托数量', '委托数量')
    # 委托时间
    weituoshijian = time_apppend(df, '委托日期', '委托时间', '委托时间')
    chengjiaojiage = cvt_col_from_to(df, '成交均价(港股通单位为港币)', '成交价格')
    chengjiaoshuliang = cvt_col_from_to(df, '成交数量', '成交数量')
    # 成交时间（使用委托时间）
    chengjiaoshijian = weituoshijian
    weituozhuangtai = cvt_col_from_to(df, '委托状态', '委托状态', lambda x: get_index_from_list(order_status, x))
    shouxufei = cvt_col_from_to(df, '总费用', '手续费')
    # 算法实例
    # suanfashili = get_algo_instance_df(df, '资产账户名称', '证券代码', '算法实例')
    suanfashili = pd.DataFrame({'算法实例': [103] * len(weituoshijian)})
    return pd.concat(
        [suanfazidanbianhao, suanfamudanbianhao, jiaoyiriqi, shichangleibie, zijinzhanghumingcheng, suanfaleixing,
         suanfashili, suanfagongyingshang, zhengquandaima, weituoleixing, maimaifangxiang, weituojiage,
         weituoshuliang, weituoshijian, chengjiaojiage, chengjiaoshuliang, chengjiaoshijian, weituozhuangtai,
         shouxufei], axis=1)


def cvt_ato_algoorder_0(df):  # ATO 拆单 母单
    global glob_date
    sfmdbh = cvt_col_from_to(df, '母单编号', '算法母单编号')
    jyrq = cvt_col_from_to(df, '交易日期', '交易日期', lambda x: x.replace('/', ''))
    glob_date = jyrq.iloc[0].values[0]
    zjzhmc = cvt_col_from_to(df, '资产账户名称', '资金账户名称')
    sflx = cvt_col_from_to(df, '母单状态', '算法类型', lambda x: 0)  # 固定拆单0
    # 算法实例
    # sfsl = get_algo_instance_df(df, '资产账户名称', '证券代码', '算法实例')
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


def cvt_ato_algoorder_1(df):  # ATO T0 母单
    global glob_date
    sfmdbh = cvt_col_from_to(df, '母单编号', '算法母单编号')
    jyrq = cvt_col_from_to(df, '交易日期', '交易日期', lambda x: x.replace('/', ''))
    glob_date = jyrq.iloc[0].values[0]
    zjzhmc = cvt_col_from_to(df, '资产账户名称', '资金账户名称')
    sflx = cvt_col_from_to(df, '产品名称', '算法类型', lambda x: 1)  # 固定T0  是1
    # 算法实例
    # sfsl = get_algo_instance_df(df, '资产账户名称', '证券代码', '算法实例')
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


side_atgo = ['', 'B', 'S', 'CB', 'SS', 'SB', 'CB', '0']


# 买卖方向—B 为买，S 为卖，CB 为买券还券，SS 为融券卖出，
# SB 为融资买入，CB 为买券还券，0 为 T0

def time_process_atgo(df, date, time, col_name):  # atgo 的时间合并工具
    date_list = df[date].values
    date_data = pd.DataFrame({date: date_list})
    date_data[date] = date_data[date].astype(str)
    date_data = cvt_col_from_to(date_data, date, date, lambda x: x.replace('-', ''))  # csv好像和xlsx不一样 '-'不是'/'
    time_list = df[time].values
    time_data = pd.DataFrame({time: time_list})
    time_data[time] = time_data[time].astype(str)
    res = pd.DataFrame({col_name: date_data[date] + time_data[time]})
    return res


order_status_atgo = ['', '', 'New', 'PartialFill', 'Filled', 'Canceled', 'PendingCancel', 'Rejected', '', '', '',
                     'PendingNew', 'Stop']

# ATGO子单(已完成)
def cvt_atgo_actualorder(df, algo_type):  # ATGO 子单 algo_type=0/1
    global glob_date
    suanfazidanbianhao = cvt_col_from_to(df, 'ClOrdID', '算法子单编号')
    suanfamudanbianhao = cvt_col_from_to(df, 'QuoteID', '算法母单编号')
    jiaoyiriqi = cvt_col_from_to(df, 'Date', '交易日期', lambda x: x.replace('/', ''))
    glob_date = jiaoyiriqi.iloc[0].values[0]
    # 市场类别
    shichangleibie = cvt_col_from_to(df, 'Symbol', '市场类别', lambda x: 1 if x.split('.')[1] == 'SZ' else 2)
    zijinzhanghumingcheng = cvt_col_from_to(df, 'ClientName', '资金账户名称')
    # 算法类型
    suanfaleixing = cvt_col_from_to(df, 'Date', '算法类型', lambda x: algo_type)  # 固定拆单0
    # 算法供应商
    suanfagongyingshang = cvt_col_from_to(df, 'Date', '算法供应商', lambda x: '多策略')  # 固定多策略
    zhengquandaima = cvt_col_from_to(df, 'Symbol', '证券代码', lambda x: x.split('.')[0])
    weituoleixing = cvt_col_from_to(df, 'OrdType', '委托类型', lambda x: 1)  # 固定为限价
    maimaifangxiang = cvt_col_from_to(df, 'Side', '买卖方向', lambda x: get_index_from_list(side_atgo, x) if get_index_from_list(side_atgo, x) != 12 else 7)
    weituojiage = cvt_col_from_to(df, 'Price', '委托价格')
    weituoshuliang = cvt_col_from_to(df, 'OrderQty', '委托数量')
    # 委托时间
    dl = df['Date'].values
    tl = df['TransactTime'].values
    for i in range(len(dl)):
        dl[i] = dl[i].replace('/', '') + str(tl[i])
    weituoshijian = pd.DataFrame({'委托时间': dl})
    chengjiaojiage = cvt_col_from_to(df, 'AvgPx', '成交价格')
    chengjiaoshuliang = cvt_col_from_to(df, 'CumQty', '成交数量')
    # 成交时间（使用委托时间）
    chengjiaoshijian = weituoshijian
    ### 委托状态
    weituozhuangtai = cvt_col_from_to(df, 'OrdStatus', '委托状态', lambda x: get_index_from_list(order_status_atgo, x))
    shouxufei = cvt_col_from_to(df, 'OtherFee', '手续费')
    # 算法实例
    # suanfashili = get_algo_instance_df(df, 'ClientName', 'Symbol', '算法实例')
    suanfashili = pd.DataFrame({'算法实例': [103] * len(weituoshijian)})
    return pd.concat(
        [suanfazidanbianhao, suanfamudanbianhao, jiaoyiriqi, shichangleibie, zijinzhanghumingcheng, suanfaleixing,
         suanfashili, suanfagongyingshang, zhengquandaima, weituoleixing, maimaifangxiang, weituojiage,
         weituoshuliang, weituoshijian, chengjiaojiage, chengjiaoshuliang, chengjiaoshijian, weituozhuangtai,
         shouxufei], axis=1)

# 未完成 70%
def cvt_atgo_algoorder(df, algo_type):  # ATGO 母单 algo_type=0/1  对algoNominal文件解析
    global glob_date
    sfmdbh = cvt_col_from_to(df, 'ClOrdID', '算法母单编号')
    jyrq = cvt_col_from_to(df, 'Date', '交易日期', lambda x: x.replace('/', ''))
    glob_date = jyrq.iloc[0].values[0]
    zjzhmc = cvt_col_from_to(df, 'ClientName', '资金账户名称')
    sflx = cvt_col_from_to(df, 'Date', '算法类型', lambda x: algo_type)  # 固定T0  是1
    # 算法实例
    # sfsl = get_algo_instance_df(df, '资产账户名称', '证券代码', '算法实例')
    sfsl = cvt_col_from_to(df, 'Date', '算法实例', lambda x: '103')
    sfgys = cvt_col_from_to(df, 'Date', '算法供应商', lambda x: '多策略')  # 固定 多策略
    rws = cvt_col_from_to(df, 'TaskQty', '任务数')
    zqdm = cvt_col_from_to(df, 'Symbol', '证券代码')

    jylb = cvt_col_from_to(df, 'Symbol', '市场类别', lambda x: 1 if x.split('.')[1] == 'SZ' else 2)  ###没找到
    if algo_type == 0:  # 拆单
        mdfx1 = cvt_col_from_to(df, 'Side', '买卖方向1', lambda x: get_index_from_list(side_atgo, x))
        mdfx2 = cvt_col_from_to(df, 'Side', '买卖方向2', lambda x: 0)
    else:  # T0
        mdfx1 = cvt_col_from_to(df, 'Side', '买卖方向1', lambda x: 'T0')
        mdfx2 = cvt_col_from_to(df, 'Side', '买卖方向2', lambda x: 'T0')

    # 时间要改   已改
    kssj = time_process_atgo(df, 'Date', 'StartTime', '开始时间')
    jssj = time_process_atgo(df, 'Date', 'EndTime', '结束时间')
    xdsj = kssj

    merged_df = pd.concat([sfmdbh, jyrq, zjzhmc, sflx, sfsl, sfgys, rws, zqdm, jylb,
                           mdfx1, mdfx2, kssj, jssj, xdsj], axis=1)
    return merged_df

def time_process_atx(df, date, time, col_name):  # atx 的时间合并工具
    date_list = df[date].values
    date_data = pd.DataFrame({date: date_list})
    date_data[date] = date_data[date].astype(str)
    time_list = df[time].values
    time_data = pd.DataFrame({time: time_list})
    time_data = cvt_col_from_to(time_data, time, time, lambda x: x.replace(':', ''))  # csv好像和xlsx不一样 '-'不是'/'
    time_data[time] = time_data[time].astype(str)
    res = pd.DataFrame({col_name: date_data[date] + time_data[time]})
    return res

# ATX子单(已完成)
def cvt_atx_actualorder(df, algo_type):  # ATX 子单 algo_type=0/1
    global glob_date
    suanfazidanbianhao = cvt_col_from_to(df, '委托编号', '算法子单编号')
    suanfamudanbianhao = cvt_col_from_to(df, '母单编号', '算法母单编号')
    jiaoyiriqi = cvt_col_from_to(df, '委托日期', '交易日期', lambda x: str(x))
    glob_date = str(jiaoyiriqi.iloc[0].values[0])
    shichangleibie = cvt_col_from_to(df, '交易市场', '市场类别', lambda x: get_index_from_list(market_type, x))
    zijinzhanghumingcheng = cvt_col_from_to(df, '资金账号', '资金账户名称')
    # 算法类型
    suanfaleixing = cvt_col_from_to(df, '证券代码', '算法类型', lambda x: algo_type)  # 固定拆单0
    # 算法供应商
    suanfagongyingshang = cvt_col_from_to(df, '证券代码', '算法供应商', lambda x: '多策略')  # 固定多策略
    zhengquandaima = cvt_col_from_to(df, '证券代码', '证券代码', lambda x: x.split('.')[0])
    # 委托类型
    weituoleixing = cvt_col_from_to(df, '证券代码', '委托类型', lambda x: 1)  # 委托类型固定为1
    maimaifangxiang = cvt_col_from_to(df, '交易方向', '买卖方向', lambda x: get_index_from_list(side, x))
    weituojiage = cvt_col_from_to(df, '委托价格', '委托价格')
    weituoshuliang = cvt_col_from_to(df, '委托数量', '委托数量')
    # 委托时间
    tl = df['委托时间'].values
    dl = df['委托日期'].values
    for i in range(len(tl)):
        tl[i] = str(dl[i]) + tl[i].replace(':', '')
    weituoshijian = pd.DataFrame({'委托时间': tl})
    chengjiaojiage = cvt_col_from_to(df, '成交均价', '成交价格')
    chengjiaoshuliang = cvt_col_from_to(df, '成交数量', '成交数量')
    # 成交时间（使用委托时间）
    chengjiaoshijian = weituoshijian
    weituozhuangtai = cvt_col_from_to(df, '子单状态', '委托状态', lambda x: get_index_from_list(order_status, x))
    shouxufei = cvt_col_from_to(df, '其他费用', '手续费')
    # 算法实例
    # suanfashili = get_algo_instance_df(df, '资产账户名称', '证券代码', '算法实例')
    suanfashili = pd.DataFrame({'算法实例': [103] * len(weituoshijian)})
    return pd.concat(
        [suanfazidanbianhao, suanfamudanbianhao, jiaoyiriqi, shichangleibie, zijinzhanghumingcheng, suanfaleixing,
         suanfashili, suanfagongyingshang, zhengquandaima, weituoleixing, maimaifangxiang, weituojiage,
         weituoshuliang, weituoshijian, chengjiaojiage, chengjiaoshuliang, chengjiaoshijian, weituozhuangtai,
         shouxufei], axis=1)

# 未完成 90%
def cvt_atx_algoorder(df, algo_type):  # ATX 母单 algo_type=0/1
    global glob_date
    sfmdbh = cvt_col_from_to(df, '母单编号', '算法母单编号')
    jyrq = cvt_col_from_to(df, '交易日期', '交易日期')
    glob_date = jyrq.iloc[0].values[0]
    zjzhmc = cvt_col_from_to(df, '资金账号', '资金账户名称')
    sflx = cvt_col_from_to(df, '母单编号', '算法类型', lambda x: algo_type)
    # 算法实例
    # sfsl = get_algo_instance_df(df, '资产账户名称', '证券代码', '算法实例')
    sfsl = cvt_col_from_to(df, '母单编号', '算法实例', lambda x: '103')
    sfgys = cvt_col_from_to(df, '母单编号', '算法供应商', lambda x: '多策略')  # 固定 多策略
    rws = cvt_col_from_to(df, '任务数量', '任务数')
    zqdm = cvt_col_from_to(df, '证券代码', '证券代码')
    jylb = cvt_col_from_to(df, '交易市场', '市场类别', lambda x: get_index_from_list(market_type, x))

    # 跟algo_type有关
    if algo_type == 0:  # 拆单
        mdfx1 = cvt_col_from_to(df, '交易方向', '买卖方向1', lambda x: get_index_from_list(side, x))
        mdfx2 = cvt_col_from_to(df, '交易方向', '买卖方向2', lambda x: 0)
    else:  # T0
        mdfx1 = cvt_col_from_to(df, '买入方向', '买卖方向1', lambda x: get_index_from_list(side, x))
        mdfx2 = cvt_col_from_to(df, '卖出方向', '买卖方向2', lambda x: get_index_from_list(side, x))

    ###
    kssj = time_process_atx(df, '交易日期', '开始时间', '开始时间')
    jssj = time_process_atx(df, '交易日期', '开始时间', '结束时间')
    xdsj = kssj

    merged_df = pd.concat([sfmdbh, jyrq, zjzhmc, sflx, sfsl, sfgys, rws, zqdm, jylb,
                           mdfx1, mdfx2, kssj, jssj, xdsj], axis=1)
    return merged_df

# 主函数
def cvt():
    get_config()
    if ato_dir != '':
        ato_dir_0 = os.path.join(ato_dir, '0')
        ato_dir_1 = os.path.join(ato_dir, '1')
        if len(os.listdir(ato_dir_0)) > 0:
            li = get_excel_path_list_from_dir(ato_dir_0, ['委托查询_\d+.xlsx', '绩效查询_母单绩效_汇总_\d+.xlsx'])
            save_csv_to(cvt_ato_actualorder_0(pd.read_excel(li[0])), 0, 0, 0)
            # save_csv_to(cvt_ato_algoorder_0(pd.read_excel(li[1])), 1, 0)
        if len(os.listdir(ato_dir_1)) > 0:
            li = get_excel_path_list_from_dir(ato_dir_0, ['委托查询_\d+.xlsx', '母单收益_\d+.xlsx'])
            save_csv_to(cvt_ato_actualorder_1(pd.read_excel(li[0])), 0, 0, 1)
            # save_csv_to(cvt_ato_algoorder_1(pd.read_excel(li[1])), 1, 0)
    if atx_dir != '':
        atx_dir_0 = os.path.join(atx_dir, '0')
        atx_dir_1 = os.path.join(atx_dir, '1')
        if len(os.listdir(atx_dir_0)) > 0:
            li = get_excel_path_list_from_dir(atx_dir_0, ['algoActual.csv', 'algoNominal.csv'])
            save_csv_to(cvt_atx_actualorder(pd.read_csv(li[0], encoding='gbk'), 0), 0, 1, 0)
            # save_csv_to(cvt_atx_algoorder(pd.read_excel(li[1]), 0), 1, 0)
        if len(os.listdir(atx_dir_1)) > 0:
            li = get_excel_path_list_from_dir(atx_dir_1, ['algoActual.csv', 'algoNominal.csv'])
            save_csv_to(cvt_atx_actualorder(pd.read_csv(li[0], encoding='gbk'), 1), 0, 1, 1)
            # save_csv_to(cvt_atx_algoorder(pd.read_excel(li[1]), 1), 1, 0)
    if atgo_dir != '':
        atgo_dir_0 = os.path.join(atgo_dir, '0')
        atgo_dir_1 = os.path.join(atgo_dir, '1')
        if len(os.listdir(atgo_dir_0)) > 0:
            li = get_excel_path_list_from_dir(atgo_dir_0, ['algoActual.csv', 'algoNominal.csv'])
            save_csv_to(cvt_atgo_actualorder(pd.read_csv(li[0], encoding='gbk'), 0), 0, 2, 0)
            # save_csv_to(cvt_atx_algoorder(pd.read_excel(li[1]), 0), 1, 0)
        if len(os.listdir(atgo_dir_1)) > 0:
            li = get_excel_path_list_from_dir(atgo_dir_1, ['algoActual.csv', 'algoNominal.csv'])
            save_csv_to(cvt_atgo_actualorder(pd.read_csv(li[0], encoding='gbk'), 1), 0, 2, 1)
            # save_csv_to(cvt_atx_actualorder(pd.read_excel(li[1]), 1), 1, 0)

if __name__ == '__main__':
    cvt()
