import matplotlib.pyplot as plt
import pandas as pd
import re

# ----- Matplotlib の rc 設定 ----
config = {
    "font.size":18,
    "axes.grid":True,
    "figure.figsize":[10.0, 7.0],
    "legend.fontsize": 18,
    "lines.linewidth": 3
}
plt.rcParams.update(config)

def phase_sim_plot(df : pd.DataFrame):
    df.plot()    
    plt.xlabel("Time [s]", size=18)  # x軸指定
    plt.ylabel("Phase difference [rad]", size=18)    # y軸指定

def voltage_sim_plot(df : pd.DataFrame):
    df.plot()    
    plt.xlabel("Time [s]", size=18)  # x軸指定
    plt.ylabel("Voltage [V]", size=18)    # y軸指定

def margin_plot(margins : pd.DataFrame, filename = None):
    # バーのcolor
    plot_color = '#01b8aa'

    df = margins.sort_index()
    index = df.index
    column0 = df['low(%)']
    column1 = df['high(%)']

    # --- biasのカラーを変更したリスト ---
    index_color = []
    for i in index:
        if re.search('bias|Vb',i,flags=re.IGNORECASE):
            index_color.append('red')
        else:
            index_color.append(plot_color)
    # ------

    # 図のサイズ　sharey:グラフの軸の共有(y軸)
    fig, axes = plt.subplots(figsize=(10, len(index)/2.5), ncols=2, sharey=True)
    plt.subplots_adjust(wspace=0)
    plt.suptitle('Margins')
    axes[0].set_ylabel("Elements", fontsize=20)
    axes[1].set_xlabel("%", fontsize=20)

    # 分割した 0 グラフ
    axes[0].barh(index, column0, align='center', color=index_color)
    axes[0].set_xlim(-100, 0)
    axes[0].grid(axis='y')


    # 分割した 1 グラフ
    axes[1].barh(index, column1, align='center', color=index_color)
    axes[1].set_xlim(0, 100)
    axes[1].tick_params(axis='y', colors=plot_color)  # 1 グラフのメモリ軸の色をプロットの色と合わせて見れなくする
    axes[1].grid(axis='y')


    if filename != None:
        fig.savefig(filename)
        plt.close(fig)