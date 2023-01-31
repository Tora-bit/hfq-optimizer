import math
import re
import numpy as np
from .util import SIstr 
from scipy.stats import truncnorm


def betac(calc_type: str, area: float = None, Rshunt: float= None, Rsubgap: float = 100, Cap : float = 0.064e-12, Ic: float = 0.1e-3, betac: float = 1) -> float:
    phi = 2.068 * 10 ** -15
    
    if re.fullmatch('area', calc_type, flags= re.IGNORECASE):
        if Rshunt == None:
            raise ValueError('areaを計算するときはRshuntの値を入力してください。')
        
        denomi = Rshunt * ( math.sqrt(2 * math.pi * Ic * Cap / (phi * betac)) - 1/Rsubgap )
        return 1/denomi

    elif re.fullmatch('betac', calc_type, flags= re.IGNORECASE):
        if area == None or Rshunt == None:
            raise ValueError('betacを計算するときはarea, Rshuntの値を入力してください。')

        _Cap = Cap * area
        _Ic = Ic * area
        _Rsubgap = Rsubgap / area
        Rj = Rshunt * _Rsubgap/(Rshunt + _Rsubgap)

        return (2 * math.pi * _Ic * _Cap * Rj**2) / phi

    elif re.fullmatch('shunt', calc_type, flags= re.IGNORECASE):
        if area == None:
            raise ValueError('Rshuntを計算するときはareaの値を入力してください。')
        _Cap = Cap * area
        _Ic = Ic * area
        _Rsubgap = Rsubgap / area
        denomi = math.sqrt(2 * math.pi * _Ic * _Cap / (phi * betac)) - 1/_Rsubgap
        return 1/denomi

    else:
        raise ValueError('calc_type(計算タイプ)の値が読み取れません。')


def shunt_calc(area: float, Rsubgap: float = 100, Cap : float = 0.064e-12, Ic: float = 0.1e-3, betac: float = 1) -> float:
    phi = 2.068 * 10 ** -15
    _Cap = Cap * area
    _Ic = Ic * area
    _Rsubgap = Rsubgap / area
    denomi = math.sqrt(2 * math.pi * _Ic * _Cap / (phi * betac)) - 1/_Rsubgap
    return 1/denomi

def betac_calc(area: float, Rshunt: float, Rsubgap: float = 100, Cap : float = 0.064e-12, Ic: float = 0.1e-3) -> float:
    phi = 2.068 * 10 ** -15
    _Cap = Cap * area
    _Ic = Ic * area
    _Rsubgap = Rsubgap / area
    Rj = Rshunt * _Rsubgap/(Rshunt + _Rsubgap)

    return (2 * math.pi * _Ic * _Cap * Rj**2) / phi

def rand_norm(mean, std, upper = None, lower = None):
    if upper == None:
        b = np.inf
    else:
        b = (upper - mean) / std

    if lower == None:
        a = -np.inf
    else:
        a = (lower - mean) / std 

    return truncnorm(a, b, loc=mean, scale=std).rvs()

def nominal_ic(L, Ic, strout = False):
    x = (L * Ic) / (2.07*10**(-15))
    result = (0.5263*x**6 -2.3279*x**5 + 3.4434*x**4 - 1.0023*x**3 - 2.5876*x**2 + 3.341*x)*Ic
    if strout:
        return SIstr(result) + "A"
    else:
        return result

def nominal_ic_check(L, Ic, strout = False):
    x = (L * Ic) / (2.068*10**(-15))
    result = (2.8009*x**6 -9.4513*x**5 + 11.697*x**4 - 5.2501*x**3 - 1.7062*x**2 + 3.3052*x)*Ic
    if strout:
        return SIstr(result) + "A"
    else:
        return result