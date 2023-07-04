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


def get_config():  # 解析配置文件
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
    mapping = config.get('Config', 'Mapping_A_B_Broker_Dir')
    check_path_exists(mapping, 'Mapping_A_B_Broker文件夹路径错误')
    output_dir = config.get('Config', 'output_dir')
    check_path_exists(output_dir, '', True)
    if has_err:
        raise Exception('配置文件异常')
    result = {
        "atgo_dir": atgo_dir,
        "ato_dir": ato_dir,
        "atx_dir": atx_dir,
        "atable": atable,
        "mapping": mapping,
        "output_dir": output_dir,
    }
    return result


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


# 主函数
def cvt():
    pass


market_type = ['无效', '深交所', '上交所', '中金所', '上期所', '大商所', '郑商所', '能源交易所', '北交所', '港股通(深)', '港股通(沪)', '港交所']
order_type = ['无效', '限价委托', '即时成交剩余转撤销', '最优五档即时成交剩余转限价', '最优五档即时成交剩余转撤销', '全部成交或撤销', '本方最优价格', '对方最优价格', '期权限价申报FOK',
              '盘后固定价格', '最新价', '昨收价', '涨停价', '跌停价', '买1', '买2', '买3', '买4', '买5', '卖1', '卖2']


def get_index_from_list(li, v, not_found=0):
    if v in li:
        return li.index(v)
    return not_found


def cvt_ato_actualorder_1(df):
    suanfazidanbianhao = cvt_col_from_to(df, '算法子单编号', '算法子单编号')
    suanfamudanbianhao = cvt_col_from_to(df, '母单序号', '算法母单编号')
    jiaoyiriqi = cvt_col_from_to(df, '委托日期', '交易日期', lambda x: x.replace('/', ''))
    shichangleibie = cvt_col_from_to(df, '交易市场', '市场类别', lambda x: get_index_from_list(market_type, x))
    zijinzhanghumingcheng = cvt_col_from_to(df, '资产账户名称', '资金账户名称')
    # 算法类型
    suanfaleixing = cvt_col_from_to(df, '资产账户名称', '算法类型', lambda x: 0)  # 固定拆单0
    # 算法实例

    # 算法供应商
    suanfagongyingshang = cvt_col_from_to(df, '资产账户名称', '算法供应商', lambda x: '多策略')  # 固定多策略
    zhengquandaima = cvt_col_from_to(df, '证券代码', '证券代码')
    weituoleixing = cvt_col_from_to(df, '价格类型', '委托类型')


if __name__ == '__main__':
    cvt_config = get_config()
    print(cvt_config)

    pass
