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


if __name__ == '__main__':
    cvt_config = get_config()
    print(cvt_config)

    pass
