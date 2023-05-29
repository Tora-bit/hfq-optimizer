import pandas as pd
import math
import numpy as np
import re
from .config import Config
import matplotlib.pyplot as plt
from .graph import sim_plot

def get_switch_timing(config : Config, data : pd.DataFrame, plot = False, timescale = "ps", blackstyle = False) -> pd.DataFrame:

    p = math.pi
    p2 = math.pi * 2

    res_df = []

    if not config.phase_ele == []:
        new_df = pd.DataFrame()
        for squid in config.phase_ele:
            if len(squid) == 1:
                new_df['P('+'+'.join(squid)+')'] = data['P('+squid[0].upper()+')']
            elif len(squid) == 2:
                new_df['P('+'+'.join(squid)+')'] = data['P('+squid[0].upper()+')'] + data['P('+squid[1].upper()+')']
            elif len(squid) == 3:
                new_df['P('+'+'.join(squid)+')'] = data['P('+squid[0].upper()+')'] + data['P('+squid[1].upper()+')'] + data['P('+squid[2].upper()+')']
    
        if plot:
            sim_plot(new_df, timescale, blackstyle)

        for column_name, srs in new_df.items():
            # バイアスをかけた時の状態の位相(初期位相)
            init_phase = srs[( srs.index > config.start_time ) & ( srs.index < config.end_time )].mean()
            
            judge_phase = init_phase + p
            
            # クロックが入ってからのものを抽出
            srs = srs[srs.index > config.end_time]

            # 位相変数
            flag = 0
            for i in range(len(srs)-1):
                if (srs.iat[i] - (flag*p2 + judge_phase)) * (srs.iat[i+1] - (flag*p2 + judge_phase)) < 0:
                    flag = flag + 1
                    res_df.append({'time':srs.index[i], 'phase':flag, 'element':column_name})
                    # res_df = pd.concat([res_df, pd.DataFrame([{'time':srs.index[i], 'phase':flag, 'element':column_name}])], ignore_index=True)
                elif (srs.iat[i] - ((flag-1)*p2 + judge_phase)) * (srs.iat[i+1] - ((flag-1)*p2 + judge_phase)) < 0:
                    flag = flag - 1
                    res_df.append({'time':srs.index[i], 'phase':flag, 'element':column_name})
                    # res_df = pd.concat([res_df, pd.DataFrame([{'time':srs.index[i], 'phase':flag, 'element':column_name}])], ignore_index=True)

    if not config.voltage_ele == []:
        for vol in config.voltage_ele:
            srs_std = data['V('+vol+')'].rolling(window=10).std()
            srs_std_max = srs_std.rolling(window=10).max()
            srs_std.plot()
            basis = srs_std_max.mean()/2
            reap = False
            tmp = 0
            flag = 1
            for i in range(len(srs_std_max)-1):
                if not reap:
                    if srs_std_max.iat[i] < basis and basis < srs_std_max.iat[i+1]:
                        srs_std_max.iat[i] = basis *2
                        tmp = srs_std_max.index[i]
                        reap = True
                else:
                    if srs_std_max.iat[i] > basis and basis > srs_std_max.iat[i+1]:
                        srs_std_max.iat[i] = - basis * 2
                        if srs_std_max.index[i] - tmp > config.pulse_interval/2:
                            res_df = pd.concat([res_df, pd.DataFrame([{'time':tmp, 'phase':flag, 'element':'V('+vol+')'}])], ignore_index=True)
                            res_df = pd.concat([res_df, pd.DataFrame([{'time':srs_std_max.index[i], 'phase':-flag, 'element':'V('+vol+')'}])], ignore_index=True)
                            flag = flag + 1
                        reap = False

    return res_df


def compare_switch_timings(dl1 : list, dl2 : list, config : Config) -> bool:

    def get_dict(dict_list : list, phase : int, element : str) -> float:
        for l in dict_list:
            if l['phase'] == phase and l['element'] == element:
                return l['time']
        return 0

    # Number of switches is different
    if len(dl1) == len(dl2):
        for l1 in dl1:
            l2_time = get_dict(dl2, l1['phase'], l1['element'])
            l1_time = l1['time']
            if l2_time < l1_time - config.pulse_delay or l1_time + config.pulse_delay < l2_time:
                return False
        return True
    else:
        return False

