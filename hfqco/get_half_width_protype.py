import pandas as pd
import numpy as np

def max_value_and_row_count(csv_file, column_name)-> float:
    # CSVファイルを読み込み、指定された列のデータを取得する
    data = pd.read_csv(csv_file)
    column_data = data[column_name]
    
    # 最大値を計算する
    max_value = column_data.max()
    
    # 最大値を持つ行のインデックスを取得する
    max_rows = column_data[column_data == max_value].index.tolist()
    
    # 最大値と行数を出力する
    print(f"最大値: {max_value}")
    print(f"行数: {len(max_rows)}")

    return max_value

def max_value_and_row_count_outlist(csv_file, column_name)->list:
    # CSVファイルを読み込み、指定された列のデータを取得する
    data = pd.read_csv(csv_file)
    column_data = data[column_name].to_list()
    time_data=data['time'].to_list()
    #index=10
    # 最大値を計算する
    max_value=max(column_data)
    index=column_data.index(max_value)
    max_time=time_data[index]
    # 最大値と行数を出力する
    print(f"時刻: {max_time}")
    print(f"最大値: {max_value}")
    print(f"index: {index}")
    
    temp=list()
    temp.append(index)
    temp.append(max_time)
    temp.append(max_value)
    return temp

def separate_data(csv_file, column_name, separate_value:float)->list:
    temp=list()
    temp_list=list()
    data = pd.read_csv(csv_file)
    time=data['time'].to_list()
    column_data = data[column_name].to_list()

    for i in range(len(time)):
        temp_dict=dict()
        temp_dict['time']=time[i]
        temp_dict['data']=column_data[i]
        temp_list.append(temp_dict)

    temp.append(list(filter(lambda x: x['time']<=separate_value, temp_list)))
    temp.append(list(filter(lambda x: x['time']>separate_value, temp_list)))

    return temp

def remove_closest_value(time_arr, data_arr, target_value)->list:
    # 配列から指定された値との差分を計算する
    target_values=np.array(target_value)
    diffs = np.abs(data_arr - target_values)

    # 差分の最小値を持つインデックスを取得する
    closest_index = np.argmin(diffs)

    # 最も近い値とそのインデックスを出力する
    print(f"{target_value}に最も近い値: {data_arr[closest_index]}, インデックス: {closest_index}")

    
    temp=dict()
    temp['index']=closest_index
    temp['time']=time_arr[closest_index]
    temp['value']=data_arr[closest_index]

    # 配列から最も近い値を削除し、更新された配列を出力する
    new_arr = np.delete(data_arr, closest_index)
    new_time_arr=np.delete(time_arr, closest_index)
    #del time_arr[closest_index]
    #print("更新された配列:", new_arr)

    temp['new_time_arr']=new_time_arr
    temp['new_arr']=new_arr

    return temp

""" def close_values(csv_file, column_name, target_value)->list:
    data = pd.read_csv(csv_file)
    time=data['time'].to_list()
    column_data = data[column_name]
    arr=column_data.to_list()
    temp_list=list()
    new_time_arr=list()
    new_arr=list()

    for i in range(2):
        print(i)
        temp_dict=dict()
        if i>0:
            temp=remove_closest_value(new_time_arr,new_arr,target_value)
        else:
            temp=remove_closest_value(time,arr,target_value)
        temp_dict['time']=temp['time']
        temp_dict['value']=temp['value']
        new_time_arr=temp['new_time_arr']
        new_arr=temp['new_arr']
        temp_list.append(temp_dict)

    return temp_list """

def close_values(data_sets:list, target_value)->list:
    time=list()
    arr=list()
    for dl in data_sets:
        time.append(dl['time'])
        arr.append(dl['data'])
    temp_list=list()
    new_time_arr=list()
    new_arr=list()

    for i in range(1):
        print(i)
        temp_dict=dict()
        if i>0:
            temp=remove_closest_value(new_time_arr,new_arr,target_value)
        else:
            temp=remove_closest_value(time,arr,target_value)
        temp_dict['time']=temp['time']
        temp_dict['value']=temp['value']
        new_time_arr=temp['new_time_arr']
        new_arr=temp['new_arr']
        temp_list.append(temp_dict)

    return temp_list


def get_halfwidth(path : str, column_name : str) -> float:
    max=max_value_and_row_count_outlist(path,column_name)
    separated_datas=separate_data(path,column_name,max[1])
    data_list1=close_values(separated_datas[0],max[2]/2.0)
    data_list2=close_values(separated_datas[1],max[2]/2.0)
    print((data_list2[0]['time']-data_list1[0]['time']))
    print('{:.6g}'.format(1.0/((data_list2[0]['time']-data_list1[0]['time'])*10)))

    return (data_list2[0]['time']-data_list1[0]['time'])


#print("Write filename.")
#filename=input("Write filename: ")
#colnum_name=input("Write colnum_name: ")

#max_value_and_row_count(filename,colnum_name)
