
class Config:
    def __init__(self, config_data : dict):
        # 全て確認
        #for k in ["avgcalc.pre_start.time", "avgcalc.pre_end.time", "avgcalc.start.time", "avgcalc.end.time", "pulse.delay", "pulse.interval","phase.ele","voltage.ele","allow.multi.swithes","state_judge"]:
        for k in ["avgcalc.start.time", "avgcalc.end.time", "pulse.delay", "pulse.interval","phase.ele","voltage.ele","allow.multi.swithes","state_judge"]:
            if not k in config_data:
                raise ValueError("\033[31m["+k+"]の値が読み取れません。"+"\033[0m")
        #,"list_of_state","list_of_transition","initial_state","output_ele","output_interval"

        #if not type(config_data["avgcalc.pre_start.time"]) == float:
        #    raise ValueError("\033[31m[avgcalc.start.time]の値が読み取れません。\033[0m")

        #if not type(config_data["avgcalc.pre_end.time"]) == float:
        #    raise ValueError("\033[31m[avgcalc.end.time]の値が読み取れません。\033[0m")

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

        if not type(config_data["state_judge"]):
            raise ValueError("\033[31m[state_judge]の値が読み取れません。\033[0m")
        else:
            self.state_judge = config_data["state_judge"]

        if self.state_judge:
            if not config_data["list_of_state"] == []:
                if not type(config_data["list_of_state"])==list:
                    raise ValueError("\033[31m[list_of_state]の値が読み取れません。"+"\033[0m")

            if not config_data["list_of_transition"] == []:
                if not type(config_data["list_of_transition"][0])==list:
                    raise ValueError("\033[31m[list_of_transition[trigger, source, dest, action(True_Output or False_Output)]]の値が読み取れません。"+"\033[0m")

            if not type(config_data["initial_state"]) == str:
                raise ValueError("\033[31m[initial_state]の値が読み取れません。\033[0m")

            if not type(config_data["output_ele"]) == list:
                raise ValueError("\033[31m[output_ele]の値が読み取れません。\033[0m")

            if not type(config_data["output_interval"]) == float:
                raise ValueError("\033[31m[output_interval]の値が読み取れません。\033[0m")

        #self.pre_start_time=config_data["avgcalc.pre_start.time"]
        #self.pre_end_time = config_data["avgcalc.pre_end.time"]
        self.start_time = config_data["avgcalc.start.time"]
        self.end_time = config_data["avgcalc.end.time"]
        print("･ (Period to calculate initial phase)\t\t= ",self.start_time, " ~ ", self.end_time, "[s]")
        
        self.pulse_delay = config_data["pulse.delay"]
        print("･ (Acceptable switch timing delay)\t\t= ",config_data["pulse.delay"], "[s]")
        
        self.pulse_interval= config_data["pulse.interval"]
        print("･ (Interval between input SFQ or HFQ pulses)\t= ", config_data["pulse.interval"], "[s]")
        
        self.phase_ele = config_data["phase.ele"]
        self.voltage_ele = config_data["voltage.ele"]
        print(self.voltage_ele)
        self.allow_multi_swithes = config_data["allow.multi.swithes"]

        if self.state_judge:
            #self.voltage_eleは要らない
            self.voltage_ele = []
            self.state_judge = config_data["state_judge"]
            self.list_of_state = config_data["list_of_state"]
            self.list_of_transition = config_data["list_of_transition"]
            self.initial_state = config_data["initial_state"]
            self.output_element = config_data["output_ele"]
            self.output_interval = config_data["output_interval"]