def compare_switch_timings_detials(dl1 : list, dl2 : list, config : Config) -> str:

    def get_dict(dict_list : list, phase : int, element : str) -> float:
        for l in dict_list:
            if l['phase'] == phase and l['element'] == element:
                return l['time']
        return 0

    # Number of switches is different
    if len(dl1) == len(dl2):
        for l1 in dl1:
            l2_time = get_dict(dl2, l1['phase'], l1['element'])
            l1_time = l1['time']
            if l2_time < l1_time - config.pulse_delay or l1_time + config.pulse_delay < l2_time:
                return str("delay_fail")
        return str("true")
    else:
        return str("num_fail")


def get_propagation_switch_defference(dl : list, start_ele : str, end_ele : str, num : int)-> float:
    print('len(dl)='+str(len(dl)))
    if len(dl)!=(num*2):
        raise ValueError("\033[31mThe number of pulses is an unexpected value.\033[0m")
    
    sw_time_first=list()
    #phase_first=list()
    sw_time_end=list()
    #phase_end=list()
    for l in dl:
        print(l)
        if(l['element']==start_ele):
            sw_time_first.append(l['time'])
        if(l['element']==end_ele):
            sw_time_end.append(l['time'])

    #time_list.append(l['time'])
    #print(len(sw_time_first))
    #print(len(sw_time_end))
    delay_list=list()
    for i in range(10):
        #print(sw_time_end[i]-sw_time_first[i])
        delay_list.append(sw_time_end[i]-sw_time_first[i])

    #print(delay_list)
    delay_per=list()
    for i in range(len(delay_list)):
        delay_per.append(delay_list[i]/(101-1))

    delay_defference_list=list()
    for i in range(len(delay_per)):
        if i%2 == 0:
            delay_defference_list.append(delay_per[i+1]-delay_per[i])

    return np.mean(delay_defference_list)

def get_propagation_switch_defference_with_delay(dl : list, start_ele : str, end_ele : str, num : int)-> dict:
    print('len(dl)='+str(len(dl)))
    if len(dl)!=(num*2):
        raise ValueError("\033[31mThe number of pulses is an unexpected value.\033[0m")
    
    sw_time_first=list()
    #phase_first=list()
    sw_time_end=list()
    #phase_end=list()
    for l in dl:
        print(l)
        if(l['element']==start_ele):
            sw_time_first.append(l['time'])
        if(l['element']==end_ele):
            sw_time_end.append(l['time'])

    #time_list.append(l['time'])
    #print(len(sw_time_first))
    #print(len(sw_time_end))
    delay_list=list()
    for i in range(10):
        #print(sw_time_end[i]-sw_time_first[i])
        delay_list.append(sw_time_end[i]-sw_time_first[i])

    #print(delay_list)
    delay_per=list()
    for i in range(len(delay_list)):
        delay_per.append(delay_list[i]/(101-1))

    delay_defference_list=list()
    for i in range(len(delay_per)):
        if i%2 == 0:
            delay_defference_list.append(delay_per[i+1]-delay_per[i])

    out_dict=dict()
    out_dict['switch_defference']=np.mean(delay_defference_list)
    out_dict['even_delay']=np.mean(delay_list[0::2])
    out_dict['odd_delay']=np.mean(delay_list[1::2])
    return out_dict

#num_of_ele1とnum_of_ele2は何番目のパルスを比較するのか指定する
def get_switch_difference_time(dl : list, element1 : str, num_of_ele1 : list , element2 : str, num_of_ele2 : list)->list:
    sw_ele1=list()
    sw_ele2=list()
    output_list=list()
    if dl==[]:
        raise ValueError("No switch!!!")
    for l in dl:
        if l['element']==element1:
            sw_ele1.append(l)
        if l['element']==element2:
            sw_ele2.append(l)
    for e1 in sw_ele1:
        for e2 in sw_ele2:
            for n1 in num_of_ele1:
                for n2 in num_of_ele2:
                    #print('e1='+str(e1['phase']))
                    #print('n1='+str(n1))
                    #print('e2='+str(e2['phase']))
                    #print('n2='+str(n2))
                    if e1['phase']==n1 and e2['phase']==n2:
                        temp=dict()
                        print(e2)
                        print(e1)
                        temp['difference_time']=e2['time']-e1['time']
                        temp['num']=str(n2)+"-"+str(n1)
                        output_list.append(temp)
    #print(len(output_list))    
    return output_list
