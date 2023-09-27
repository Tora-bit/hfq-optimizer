import re
import io
from subprocess import PIPE
import subprocess
import pandas as pd


def simulation(simulation_data : str) -> pd.DataFrame:
    
    result = subprocess.run(["josim-cli", "-i"], input=simulation_data, stdout=PIPE, stderr=PIPE, text=True)
    first_split = re.split('100%\s*Formatting\s*Output',result.stdout)
    if len(first_split) == 2:
        split_data = first_split[1]
    else:
        raise ValueError("\033[31m" + result.stderr + "\033[0m")
    
    return pd.read_csv(io.StringIO(split_data),index_col=0,header=0, sep='\s+') if split_data is not None else None
    #return pd.read_csv(io.StringIO(split_data),header=0, sep='\s+') if split_data is not None else None

def simulation_from_rebuilt(simulation_data : str, seed : int) -> pd.DataFrame:
    
    if seed<0:
        raise ValueError("Dont use negative seed value.")
    temp="seed="+str(seed)
    #result = subprocess.run(["/home/nakayama_tora/rebuilt_josim/JoSIM-master/build/josim-cli", "-i", temp], input=simulation_data, stdout=PIPE, stderr=PIPE, text=True)
    result = subprocess.run(["/home/nakayama_tora/rebuilt_josim/JoSIM-master/build/josim-cli", temp, "-i"], input=simulation_data, stdout=PIPE, stderr=PIPE, text=True)
    first_split = re.split('100%\s*Formatting\s*Output',result.stdout)
    #print(first_split)
    if len(first_split) == 2:
        split_data = first_split[1]
    else:
        raise ValueError("\033[31m" + result.stderr + "\033[0m")
    
    return pd.read_csv(io.StringIO(split_data),index_col=0,header=0, sep='\s+') if split_data is not None else None
    #return pd.read_csv(io.StringIO(split_data),header=0, sep='\s+') if split_data is not None else None

def simulation_from_rebuilt_NoSeed(simulation_data : str) -> pd.DataFrame:
    
    result = subprocess.run(["/home/nakayama_tora/rebuilt_josim/JoSIM-master/build/josim-cli", "-i"], input=simulation_data, stdout=PIPE, stderr=PIPE, text=True)
    #result = subprocess.run(["/home/nakayama_tora/rebuilt_josim/JoSIM-master/build/josim-cli", temp, "-i"], input=simulation_data, stdout=PIPE, stderr=PIPE, text=True)
    first_split = re.split('100%\s*Formatting\s*Output',result.stdout)
    #print(first_split)
    if len(first_split) == 2:
        split_data = first_split[1]
    else:
        raise ValueError("\033[31m" + result.stderr + "\033[0m")
    
    return pd.read_csv(io.StringIO(split_data),index_col=0,header=0, sep='\s+') if split_data is not None else None
    #return pd.read_csv(io.StringIO(split_data),header=0, sep='\s+') if split_data is not None else None
    