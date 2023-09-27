from cmath import nan
import re
import pandas as pd
from .util import stringToNum, isfloat, isint, vaild_number
from .pyjosim import simulation, simulation_from_rebuilt, simulation_from_rebuilt_NoSeed
from .judge import get_switch_timing, get_dc_edge_timing, compare_switch_timings, compare_switch_timings_with_dc_judge, compare_switch_timings_detials, get_propagation_switch_defference, get_propagation_switch_defference_with_delay, get_switch_difference_time
from .config import Config
from .calculator import shunt_calc, rand_norm
from .graph import margin_plot, sim_plot
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures
import copy
import os
import sys
import shutil
from tqdm import tqdm
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

class Data:
    def __init__(self, raw_data : str, config : dict):

        #self.sim_data_for_custom
        
        # get variable
        self.vdf, self.raw_sim_data = self.__get_variable(raw=raw_data)

        # check config file
        self.conf : Config = Config(config)

        # create netlist
        self.sim_data = self.__create_netlist(self.raw_sim_data, self.conf)

        # create netlist add .temp 4.2(default)
        #self.sim_data_with_noise = self.__create_netlist_noise(self.sim_data, self.conf)

        # Base switch timing
        self.base_switch_timing = None

        # Base DC switch timing
        self.base_dc_switch_timing = None

    def set_base_switch_timing(self, switch_timing):
        self.base_switch_timing = switch_timing

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

    def __create_netlist_noise(self, netlist, conf : Config, Temp : int=4.2) -> str:
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

        raw = raw + ".temp "+str(Temp)+"\n"
        raw = raw + ".end"
        return raw

    def __create_raw_netlist_noise(self, raw_netlist, conf : Config, Temp : int=4.2) -> str:
        # raw のリセット
        raw = ""
        # .print .endの行を取得
        for line in raw_netlist.splitlines():
            
            #print_obj = re.search('\.print',line, flags=re.IGNORECASE)
            end_obj = re.search('\.end$',line, flags=re.IGNORECASE)
            if not end_obj:
                raw = raw + line + "\n"

        raw = raw + ".temp "+str(Temp)+"\n"
        raw = raw + ".end"
        return raw

    def data_simulation(self,  plot = True):
        copied_sim_data = self.raw_sim_data

        if not self.vdf.empty:
            parameters : pd.Series =  self.vdf['def']
            for index in parameters.index:
                copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))
                
        df = simulation(copied_sim_data)
        if plot:
            sim_plot(df)
        return df

    def data_simulation_with_noise(self,  plot = True, Temp : int=4.2):
        self.sim_data_with_noise = self.__create_netlist_noise(self.sim_data, self.conf, Temp)
        copied_sim_data = self.sim_data_with_noise

        #if not self.vdf.empty:
        parameters : pd.Series =  self.vdf['def']
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))
                
        df = simulation(copied_sim_data)
        if plot:
            sim_plot(df)
        return df

    def data_raw_simulation_with_noise(self,  plot = True, Temp : int=4.2):
        self.sim_data_with_noise = self.__create_raw_netlist_noise(self.raw_sim_data, self.conf, Temp)
        copied_sim_data = self.sim_data_with_noise

        if not self.vdf.empty:
            parameters : pd.Series =  self.vdf['def']
            for index in parameters.index:
                copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))
                
        df = simulation(copied_sim_data)
        if plot:
            sim_plot(df)
        return df

    def data_simulation_with_noise_seed(self,  plot = True, Temp : int=4.2, Seed : int=0):
        self.sim_data_with_noise = self.__create_netlist_noise(self.sim_data, self.conf, Temp)
        copied_sim_data = self.sim_data_with_noise

        #if not self.vdf.empty:
        parameters : pd.Series =  self.vdf['def']
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

        #print(copied_sim_data)
                
        df = simulation_from_rebuilt(copied_sim_data, Seed)
        if plot:
            sim_plot(df)
        return df

    def data_simulation_with_noise_noseed(self,  plot = True, Temp : int=4.2):
            self.sim_data_with_noise = self.__create_netlist_noise(self.sim_data, self.conf, Temp)
            copied_sim_data = self.sim_data_with_noise

            #if not self.vdf.empty:
            parameters : pd.Series =  self.vdf['def']
            for index in parameters.index:
                copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

            #print(copied_sim_data)
                    
            df = simulation_from_rebuilt_NoSeed(copied_sim_data)
            if plot:
                sim_plot(df)
            return df

    def data_raw_simulation_with_noise_seed(self,  plot = True, Temp : int=4.2, Seed : int=0):
        self.sim_data_with_noise = self.__create_raw_netlist_noise(self.raw_sim_data, self.conf, Temp)
        copied_sim_data = self.sim_data_with_noise

        #if not self.vdf.empty:
        parameters : pd.Series =  self.vdf['def']
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

        #print(copied_sim_data)
                
        df = simulation_from_rebuilt(copied_sim_data, Seed)
        if plot:
            sim_plot(df)
        return df

    def get_base_switch_timing(self,  plot = True, timescale = "ps", blackstyle = False):
        print("Simulate with default values.")

        df = self.__data_sim(self.vdf['def'])
        if plot:
            sim_plot(df, timescale, blackstyle)
        self.base_switch_timing = get_switch_timing(self.conf, df, plot, timescale, blackstyle)
        if self.conf.dc_judge:
            self.base_dc_switch_timing = get_dc_edge_timing(self.conf, df, False, timescale, blackstyle)
        return self.base_switch_timing

    def public_sim(self, parameters : pd.Series) -> pd.DataFrame:
        copied_sim_data = self.sim_data
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))
        df = simulation(copied_sim_data)
        return df

    def __data_sim(self, parameters : pd.Series) -> pd.DataFrame:
        copied_sim_data = self.sim_data
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

        #self.sim_data_for_custom=copied_sim_data

        df = simulation(copied_sim_data)
        return df

    def __data_sim_with_noise(self, parameters : pd.Series, Temp : int) -> pd.DataFrame:
        if parameters.empty:
            parameters : pd.Series =  self.vdf['def']
        self.sim_data_with_noise = self.__create_netlist_noise(self.sim_data, self.conf, Temp)
        copied_sim_data = self.sim_data_with_noise
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

        df = simulation(copied_sim_data)
        return df

    def __data_sim_with_noise_noseed(self, parameters : pd.Series, Temp : int) -> pd.DataFrame:
        self.sim_data_with_noise = self.__create_netlist_noise(self.sim_data, self.conf, Temp)
        copied_sim_data = self.sim_data_with_noise
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

        df = simulation_from_rebuilt_NoSeed(copied_sim_data)
        return df

    def __data_sim_with_noise_by_myseed(self, parameters : pd.Series, Temp : int, myseed : int) -> pd.DataFrame:
        self.sim_data_with_noise = self.__create_netlist_noise(self.sim_data, self.conf, Temp)
        copied_sim_data = self.sim_data_with_noise
        for index in parameters.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameters[index]))

        #print(copied_sim_data)
        
        df = simulation_from_rebuilt(copied_sim_data, myseed)
        return df

    def only_output_custom_netlist(self, res_df : pd.DataFrame, path : str) -> bool:
        param = copy.deepcopy(self.vdf['def'])
        res_df['margin'] = 0
        #copied_sim_data = self.sim_data

        for num, srs in tqdm(res_df.iterrows(), total=len(res_df)):
            copied_sim_data = self.sim_data

            # 値の書き換え
            for colum, value in srs.items():
                if not colum == 'param':
                    param[colum] = value
            # create netlist
            for index in param.index:
                copied_sim_data = copied_sim_data.replace('#('+index+')', '#'+index+'('+str(param[index])+')')

            #return copied_sim_data
            with open(path+"/netlist"+str(num)+".inp","w") as o:
                print(copied_sim_data, file=o)

            #res_df.at[num,'margin'] = self.get_critical_margin(param = param)[1]
        return True
    
    def only_output_custom_raw_netlist(self, res_df : pd.DataFrame, path : str) -> bool:
        param = copy.deepcopy(self.vdf['def'])
        res_df['margin'] = 0
        #copied_sim_data = self.sim_data

        for num, srs in tqdm(res_df.iterrows(), total=len(res_df)):
            copied_sim_data = self.raw_sim_data

            # 値の書き換え
            for colum, value in srs.items():
                if not colum == 'param':
                    param[colum] = value
            # create netlist
            for index in param.index:
                copied_sim_data = copied_sim_data.replace('#('+index+')', '#'+index+'('+str(param[index])+')')

            #return copied_sim_data
            with open(path+"/netlist"+str(num)+".inp","w") as o:
                print(copied_sim_data, file=o)

            #res_df.at[num,'margin'] = self.get_critical_margin(param = param)[1]
        return True
    
    def only_output_list_custom_netlist(self, res_df : pd.DataFrame) -> list:
        output=list()
        param = copy.deepcopy(self.vdf['def'])
        res_df['margin'] = 0
        #copied_sim_data = self.sim_data

        for num, srs in tqdm(res_df.iterrows(), total=len(res_df)):
            copied_sim_data = self.sim_data

            # 値の書き換え
            for colum, value in srs.items():
                if not colum == 'param':
                    param[colum] = value
            # create netlist
            for index in param.index:
                copied_sim_data = copied_sim_data.replace('#('+index+')', '#'+index+'('+str(param[index])+')')
            
            output.append(copied_sim_data)
            #return copied_sim_data
            #with open(path+"/netlist"+str(num)+".inp","w") as o:
            #    print(copied_sim_data, file=o)

            #res_df.at[num,'margin'] = self.get_critical_margin(param = param)[1]
        return output
    
    def only_output_list_custom_raw_netlist(self, res_df : pd.DataFrame) -> list:
        output=list()
        param = copy.deepcopy(self.vdf['def'])
        res_df['margin'] = 0
        #copied_sim_data = self.sim_data

        for num, srs in tqdm(res_df.iterrows(), total=len(res_df)):
            copied_sim_data = self.raw_sim_data

            # 値の書き換え
            for colum, value in srs.items():
                if not colum == 'param':
                    param[colum] = value
            # create netlist
            for index in param.index:
                copied_sim_data = copied_sim_data.replace('#('+index+')', '#'+index+'('+str(param[index])+')')
            
            output.append(copied_sim_data)
            #return copied_sim_data
            #with open(path+"/netlist"+str(num)+".inp","w") as o:
            #    print(copied_sim_data, file=o)

            #res_df.at[num,'margin'] = self.get_critical_margin(param = param)[1]
        return output


    def only_operation_judge(self, parameters : pd.Series = pd.Series(dtype='float64')):
        """ if param.empty:
            print("Using default parameters")
            param = self.sim_data_with_noise
        res = get_switch_timing(self.conf, self.__data_sim(param))
        return compare_switch_timings(res, self.base_switch_timing, self.conf) """
        res = get_switch_timing(self.conf, self.__data_sim(parameters))
        return compare_switch_timings(res, self.base_switch_timing, self.conf)


    def only_operation_judge_with_noise(self, parameters : pd.Series = pd.Series(dtype='float64'), Temp : int=4.2)-> bool:
        result = self.__data_sim_with_noise(parameters, Temp)
        res = get_switch_timing(self.conf, result)
        #res = get_switch_timing(self.conf, self.__data_sim_with_noise(parameters, Temp))
        if self.conf.dc_judge:
            dc_res=get_dc_edge_timing(self.conf, result)
            return compare_switch_timings_with_dc_judge(res, self.base_switch_timing, dc_res, self.base_dc_switch_timing, self.conf)
        return compare_switch_timings(res, self.base_switch_timing, self.conf)

    def only_operation_judge_with_noise_noseed(self, parameters : pd.Series = pd.Series(dtype='float64'), Temp : int=4.2)-> bool:
        result = self.__data_sim_with_noise_noseed(parameters, Temp)
        res = get_switch_timing(self.conf, result)
        #res = get_switch_timing(self.conf, self.__data_sim_with_noise_noseed(parameters, Temp))
        if self.conf.dc_judge:
            dc_res=get_dc_edge_timing(self.conf, result)
            return compare_switch_timings_with_dc_judge(res, self.base_switch_timing, dc_res, self.base_dc_switch_timing, self.conf)
        return compare_switch_timings(res, self.base_switch_timing, self.conf)

    def only_operation_judge_with_noise_by_myseed(self, myseed : int, parameters : pd.Series = pd.Series(dtype='float64'), Temp : int=4.2)-> bool:
        res = get_switch_timing(self.conf, self.__data_sim_with_noise_by_myseed(parameters, Temp, myseed), plot=True)
        return compare_switch_timings(res, self.base_switch_timing, self.conf)

    def __only_operation_judge_with_noise_by_myseed(self, myseed : int, parameters : pd.Series = pd.Series(dtype='float64'), Temp : int=4.2)-> bool:
        res = get_switch_timing(self.conf, self.__data_sim_with_noise_by_myseed(parameters, Temp, myseed), plot=False)
        return compare_switch_timings(res, self.base_switch_timing, self.conf)

    def only_operation_judge_with_noise_by_myseeds(self, myseeds : list, parameters : pd.Series = pd.Series(dtype='float64'), Temp : int=4.2)-> list:
        for imyseed in myseeds:
            result = self.__data_sim_with_noise_by_myseed(parameters, Temp, imyseed['num'])
            res = get_switch_timing(self.conf, result, plot=False)
            if self.conf.dc_judge:
                dc_res=get_dc_edge_timing(self.conf, result)
                judge_result = compare_switch_timings_with_dc_judge(res, self.base_switch_timing, dc_res, self.base_dc_switch_timing, self.conf)
            else:
                judge_result = compare_switch_timings(res, self.base_switch_timing, self.conf)
            imyseed['result']=judge_result
        return myseeds

    # myseeds is a list of dict
    def only_operation_judge_with_noise_by_myseed_async(self, myseedss : list, parameters : pd.Series = pd.Series(dtype='float64'), Temp : int=4.2)-> list:

        # def check(num):
        #     print(num)
        #     return num

        if self.base_switch_timing == None:
            print("\033[31mFirst, you must get the base switch timing.\nPlease use 'get_base_switch_timing()' method before getting the margin.\033[0m")
            sys.exit()

        param = copy.deepcopy(parameters)

        print("Temp="+str(Temp))

        # tqdmで経過が知りたい時
        new_myseeds=[]
        with tqdm(total=len(myseedss)) as progress:
            futures = []
            with concurrent.futures.ProcessPoolExecutor(max_workers=32) as executor:
                
                for imyseeds in myseedss:
                    future = executor.submit(self.only_operation_judge_with_noise_by_myseeds, imyseeds, param, Temp)
                    #future = executor.submit(check, imyseed['num'])
                    future.add_done_callback(lambda p: progress.update()) # tqdmで経過が知りたい時
                    futures.append(future)
                    #result=future.result()
            
            for ifu in futures:
                result=ifu.result()
                if new_myseeds==[]:
                    new_myseeds=result
                else:
                    new_myseeds.extend(result)
                # #for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                # temp_d=dict()
                # result=future.result()
                # #print(result)
                # temp_d['num']=imyseeds['num']
                # temp_d['result']=result
                # new_myseeds.append(temp_d)
                # #imyseed['result']=result
    
        return new_myseeds

    def only_operation_judge_with_noise_details(self, parameters : pd.Series = pd.Series(dtype='float64'), Temp : int=4.2)-> str:
        res = get_switch_timing(self.conf, self.__data_sim_with_noise(parameters, Temp))
        return compare_switch_timings_detials(res, self.base_switch_timing, self.conf)

    def __operation_judge(self, parameters : pd.Series):
        result = self.__data_sim(parameters)
        res = get_switch_timing(self.conf, result)
        if self.conf.dc_judge:
            dc_res=get_dc_edge_timing(self.conf, result)
            return compare_switch_timings_with_dc_judge(res, self.base_switch_timing, dc_res, self.base_dc_switch_timing, self.conf)
        return compare_switch_timings(res, self.base_switch_timing, self.conf)

    def __operation_judge_2(self, parameters : pd.Series, num : int):
        res = get_switch_timing(self.conf, self.__data_sim(parameters))
        return (compare_switch_timings(res, self.base_switch_timing, self.conf),num)

    def only_get_propagation_time_defference(self, start_ele : str, end_ele : str, pulse_num : int, params_raw_num : int, param : pd.Series = pd.Series(dtype='float64'))-> float:
        # print(param)
        result=float()
        if param.empty:
            print("Using default parameters")
            param = self.vdf['def']
            print('<<<<<<<<param>>>>>>>>')
            print(param)
        res = get_switch_timing(self.conf, self.__data_sim(param))
        try:
            result=get_propagation_switch_defference(res, start_ele, end_ele, pulse_num)
        except ValueError:
            print('params_raw_num='+str(params_raw_num))
            sys.exit()
        finally:
            return result
        
    def only_get_propagation_time_defference_with_delay(self, start_ele : str, end_ele : str, pulse_num : int, params_raw_num : int, param : pd.Series = pd.Series(dtype='float64'))-> dict:
        # print(param)
        result=dict()
        if param.empty:
            print("Using default parameters")
            param = self.vdf['def']
            print('<<<<<<<<param>>>>>>>>')
            print(param)
        res = get_switch_timing(self.conf, self.__data_sim(param))
        try:
            result=get_propagation_switch_defference_with_delay(res, start_ele, end_ele, pulse_num)
        except ValueError:
            print('params_raw_num='+str(params_raw_num))
            sys.exit()
        finally:
            return result

    def __get_propagation_time_defference(self, start_ele : str, end_ele : str, num : int, param : pd.Series = pd.Series(dtype='float64'))-> float:
        # print(param)
        if param.empty:
            print("Using default parameters")
            param = self.vdf['def']
            #print('<<<<<<<<param>>>>>>>>')
            #print(param)
        res = get_switch_timing(self.conf, self.__data_sim(param))
        return get_propagation_switch_defference(res, start_ele, end_ele, num)


    def custom_opera_judge(self, res_df : pd.DataFrame):
        param = copy.deepcopy(self.vdf['def'])
        
        # tqdmで経過が知りたい時
        with tqdm(total=len(res_df)) as progress:
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
               
                for num, srs in res_df.iterrows():
                    # 値の書き換え
                    for colum, value in srs.items():
                        if not colum == 'param':
                            param[colum] = value

                    inp = copy.deepcopy(param)
                    future = executor.submit(self.__operation_judge_2, inp, num)
                    future.add_done_callback(lambda p: progress.update()) # tqdmで経過が知りたい時
                    futures.append(future)

            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                res : tuple = future.result()
                res_df.at[res[1],'opera'] = res[0]
        return res_df

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
    
    def custom_simulation_async(self, res_df : pd.DataFrame):
        param = copy.deepcopy(self.vdf['def'])
        
        # tqdmで経過が知りたい時
        with tqdm(total=len(res_df)) as progress:
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
               
                for num, srs in res_df.iterrows():
                    # 値の書き換え
                    for colum, value in srs.items():
                        if not colum == 'param':
                            param[colum] = value

                    inp = copy.deepcopy(param)
                    future = executor.submit(self.get_critical_margin_sync, num, inp)
                    future.add_done_callback(lambda p: progress.update()) # tqdmで経過が知りたい時
                    futures.append(future)

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            res : tuple = future.result()
            res_df.at[res[0],'min_ele'] = res[1]
            res_df.at[res[0],'min_margin'] = res[2]

        return res_df

    def custom_simulation_with_bias_margin_async(self, res_df : pd.DataFrame):
        param = copy.deepcopy(self.vdf['def'])
        
        # tqdmで経過が知りたい時
        with tqdm(total=len(res_df)) as progress:
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
               
                for num, srs in res_df.iterrows():
                    # 値の書き換え
                    for colum, value in srs.items():
                        if not colum == 'param':
                            param[colum] = value

                    inp = copy.deepcopy(param)
                    future = executor.submit(self.get_critical_margin_sync_with_bias_margin, num, inp)
                    future.add_done_callback(lambda p: progress.update()) # tqdmで経過が知りたい時
                    futures.append(future)

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            res : tuple = future.result()
            res_df.at[res[0],'min_ele'] = res[1]
            res_df.at[res[0],'min_margin'] = res[2]
            res_df.at[res[0],'bias_margin+'] = res[3]
            res_df.at[res[0],'bias_margin-'] = res[4]

        return res_df

    def custom_get_propagation_time_defferences_async(self, start_ele : str, end_ele : str, pulse_num : int, res_df : pd.DataFrame):
        if self.base_switch_timing == None:
            print("\033[31mFirst, you must get the base switch timing.\nPlease use 'get_base_switch_timing()' method before getting the margin.\033[0m")
            sys.exit()

        param = copy.deepcopy(self.vdf['def'])
        res_df['Ave_delay_defference']=0

        # tqdmで経過が知りたい時
        with tqdm(total=len(res_df)) as progress:
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
               
                for num, srs in res_df.iterrows():
                    # 値の書き換え
                    for colum, value in srs.items():
                        if not colum == 'param':
                            param[colum] = value

                    res = copy.deepcopy(param)
                    future = executor.submit(self.only_get_propagation_time_defference, start_ele, end_ele, pulse_num, num, res)
                    future.add_done_callback(lambda p: progress.update()) # tqdmで経過が知りたい時
                    futures.append(future)

                    for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                        result=future.result()
                        print(result)
                        res_df.at[num, 'Ave_delay_defference'] = result
    
        return res_df
    
    def custom_get_propagation_time_defferences_with_all_delay_async(self, start_ele : str, end_ele : str, pulse_num : int, res_df : pd.DataFrame):
        if self.base_switch_timing == None:
            print("\033[31mFirst, you must get the base switch timing.\nPlease use 'get_base_switch_timing()' method before getting the margin.\033[0m")
            sys.exit()

        param = copy.deepcopy(self.vdf['def'])
        res_df['Ave_delay_defference']=0

        # tqdmで経過が知りたい時
        with tqdm(total=len(res_df)) as progress:
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
               
                for num, srs in res_df.iterrows():
                    # 値の書き換え
                    for colum, value in srs.items():
                        if not colum == 'param':
                            param[colum] = value

                    res = copy.deepcopy(param)
                    future = executor.submit(self.only_get_propagation_time_defference_with_delay, start_ele, end_ele, pulse_num, num, res)
                    future.add_done_callback(lambda p: progress.update()) # tqdmで経過が知りたい時
                    futures.append(future)

                    for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                        result=future.result()
                        print(result)
                        res_df.at[num, 'Ave_delay_defference'] = result['switch_defference']
                        res_df.at[num, 'even_delay'] = result['even_delay']
                        res_df.at[num, 'odd_delay'] = result['odd_delay']
    
        return res_df

    #num_of_clkとnum_of_inoutは何番目のパルスを比較するのか指定する
    def get_setup_hold_time(self, input_pwl : str, clk_element : str, num_of_clk : list, input_element : str, num_of_input : list, output_element : str, num_of_output : list, initial_time_of_data : int, shift_renge=1, shift_interval=0.1, param : pd.Series = pd.Series(dtype='float64')):
        output_dict=dict()

        #時間の単位はps
        def rewrite_pwl(netlist : str, element_name : str, start_time : float , period : float, num : int, dc_or_pulse='pulse') -> dict:
            output_dict=dict()
            temp_str=str()
            temp_list=re.findall(element_name+'.+\s\d\s.+', netlist)
            first_str_list=re.split('\(',temp_list[0])
            first = "(0ps 0mv "
            tab = " "
            ps = "ps"
            mv = "mv "
            end = ")"
            if dc_or_pulse=='pulse':
                temp_str=first_str_list[0]+first
                for i in range(num):
                    temp_str=temp_str+(str(Decimal(str(start_time + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "0" + mv)
                    temp_str=temp_str+(str(Decimal(str(start_time + 1.0 + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "1.035" + mv)
                    temp_str=temp_str+(str(Decimal(str(start_time + 2.0 + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "1.035" + mv)
                    temp_str=temp_str+(str(Decimal(str(start_time + 3.0 + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "0" + mv)
                temp_str+=end
            #print(temp_str)
            output_dict['input_pwl']=temp_str
            output_dict['netlist']=re.sub(element_name+'.+\s\d\s.+', temp_str, netlist)
            #print(output_str)
            return output_dict
        
        #2つのクロックとその間の入力による出力の時間差を得る
        #def get_output_timing(clk_element, num_of_clk, output_element, num_of_output) -> list:
        #    if param.empty:
        #        print("Using default parameters")
        #        param = self.vdf['def']
        #    res = get_switch_timing(self.conf, self.__data_sim(param))
        #    return get_switch_difference_time(res, clk_element, [num_of_clk[1]], output_element, num_of_output)

        print("Checking holdtime...")
        self.sim_data=rewrite_pwl(self.sim_data, input_pwl, initial_time_of_data, 200, 1)['netlist']
        if param.empty:
            print("Using default parameters")
            param = self.vdf['def']
        res = get_switch_timing(self.conf, self.__data_sim(param))
        #setup_hold=get_switch_difference_time(res, clk_element, num_of_clk, input_element, num_of_input)
        output_timing=get_switch_difference_time(res, clk_element, [num_of_clk[1]], output_element, num_of_output)
        if output_timing==[] or output_timing[0]['difference_time']<0:
            raise ValueError("Input maybe too late or early.")
        
        temp_initial_time=initial_time_of_data
        temp_holdtime=list()
        temp_dict=dict()
        temp_pwl=str()
        while(True):
            #for i in range((int)(shift_renge/shift_interval)):
            temp_initial_time+=shift_interval
            temp_dict=rewrite_pwl(self.sim_data, input_pwl, temp_initial_time, 200, 1)
            self.sim_data=temp_dict['netlist']
            if param.empty:
                print("Using default parameters")
                param = self.vdf['def']
            res_new = get_switch_timing(self.conf, self.__data_sim(param))
            output_timing=get_switch_difference_time(res_new, clk_element, [num_of_clk[1]], output_element, num_of_output)
            if output_timing==[]:
                #print(self.sim_data)
                print("num of temp_holdtime="+str(len(temp_holdtime)))
                print(temp_pwl)
                break
            temp_holdtime=get_switch_difference_time(res_new, input_element, num_of_input, clk_element, [num_of_clk[1]],)
            temp_pwl=temp_dict['input_pwl']
            #print(temp_holdtime)
        #print("num of temp_holdtime="+str(len(temp_holdtime)))
        output_dict['holdtime']=temp_holdtime[0]['difference_time']


        print("Checking setuptime...")
        self.sim_data=rewrite_pwl(self.sim_data, input_pwl, initial_time_of_data, 200, 1)['netlist']
        if param.empty:
            print("Using default parameters")
            param = self.vdf['def']
        res = get_switch_timing(self.conf, self.__data_sim(param))
        #setup_hold=get_switch_difference_time(res, clk_element, num_of_clk, input_element, num_of_input)
        output_timing=get_switch_difference_time(res, clk_element, [num_of_clk[1]], output_element, num_of_output)
        if output_timing==[] or output_timing[0]['difference_time']<0:
            raise ValueError("Input maybe too late or early.")
        
        temp_initial_time=initial_time_of_data
        temp_setuptime=list()
        while(True):
            #for i in range((int)(shift_renge/shift_interval)):
            temp_initial_time-=shift_interval
            temp_dict=rewrite_pwl(self.sim_data, input_pwl, temp_initial_time, 200, 1)
            self.sim_data=temp_dict['netlist']
            if param.empty:
                print("Using default parameters")
                param = self.vdf['def']
            res_new = get_switch_timing(self.conf, self.__data_sim(param))
            output_timing=get_switch_difference_time(res_new, clk_element, [num_of_clk[1]], output_element, num_of_output)
            if output_timing[0]['difference_time']<0:
                #print(self.sim_data)
                print("num of temp_setuptime="+str(len(temp_setuptime)))
                print(temp_pwl)
                break
            temp_setuptime=get_switch_difference_time(res_new ,clk_element, [num_of_clk[0]], input_element, num_of_input)
            temp_pwl=temp_dict['input_pwl']
            #print(temp_setuptime)
        #print("num of temp_setuptime="+str(len(temp_setuptime)))
        output_dict['setuptime']=temp_setuptime[0]['difference_time']
        
        return output_dict

    #num_of_clkとnum_of_inoutは何番目のパルスを比較するのか指定する
    def get_setup_hold_time_which(self, input_pwl : str, clk_element : str, num_of_clk : list, input_element : str, num_of_input : list, output_element : str, num_of_output : list, initial_time_of_data : int , which : str, shift_renge=1, shift_interval=0.1, param : pd.Series = pd.Series(dtype='float64')):
        output_dict=dict()

        #時間の単位はps
        def rewrite_pwl(netlist : str, element_name : str, start_time : float , period : float, num : int, dc_or_pulse='pulse') -> dict:
            output_dict=dict()
            temp_str=str()
            temp_list=re.findall(element_name+'.+\s\d\s.+', netlist)
            first_str_list=re.split('\(',temp_list[0])
            first = "(0ps 0mv "
            tab = " "
            ps = "ps"
            mv = "mv "
            end = ")"
            if dc_or_pulse=='pulse':
                temp_str=first_str_list[0]+first
                for i in range(num):
                    temp_str=temp_str+(str(Decimal(str(start_time + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "0" + mv)
                    temp_str=temp_str+(str(Decimal(str(start_time + 1.0 + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "1.035" + mv)
                    temp_str=temp_str+(str(Decimal(str(start_time + 2.0 + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "1.035" + mv)
                    temp_str=temp_str+(str(Decimal(str(start_time + 3.0 + period * i)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) + ps + tab + "0" + mv)
                temp_str+=end
            #print(temp_str)
            output_dict['input_pwl']=temp_str
            output_dict['netlist']=re.sub(element_name+'.+\s\d\s.+', temp_str, netlist)
            #print(output_str)
            return output_dict
        
        #2つのクロックとその間の入力による出力の時間差を得る
        #def get_output_timing(clk_element, num_of_clk, output_element, num_of_output) -> list:
        #    if param.empty:
        #        print("Using default parameters")
        #        param = self.vdf['def']
        #    res = get_switch_timing(self.conf, self.__data_sim(param))
        #    return get_switch_difference_time(res, clk_element, [num_of_clk[1]], output_element, num_of_output)

        if which=='hold':
            print("Checking holdtime...")
            self.sim_data=rewrite_pwl(self.sim_data, input_pwl, initial_time_of_data, 200, 1)['netlist']
            if param.empty:
                print("Using default parameters")
                param = self.vdf['def']
            res = get_switch_timing(self.conf, self.__data_sim(param))
            #setup_hold=get_switch_difference_time(res, clk_element, num_of_clk, input_element, num_of_input)
            output_timing=get_switch_difference_time(res, clk_element, [num_of_clk[1]], output_element, num_of_output)
            if output_timing==[] or output_timing[0]['difference_time']<0:
                raise ValueError("Input maybe too late or early.")
        
            temp_initial_time=initial_time_of_data
            temp_holdtime=list()
            temp_dict=dict()
            temp_pwl=str()
            while(True):
                #for i in range((int)(shift_renge/shift_interval)):
                temp_initial_time+=shift_interval
                temp_dict=rewrite_pwl(self.sim_data, input_pwl, temp_initial_time, 200, 1)
                self.sim_data=temp_dict['netlist']
                if param.empty:
                    print("Using default parameters")
                    param = self.vdf['def']
                res_new = get_switch_timing(self.conf, self.__data_sim(param))
                output_timing=get_switch_difference_time(res_new, clk_element, [num_of_clk[1]], output_element, num_of_output)
                if output_timing==[]:
                    #print(self.sim_data)
                    print("num of temp_holdtime="+str(len(temp_holdtime)))
                    print(temp_pwl)
                    break
                temp_holdtime=get_switch_difference_time(res_new, input_element, num_of_input, clk_element, [num_of_clk[1]],)
                temp_pwl=temp_dict['input_pwl']
                #print(temp_holdtime)
            #print("num of temp_holdtime="+str(len(temp_holdtime)))
            output_dict['holdtime']=temp_holdtime[0]['difference_time']


        if which=='setup':
            print("Checking setuptime...")
            self.sim_data=rewrite_pwl(self.sim_data, input_pwl, initial_time_of_data, 200, 1)['netlist']
            if param.empty:
                print("Using default parameters")
                param = self.vdf['def']
            res = get_switch_timing(self.conf, self.__data_sim(param))
            #setup_hold=get_switch_difference_time(res, clk_element, num_of_clk, input_element, num_of_input)
            output_timing=get_switch_difference_time(res, clk_element, [num_of_clk[1]], output_element, num_of_output)
            if output_timing==[] or output_timing[0]['difference_time']<0:
                raise ValueError("Input maybe too late or early.")
        
            temp_initial_time=initial_time_of_data
            temp_setuptime=list()
            while(True):
                #for i in range((int)(shift_renge/shift_interval)):
                temp_initial_time-=shift_interval
                temp_dict=rewrite_pwl(self.sim_data, input_pwl, temp_initial_time, 200, 1)
                self.sim_data=temp_dict['netlist']
                if param.empty:
                    print("Using default parameters")
                    param = self.vdf['def']
                res_new = get_switch_timing(self.conf, self.__data_sim(param))
                output_timing=get_switch_difference_time(res_new, clk_element, [num_of_clk[1]], output_element, num_of_output)
                if output_timing[0]['difference_time']<0:
                    #print(self.sim_data)
                    print("num of temp_setuptime="+str(len(temp_setuptime)))
                    print(temp_pwl)
                    break
                temp_setuptime=get_switch_difference_time(res_new ,clk_element, [num_of_clk[0]], input_element, num_of_input)
                temp_pwl=temp_dict['input_pwl']
                #print(temp_setuptime)
            #print("num of temp_setuptime="+str(len(temp_setuptime)))
            output_dict['setuptime']=temp_setuptime[0]['difference_time']
        
        return output_dict

    def get_critical_margin(self,  param : pd.Series = pd.Series(dtype='float64')) -> tuple:
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

    def get_critical_margin_sync(self,num : int, param : pd.Series = pd.Series(dtype='float64')) -> tuple:
        margins = self.get_margins_sync(param = param, plot=False)
        
        min_margin = 100
        min_ele = None
        for element in margins.index:
            if not self.vdf.at[element,'fix']:
                # 最小マージンの素子を探す。
                if abs(margins.at[element,'low(%)']) < min_margin or abs(margins.at[element,'high(%)']) < min_margin:
                    min_margin = vaild_number(min(abs(margins.at[element,'low(%)']), abs(margins.at[element,'high(%)'])), 4)
                    min_ele = element
        
        return (num, min_ele, min_margin)

    def get_critical_margin_sync_with_bias_margin(self,num : int, param : pd.Series = pd.Series(dtype='float64')) -> tuple:
        margins = self.get_margins_sync(param = param, plot=False)
        
        min_margin = 100
        min_ele = None
        bias_margin_p=0
        bias_margin_m=0
        for element in margins.index:
            if not self.vdf.at[element,'fix']:
                # 最小マージンの素子を探す。
                if abs(margins.at[element,'low(%)']) < min_margin or abs(margins.at[element,'high(%)']) < min_margin:
                    min_margin = vaild_number(min(abs(margins.at[element,'low(%)']), abs(margins.at[element,'high(%)'])), 4)
                    min_ele = element
            if element=='BIAS':
                bias_margin_p=vaild_number(abs(margins.at[element,'high(%)']),4)
                bias_margin_m=vaild_number(abs(margins.at[element,'low(%)']),4)
        
        return (num, min_ele, min_margin, bias_margin_p, bias_margin_m)

    def get_margins_sync(self, param : pd.Series = pd.Series(dtype='float64'), plot : bool = True, blackstyle : bool = False, accuracy : int = 8) -> pd.DataFrame:
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
            for index in self.vdf.index:
                result_dic= self.__get_margin(param, index, accuracy)
                margin_result.loc[result_dic["index"]] = result_dic["result"]

        # plot     
        if plot:
            min_margin = 100
            min_ele = None
            for element in margin_result.index:
                if not self.vdf.at[element,'fix']:
                    # 最小マージンの素子を探す。
                    if abs(margin_result.at[element,'low(%)']) < min_margin or abs(margin_result.at[element,'high(%)']) < min_margin:
                        min_margin = vaild_number(min(abs(margin_result.at[element,'low(%)']), abs(margin_result.at[element,'high(%)'])), 4)
                        min_ele = element

            margin_plot(margin_result, min_ele, blackstyle = blackstyle)

        return margin_result


    def get_margins(self, param : pd.Series = pd.Series(dtype='float64'), plot : bool = True, blackstyle : bool = False, accuracy : int = 8, thread : int = 128) -> pd.DataFrame:
        if self.base_switch_timing == None:
            print("\033[31mFirst, you must get the base switch timing.\nPlease use 'get_base_switch_timing()' method before getting the margin.\033[0m")
            sys.exit()
        
        # print(param)
        if param.empty:
            print("Using default parameters")
            param = self.vdf['def']

        # result を受け取る dataframe
        margin_result = pd.DataFrame(columns = ['low(value)', 'low(%)', 'high(value)', 'high(%)'])

        # 0%の値は動くか確認
        if not self.__operation_judge(param):
            for index in self.vdf.index:
                margin_result.loc[index] = 0

        else:
            with tqdm(total=len(self.vdf)) as progress:
                futures = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
                    for index in self.vdf.index:
                        future = executor.submit(self.__get_margin, param, index, accuracy)
                        future.add_done_callback(lambda p: progress.update()) # tqdmで経過が知りたい時
                        futures.append(future)
                
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                    # 結果を受け取り
                    result_dic= future.result()
                    # variables dataframeに追加
                    margin_result.loc[result_dic["index"]] = result_dic["result"]

        # plot     
        if plot:
            min_margin = 100
            min_ele = None
            for element in margin_result.index:
                if not self.vdf.at[element,'fix']:
                    # 最小マージンの素子を探す。
                    if abs(margin_result.at[element,'low(%)']) < min_margin or abs(margin_result.at[element,'high(%)']) < min_margin:
                        min_margin = vaild_number(min(abs(margin_result.at[element,'low(%)']), abs(margin_result.at[element,'high(%)'])), 4)
                        min_ele = element

            margin_plot(margin_result, min_ele, blackstyle = blackstyle)

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
                #self.__plot(margins_for_plot, directory+"/"+str(k)+"-x.png")
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
