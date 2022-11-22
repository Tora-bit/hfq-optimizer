from cmath import nan
import re
import pandas as pd
from .util import stringToNum, isfloat, isint, vaild_number
from .pyjosim import simulation
from .judge import comfirm_pre_switch, get_switch_timing, compare_switch_timings, state_judgement
from .config import Config
from .calculator import shunt_calc, rand_norm
from .graph import margin_plot, sim_plot
import numpy as np
import concurrent.futures
import copy
import os
import sys
import shutil
from tqdm import tqdm


class Data:
    def __init__(self, raw_data : str, config : dict):
        
        # get variable
        self.vdf, self.raw_sim_data = self.__get_variable(raw=raw_data)

        # check config file
        self.conf : Config = Config(config)

        # create netlist
        self.sim_data = self.__create_netlist(self.raw_sim_data, self.conf)

        # Base switch timing
        self.base_switch_timing = None


    def __get_variable(self, raw : str) -> tuple:
        df = pd.DataFrame()
        
        vlist = re.findall('#.+\(.+?\)',raw)

        for raw_line in vlist:
            li = re.sub('\s','',raw_line)
            char = re.search('#.+?\(',li, flags=re.IGNORECASE).group()
            char = re.sub('#|\(','',char)
            if not df.empty and char in df.index.tolist():
                continue
            dic = {'def': None, 'main': None, 'sub': None, 'element':None,'fix': False ,'upper': None, 'lower': None ,'shunt': None,'dp': True,'dpv': None}
            
            m = re.search('\(.+?\)',li).group()
            m = re.sub('\(|\)','',m)
            spl = re.split(',',m)
            if len(spl)==1:
                if isfloat(spl[0]) or isint(spl[0]):
                    num = stringToNum(spl[0])
                    dic['def'] = num
                    dic['main'] = num
                    dic['sub'] = num
            for sp in spl:
                val = re.split('=',sp)
                if len(val) == 1:
                    if isfloat(val[0]) or isint(val[0]):
                        num = stringToNum(spl[0])
                        dic['def'] = num
                        dic['main'] = num
                        dic['sub'] = num
                elif len(val) == 2:
                    if re.fullmatch('v|value',val[0],flags=re.IGNORECASE):
                        num = stringToNum(val[1])
                        dic['def'] = num
                        dic['main'] = num
                        dic['sub'] = num
                    elif re.fullmatch('fix|fixed',val[0],flags=re.IGNORECASE):
                        if re.fullmatch('true',val[1],flags=re.IGNORECASE):
                            dic['fix'] = True
                    elif re.fullmatch('shunt',val[0],flags=re.IGNORECASE):
                        dic['shunt'] = val[1]
                    elif re.fullmatch('dp',val[0],flags=re.IGNORECASE):
                        if re.fullmatch('false',val[1],flags=re.IGNORECASE):
                            dic['dp'] = False
                    elif re.fullmatch('dpv',val[0],flags=re.IGNORECASE):
                        num = stringToNum(val[1])
                        dic['dpv'] = num
                    elif re.fullmatch('upper',val[0],flags=re.IGNORECASE):
                        num = stringToNum(val[1])
                        dic['upper'] = num
                    elif re.fullmatch('lower',val[0],flags=re.IGNORECASE):
                        num = stringToNum(val[1])
                        dic['lower'] = num
                    else:
                        raise ValueError("[ "+sp+" ]の記述が読み取れません。")
                else:
                    raise ValueError("[ "+sp+" ]の記述が読み取れません。")

            for line in raw.splitlines():
                if raw_line in line:
                    if re.fullmatch('R',line[0:1],flags=re.IGNORECASE):
                        dic['element'] = 'R'
                        if dic['dpv'] == None:
                            dic['dpv'] = 7
                    elif re.fullmatch('L',line[0:1],flags=re.IGNORECASE):
                        dic['element'] = 'L'
                        if dic['dpv'] == None:
                            dic['dpv'] = 7
                    elif re.fullmatch('C',line[0:1],flags=re.IGNORECASE):
                        dic['element'] = 'C'
                        if dic['dpv'] == None:
                            dic['dpv'] = 7
                    elif re.fullmatch('V',line[0:1],flags=re.IGNORECASE):
                        dic['element'] = 'V'
                        if dic['dpv'] == None:
                            dic['dpv'] = 7
                    elif re.fullmatch('B',line[0:1],flags=re.IGNORECASE):
                        dic['element'] = 'B'
                        if dic['dpv'] == None:
                            dic['dpv'] = 7
                    else:
                        dic['element'] = None
                        if dic['dpv'] == None:
                            dic['dpv'] = 7
                    break
            
            dic_df = pd.DataFrame.from_dict({ char : dic }, orient = "index")
            df = pd.concat([df, dic_df])

        for v in re.findall('#.+\(.+?\)',raw):
            ch = re.search('#.+?\(',v).group()
            ch = re.sub('#|\(','',ch)
            ch = "#("+ch+")"
            raw = raw.replace(v, ch)

        return df , raw

    def __create_netlist(self, netlist, conf : Config) -> str:
        # raw のリセット
        raw = ""
        # .print .endの行を取得
        for line in netlist.splitlines():
            
            print_obj = re.search('\.print',line, flags=re.IGNORECASE)
            end_obj = re.search('\.end$',line, flags=re.IGNORECASE)
            if not print_obj and not end_obj:
                raw = raw + line + "\n"

        if not conf.phase_ele==[]:
            for ll in conf.phase_ele:
                for l in ll:
                    raw = raw + ".print phase " + l + "\n"

        if not conf.voltage_ele==[]:
            for l in conf.voltage_ele:
                raw = raw + ".print devv " + l + "\n"

        raw = raw + ".end"
        return raw

    def data_simulation(self,  plot = True):
        copied_sim_data = self.raw_sim_data
        parameters : pd.Series =  self.vdf['def']
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))
        df = simulation(copied_sim_data)
        if plot:
            sim_plot(df)
        return df

    def get_base_switch_timing(self,  plot = True):
        print("Simulate with default values.")

        df = self.__data_sim(self.vdf['def'])
        if plot:
            sim_plot(df)
        self.base_switch_timing = get_switch_timing(self.conf, df, plot)
        return self.base_switch_timing

    def __data_sim(self, parameters : pd.Series) -> pd.DataFrame:
        copied_sim_data = self.sim_data
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

        df = simulation(copied_sim_data)
        return df

    def __operation_judge(self, parameters : pd.Series):
        #if not comfirm_pre_switch(self.conf, self.__data_sim(parameters)):
        #    return False
        res = get_switch_timing(self.conf, self.__data_sim(parameters))
        if self.conf.state_judge==False:
            return compare_switch_timings(res, self.base_switch_timing, self.conf)
        else:
            return state_judgement(res, self.conf)


    def custom_simulation(self, res_df : pd.DataFrame):
        param = copy.deepcopy(self.vdf['def'])
        res_df['margin'] = 0

        for num, srs in tqdm(res_df.iterrows(), total=len(res_df)):

            # 値の書き換え
            for colum, value in srs.items():
                if not colum == 'param':
                    param[colum] = value

            res_df.at[num,'margin'] = self.get_critical_margin(param = param)[1]
        return res_df

    def get_critical_margin(self, param : pd.Series = pd.Series(dtype='float64')) -> tuple:
        margins = self.get_margins(param = param, plot=False)
        
        min_margin = 100
        min_ele = None
        for element in margins.index:
            if not self.vdf.at[element,'fix']:
                # 最小マージンの素子を探す。
                if abs(margins.at[element,'low(%)']) < min_margin or abs(margins.at[element,'high(%)']) < min_margin:
                    min_margin = vaild_number(min(abs(margins.at[element,'low(%)']), abs(margins.at[element,'high(%)'])), 4)
                    min_ele = element
        
        return (min_ele, min_margin)

    # Use parameters of vdf['sub']
    def get_margins(self, param : pd.Series = pd.Series(dtype='float64'), plot : bool = True, accuracy : int = 8, thread : int = 16) -> pd.DataFrame:
        if self.base_switch_timing == None:
            print("\033[31mFirst, you must get the base switch timing.\nPlease use 'get_base_switch_timing()' method before getting the margin.\033[0m")
            sys.exit()
        
        # print(param)
        if param.empty:
            print("Using default parameters")
            param = self.vdf['def']

        margin_columns_list = ['low(value)', 'low(%)', 'high(value)', 'high(%)']

        # result を受け取る dataframe
        margin_result = pd.DataFrame(columns = margin_columns_list)

        # 0%の値は動くか確認
        if not self.__operation_judge(param):
            for index in self.vdf.index:
                margin_result.loc[index] = 0

        else:
            futures = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
                for index in self.vdf.index:
                    future = executor.submit(self.__get_margin, param, index, accuracy)
                    futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                # 結果を受け取り
                result_dic= future.result()
                # variables dataframeに追加
                margin_result.loc[result_dic["index"]] = result_dic["result"]

        # plot     
        if plot:
            margin_plot(margin_result)

        return margin_result


    def __get_margin(self, srs : pd.Series, target_ele : str, accuracy : int = 7):

        # deepcopy　をする
        parameters : pd.Series = copy.deepcopy(srs)

        # デフォルト値の抽出
        default_v = parameters[target_ele]

        # lower ----------------- 
        high_v = default_v
        low_v = 0
        target_v = (high_v + low_v)/2

        for i in range(accuracy):
            parameters[target_ele] = target_v
            if self.__operation_judge(parameters):
                high_v = target_v
                target_v = (high_v + low_v)/2
            else:
                low_v = target_v
                target_v = (high_v + low_v)/2

        lower_margin = high_v
        lower_margin_rate = (lower_margin - default_v) * 100 / default_v
        # -----------------

        # upper -----------------
        high_v = 0
        low_v = default_v
        target_v = default_v * 2

        for i in range(accuracy):

            parameters[target_ele] = target_v
            if self.__operation_judge(parameters):
                if high_v == 0:
                    low_v = target_v
                    break
                low_v = target_v
                target_v = (high_v + low_v)/2
            else:
                high_v = target_v
                target_v = (high_v + low_v)/2

        upper_margin = low_v
        upper_margin_rate = (upper_margin - default_v) * 100 / default_v
        # -----------------

        # deepcopy　したものを削除
        del parameters

        return {"index" : target_ele, "result" : (lower_margin, lower_margin_rate, upper_margin, upper_margin_rate)}


    
    def optimize(self, directory : str, l1c=10, l2c=40):

        # ------------------------------ #
        # 変数
        # ------------------------------ #
        diff_margin_parcentage = 0.2
        loop1_count = l1c
        loop2_count = l2c



        # directory の処理
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.mkdir(directory)

        
        first_min_margin = 0 # loop 1 のマージン

        
        for k in range(loop1_count):

            # -------- loop 1 --------

            second_min_margin = 0     # loop 2 のマージン
            margins_for_plot = None   # 保存するためのマージン保管場所
            main_parameters = None     # 最適解のパラメータ

            
            for j in range(loop2_count):

                # -------- loop 2 --------

                self.vdf['sub'] = self.vdf['main'] 
                self.shunt_apply()
                # 最初の一回はそのままのマージンを計算
                if j > 0:
                    self.variation()
                
                pre_min_ele = None    # ひとつ前の最小マージンを取るindex
                for i in range(10):
                    print(str(k)+":"+str(j)+":"+str(i)+"の最適化")
                    # マージンの計算
                    margins = self.get_margins(param=self.vdf['sub'],plot=False)

                    min_margin = 100
                    
                    min_ele = None
                    for element in margins.index:
                        if not self.vdf.at[element,'fix']:
                            # 最小マージンの素子を探す。
                            if abs(margins.at[element,'low(%)']) < min_margin or abs(margins.at[element,'high(%)']) < min_margin:
                                min_margin = vaild_number(min(abs(margins.at[element,'low(%)']), abs(margins.at[element,'high(%)'])), 4)
                                min_ele = element
                    
                    if 'BIAS' in margins.index:
                        bias_margin =  vaild_number(min(abs(margins.at['BIAS','low(%)']), abs(margins.at['BIAS','high(%)'])), 4)
                        print("バイアスマージン : ",bias_margin)

                    print("最小マージン : ", min_ele, "  ", min_margin)

                    #　logへのマージンの書き込み
                    with open(directory+"/log.txt", 'a') as f:
                        f.write(str(k)+":"+str(j)+":"+str(i)+"の最小マージン : "+ str(min_ele)+ "  "+ str(min_margin)+'\n') 

                    
                    if min_margin > second_min_margin:
                        print("最適値の更新"+str(k)+":"+str(j)+":"+str(i)+"の最適化  ", min_margin, "%")
                        margins_for_plot = margins
                        second_min_margin = min_margin
                        main_parameters = copy.copy(self.vdf['sub'])

                    else:
                        if min_margin + diff_margin_parcentage > second_min_margin:
                            self.vdf['sub'].to_csv(directory+"/"+str(k)+"-"+str(j)+"-"+str(i)+"-sub.csv")

    
                    # -------------------------- #
                    # ループ2 終了条件
                    # 1. 最小マージンが0
                    # 2. 同じものが最適化対象になる
                    # -------------------------- #                  
                    if min_margin == 0:     # 最小マージンが0
                        break

                    if pre_min_ele == min_ele:      # 同じものが最適化対象
                        break
                    pre_min_ele = min_ele



                    # 最大マージンと最小マージンの中間点を次の最適化対象にする。最小値最大値を考慮
                    shifted_value = ( margins.at[min_ele,'low(value)'] + margins.at[min_ele,'high(value)'] )/2
                    lower_limit = self.vdf.at[min_ele,'lower']
                    upper_limit = self.vdf.at[min_ele,'upper']

                    if lower_limit != None and shifted_value < lower_limit:
                        self.vdf.at[min_ele,'sub'] = lower_limit
                    elif upper_limit != None and shifted_value < upper_limit:
                        self.vdf.at[min_ele,'sub'] = upper_limit
                    else:
                        self.vdf.at[min_ele,'sub'] = shifted_value

                # -------- loop 2 end --------


            # -------------------------- #
            # ループ1 終了条件
            # 1. 最小マージンが改善されない
            # -------------------------- #
            if second_min_margin > first_min_margin:
                print("--- "+str(k)+":x:x"+"の最適化  ", second_min_margin, "% ---")
                first_min_margin = second_min_margin
                self.vdf['main'] = main_parameters
                

                # 保存する
                print("保存")
                # self.__plot(margins_for_plot, directory+"/"+str(k)+"-x.png")
                main_parameters.to_csv(directory+"/"+str(k)+"-main.csv")
                with open(directory+"/"+str(k)+"-netlist.txt","w") as f:
                    copied_sim_data = self.sim_data
                    for index in main_parameters.index:
                        copied_sim_data = copied_sim_data.replace('#('+index+')', '#'+index+'('+ str(vaild_number(main_parameters[index],3))+')')
                    f.write(copied_sim_data)

            else:
                print("最適化終了")
                break


    def shunt_apply(self):
        for index in self.vdf.index:
            if self.vdf.at[index, 'shunt'] != None:
                shunt_index = self.vdf.at[index, 'shunt']
                self.vdf.at[shunt_index, 'sub'] = shunt_calc(area=self.vdf.at[index, 'sub']) 


    def variation(self):
        for index in self.vdf.index:
            if self.vdf.at[index,'dp']:
                tmp = self.vdf.at[index,'sub']
                dpv = self.vdf.at[index,'dpv']
                up = self.vdf.at[index,'upper']
                lo = self.vdf.at[index,'lower']
                self.vdf.at[index,'sub'] = rand_norm(tmp, abs(tmp*dpv/200), up, lo)
