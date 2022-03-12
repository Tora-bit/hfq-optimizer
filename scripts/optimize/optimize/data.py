
import re
import pandas as pd
from .util import stringToNum, isfloat, isint
from .pyjosim import simulation
from .judge import judge
from .calculator import shunt_calc
import numpy as np
import concurrent
import copy
import matplotlib.pyplot as plt
import os
import shutil

# ----- Matplotlib の rc 設定 ----
config = {
    "font.size":18,
    "axes.grid":True,
    "figure.figsize":[10.0, 7.0],
    "legend.fontsize": 18,
    "lines.linewidth": 3
}
plt.rcParams.update(config)


class Data:
    def __init__(self, raw_data : str, show : bool = False, plot : bool = True):
        self.vdf, self.sim_data = self.__get_variable(raw=raw_data)
        self.time_start= float(self.__get_value(raw_data, "EndTimeOfBiasRise"))
        self.time_stop = float(self.__get_value(raw_data, "StartTimeOfPulseInput"))
        self.time_delay = float(self.__get_value(raw_data, "PulseDelay"))
        self.squids = self.__get_judge_spuid(raw_data)
        self.default_result = self.__default_simulation(plot=plot)

        if show:
            print("--- List of variables to optimize ---")
            print(self.vdf)
            print('\n')
            print("--- Period to calculate the initial value of bias ---")
            print(self.time_start, " ~ ", self.time_stop)
            print('\n')
            print("--- SQUID used for judging the operation ---")
            print(self.squids)
            print('\n')

    def __get_variable(self, raw : str) -> tuple:
        df = pd.DataFrame()
        
        vlist = re.findall('#.+\(.+?\)',raw)

        for raw_line in vlist:
            li = re.sub('\s','',raw_line)
            char = re.search('#.+?\(',li, flags=re.IGNORECASE).group()
            char = re.sub('#|\(','',char)
            if not df.empty and char in df['char'].tolist():
                continue
            dic = {'char': char,'def': None, 'main': None, 'sub': None, 'element':None,'fix': False,'shunt': None,'dp': True,'dpv': None,'tmp': 0}
            
            
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
                    break
            

            df = df.append(dic,ignore_index=True, verify_integrity=True)
        # dataframe の検査が必要かもしれない
        df.set_index('char', inplace=True)


        raw = re.sub('\*+\s*optimize[\s\S]+$','', raw)

        for v in re.findall('#.+\(.+?\)',raw):
            char = re.search('#.+?\(',v).group()
            char = re.sub('#|\(','',char)
            char = "#("+char+")"
            raw = raw.replace(v, char)
            
        return df , raw




    def __get_value(self, raw, key) -> str:
        m_object = re.search(key+'=[\d\.\+e-]+', raw, flags=re.IGNORECASE)
        if m_object:
            return re.split('=', m_object.group())[1]
        else:
            return None

    def __get_judge_spuid(self, raw : str) -> list:
        squids = []
        tmp = []
        for line in raw.splitlines():
            m_obj = re.search('\.print\s+phase.+',line, flags=re.IGNORECASE)
            if m_obj:
                data_sub = re.sub('\s|\.print|phase','',m_obj.group(), flags=re.IGNORECASE)
                tmp.append('P('+data_sub+')')
            else:
                if len(tmp)>0:
                    squids.append(tmp)
                    tmp = []
        return squids

    def __default_simulation(self,  plot = True) -> pd.DataFrame:
        df = self.__simulation(self.vdf['def'])
        if plot: 
            # print("default 値でのシュミレーション結果")
            df.plot()
            #df.plot(legend=False,figsize=(9, 6), fontsize=14, grid=True, linewidth=3)
        return judge(self.time_start, self.time_stop, df, self.squids, plot)


    def __simulation(self, parameter : pd.Series) -> pd.DataFrame:
        copied_sim_data = self.sim_data
        for index in parameter.index:
            copied_sim_data = copied_sim_data.replace('#('+index+')', str(parameter[index]))

        df = simulation(copied_sim_data)
        return df


    def __operation_judge(self, parameter : pd.Series):
        res = judge(self.time_start, self.time_stop, self.__simulation(parameter), self.squids)
        if self.default_result.drop('time', axis=1).equals(res.drop('time', axis=1)):
            for index in self.default_result.index:
                if self.default_result.at[index, 'element'] == res.at[index, 'element'] and self.default_result.at[index, 'phase'] == res.at[index, 'phase']:
                    time_df1 = self.default_result.at[index, 'time']
                    time_df2 = res.at[index, 'time']
                    if time_df2 < time_df1 - self.time_delay or time_df1 + self.time_delay < time_df2:
                        return False
                else:
                    return False
            return True    
        else:
            return False


    def get_margins(self, plot : bool = False, accuracy : int = 8, thread : int = 8) -> pd.DataFrame:
        margin_columns_list = ['low(value)', 'low(%)', 'high(value)', 'high(%)']

        futures = []
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=thread)
        for index in self.vdf.index:
            future = executor.submit(self.__get_margin, self.vdf['sub'], index, accuracy)
            futures.append(future)

        # result を受け取る dataframe
        margin_result = pd.DataFrame(columns = margin_columns_list)
        
        for future in concurrent.futures.as_completed(futures):
            # 結果を受け取り
            result_dic= future.result()
            # variables dataframeに追加
            margin_result.loc[result_dic["index"]] = result_dic["result"]

        if plot:
            self.__plot(margin_result)

        return margin_result


    def __get_margin(self, srs : pd.Series, target_ele : str, accuracy : int = 7):

        parameter : pd.Series = copy.deepcopy(srs)

        # デフォルト値の抽出
        default_v = parameter[target_ele]

        # 0%の値は動くか確認
        if not self.__operation_judge(parameter):
            return {"index" : target_ele, "result" : (0, 0, 0, 0)}

        # lower    
        high_v = default_v
        low_v = 0
        target_v = (high_v + low_v)/2

        for i in range(accuracy):
            parameter[target_ele] = target_v
            if self.__operation_judge(parameter):
                high_v = target_v
                target_v = (high_v + low_v)/2
            else:
                low_v = target_v
                target_v = (high_v + low_v)/2

        lower_margin = high_v
        lower_margin_rate = (lower_margin - default_v) * 100 / default_v

        # upper
        high_v = 0
        low_v = default_v
        target_v = default_v * 2

        for i in range(accuracy):

            parameter[target_ele] = target_v
            if self.__operation_judge(parameter):
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

        del parameter

        return {"index" : target_ele, "result" : (lower_margin, lower_margin_rate, upper_margin, upper_margin_rate)}


    
    def optimize(self, directory : str):
        # 今のところは10回の回数制限とbreakで処理
        # 後々、制限を変更したい
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.mkdir(directory)

        first_min_margin = 0
        for k in range(10):

            second_min_margin = 0
            margins_for_plot = None
            main_parameter = None
            #　ばらつきシュミレーション
            for j in range(15):
                
                self.vdf['sub'] = self.vdf['main'] 
                self.shunt_apply()
                # 最初の一回はそのままのマージンを計算
                if j > 0:
                    self.scatter_apply()
                
                pre_min_index = None    # ひとつ前の最小マージンを取るindex
                for i in range(10):
                    print(str(k)+":"+str(j)+":"+str(i)+"の最適化")
                    # マージンの計算
                    margins = self.get_margins()

                    min_margin = 100
                    min_index = None
                    for element in margins.index:
                        if not self.vdf.at[element,'fix']:
                            # 最小マージンの素子を探す。
                            if abs(margins.at[element,'low(%)']) < min_margin or abs(margins.at[element,'high(%)']) < min_margin:
                                min_margin = min(abs(margins.at[element,'low(%)']), abs(margins.at[element,'high(%)']))
                                min_index = element
                    
                    print("最小マージン : ", min_index, "  ", min_margin)


                    if min_margin > second_min_margin:
                        print("最適値の更新"+str(k)+":"+str(j)+":"+str(i)+"の最適化  ", min_margin, "%")
                        margins_for_plot = margins
                        second_min_margin = min_margin
                        main_parameter = copy.copy(self.vdf['sub'])

                    with open(directory+"/log.txt", 'a') as f:
                        f.write(str(k)+":"+str(j)+":"+str(i)+"の最小マージン : "+ str(min_index)+ "  "+ str(min_margin)+'\n') 

                    # 同じものが最適化対象になってしまったら終了
                    if pre_min_index == min_index:
                        break

                    # 最小マージンが0であれば終了
                    if min_margin == 0:
                        break

                    pre_min_index = min_index

                    # 最大マージンと最小マージンの中間点を次の最適化対象にする。
                    self.vdf.at[min_index,'sub'] = ( margins.at[min_index,'low(value)'] + margins.at[min_index,'high(value)'] )/2

                # --------------- ばらつきのループ

            if second_min_margin > first_min_margin:
                print("--- "+str(k)+":x:x"+"の最適化  ", second_min_margin, "% ---")
                first_min_margin = second_min_margin
                self.vdf['main'] = main_parameter
                print("保存")
                # 保存する
                self.__plot(margins_for_plot, directory+"/"+str(k)+"-x.png")
                self.vdf.to_csv(directory+"/"+str(k)+"-value.csv")

            else:
                print("最適化終了")
                break


    def shunt_apply(self):
        for index in self.vdf.index:
            if self.vdf.at[index, 'shunt'] != None:
                shunt_index = self.vdf.at[index, 'shunt']
                self.vdf.at[shunt_index, 'sub'] = shunt_calc(area=self.vdf.at[index, 'sub']) 


    def scatter_apply(self):
        for index in self.vdf.index:
            if self.vdf.at[index,'dp']:
                tmp = self.vdf.at[index,'sub']
                dpv = self.vdf.at[index,'dpv']
                self.vdf.at[index,'sub'] = np.random.normal(tmp,tmp*dpv/200)


    def __plot(self, margins : pd.DataFrame, filename = None):
        # バーのcolor
        plot_color = '#01b8aa'

        df = margins.sort_index()
        index = df.index
        column0 = df['low(%)']
        column1 = df['high(%)']

        # --- biasのカラーを変更したリスト ---
        index_color = []
        import re
        for i in index:
            if re.search('bias|Vb',i,flags=re.IGNORECASE):
                index_color.append('red')
            else:
                index_color.append(plot_color)
        # ------

        # 図のサイズ　sharey:グラフの軸の共有(y軸)
        fig, axes = plt.subplots(figsize=(10, len(index)/2.5), ncols=2, sharey=True)
        plt.subplots_adjust(wspace=0)
        # fig.suptitle("Operation Margin", fontsize=15)

        # 分割した 0 グラフ
        axes[0].barh(index, column0, align='center', color=index_color)
        axes[0].set_xlim(-100, 0)
        # axes[0].tick_params(labelsize=15)
        axes[0].grid(False)
        # 分割した 1 グラフ
        axes[1].barh(index, column1, align='center', color=index_color)
        axes[1].set_xlim(0, 100)
        # axes[1].tick_params(labelsize=15)
        axes[1].tick_params(axis='y', colors=plot_color)  # 1 グラフのメモリ軸の色をプロットの色と合わせて見れなくする
        axes[1].grid(False)

        if filename != None:
            fig.savefig(filename)
            plt.close(fig)