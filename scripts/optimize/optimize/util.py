import re
import math
import itertools
import pandas as pd
import numpy as np

def isint(s):  # 正規表現を使って判定を行う
    p = '[-+]?\d+'
    return True if re.fullmatch(p, s) else False

def isfloat(s):  # 正規表現を使って判定を行う
    p = '[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?'
    return True if re.fullmatch(p, s) else False

def digit(s):  # 正規表現を使って小数点以下の桁数
    if re.search("\.",s)!= None:
        return len(re.split("\.",s)[1])
    else:
        return 0

def stringToNum(s):
    if isint(s):
        return int(s)

    elif isfloat(s):
        return float(s)

    else:
        raise ValueError("値が数値ではありません。")



def vaild_number(x, num):
    if x == 0:
        return 0
    else:
        return round(x, num - math.floor(math.log10(abs(x)))- 1)

def SIstr(num):
    l = math.log(num,10)
    if l >= -1:
        return '{:.2f}'.format(num)
    elif -1 > l and l >= -4:
        return '{:.2f}'.format(num*10**3) + "m"
    elif -4 > l and l >= -7:
        return '{:.2f}'.format(num*10**6) + "u"
    elif -7 > l and l >= -10:
        return '{:.2f}'.format(num*10**9) + "n"
    else:
        return '{:.2f}'.format(num*10**12) + "p"

def create_inp_df(*args):
    print(len(args))
    if not len(args)%4 == 0:
        raise ValueError("引数は tag1, start1, stop1, increment1, tag2, start2, stop2, increment2, .....を指定してください")

    print(len(args))
    spl_list = [args[idx:idx + 4] for idx in range(0, len(args), 4)]
    col_list = [l[0] for l in spl_list]
    print(len(spl_list))
    pro_list = [ np.round(np.arange(l[1],l[2]+l[3],l[3]),3) for l in spl_list]
    return pd.DataFrame(itertools.product(*pro_list), columns=col_list)