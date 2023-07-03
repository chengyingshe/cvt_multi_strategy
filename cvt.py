import configparser
import os
import re
import pandas as pd

has_err = False

def check_path_exists(path, err, new=False):
    global has_err
    if not new:
        if not os.path.exists(path):
            print(err)
            has_err = True
    else:
        if not os.path.exists(path):
            print(f'路径 {path} 不存在，自动创建该路径')
            os.mkdir(path)

def get_config():
    config_file_path = './config.ini'
    if not os.path.exists(config_file_path):
        raise Exception('当前路径下不存在配置文件 config.ini')
    config = configparser.ConfigParser()
    config.read(config_file_path, encoding='utf-8')
    atgo_dir = config.get('Config', 'ATGO')
    check_path_exists(atgo_dir, 'ATGO解算文件路径错误')
    ato_dir = config.get('Config', 'ATO')
    check_path_exists(ato_dir, 'ATO解算文件路径错误')
    atx_dir = config.get('Config', 'ATX')
    check_path_exists(atx_dir, 'ATX解算文件路径错误')
    atable = config.get('Config', 'client_broker_association_table')
    check_path_exists(atable, '客户-券商关联表文件不存在')
    mapping = config.get('Config', 'Mapping_A_B_Broker_Dir')
    check_path_exists(mapping, 'Mapping_A_B_Broker文件夹路径错误')
    output_dir = config.get('Config', 'output_dir')
    check_path_exists(output_dir, '', True)
    if has_err:
        raise Exception('配置文件异常')

# 获取路径中所有的excel文件路径
def get_all_excel_path(dir):
    pass

# 从df数据中获取origin_cname列，然后生成new_cname列
# new_cdata_cvt_fun为转换function
def cvt_col_from_to(df, origin_cname, new_cname, new_cdata_cvt_fun=None):
    clist = df[origin_cname].values
    if new_cdata_cvt_fun:
        clist = [new_cdata_cvt_fun(c) for c in clist]
    cdata = pd.DataFrame({new_cname: clist})
    return cdata


if __name__ == '__main__':
    pass
