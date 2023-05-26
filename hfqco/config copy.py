
class Config:
    def __init__(self, config_data : dict):
        # 全て確認
        for k in ["avgcalc.start.time", "avgcalc.end.time", "pulse.delay", "pulse.interval","phase.ele","voltage.ele","allow.multi.swithes"]:
            if not k in config_data:
                raise ValueError("\033[31m["+k+"]の値が読み取れません。"+"\033[0m")
        
        if not type(config_data["avgcalc.start.time"]) == float:
            raise ValueError("\033[31m[avgcalc.start.time]の値が読み取れません。\033[0m")

        if not type(config_data["avgcalc.end.time"]) == float:
            raise ValueError("\033[31m[avgcalc.end.time]の値が読み取れません。\033[0m")

        if not type(config_data["pulse.delay"]) == float:
            raise ValueError("\033[31m[pulse.delay]の値が読み取れません。\033[0m")

        if not type(config_data["pulse.interval"]) == float:
            raise ValueError("\033[31m[pulse.interval]の値が読み取れません。\033[0m")

        if not config_data["phase.ele"] == []:
            if not type(config_data["phase.ele"][0])==list:
                raise ValueError("\033[31m[phase.ele]の値が読み取れません。"+"\033[0m")

        if not type(config_data["allow.multi.swithes"]):
            raise ValueError("\033[31m[allow.multi.swithes]の値が読み取れません。\033[0m")

        self.start_time = config_data["avgcalc.start.time"]
        self.end_time = config_data["avgcalc.end.time"]
        print("･ (Period to calculate initial phase)\t\t= ",self.start_time, " ~ ", self.end_time, "[s]")
        
        self.pulse_delay = config_data["pulse.delay"]
        print("･ (Acceptable switch timing delay)\t\t= ",config_data["pulse.delay"], "[s]")
        
        self.pulse_interval= config_data["pulse.interval"]
        print("･ (Interval between input SFQ or HFQ pulses)\t= ", config_data["pulse.interval"], "[s]")
        
        self.phase_ele = config_data["phase.ele"]
        self.voltage_ele = config_data["voltage.ele"]
        self.allow_multi_swithes = config_data["allow.multi.swithes"]
