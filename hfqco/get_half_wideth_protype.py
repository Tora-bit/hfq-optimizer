import pandas as pd

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



#print("Write filename.")
#filename=input("Write filename: ")
#colnum_name=input("Write colnum_name: ")

#max_value_and_row_count(filename,colnum_name)
