""" Fluids Functions """
import numpy as np


def sutherlands_law(T):
    """ Returns the dynamic viscosity of air at temperature T (in Kelvin) using Sutherland's law. """
    visc_0 = 1.716e-5   # Pa.s
    T_0 = 273.15        # Kelvin  (ISA-consistent reference)
    S = 110.4           # Kelvin
    return visc_0 * (T / T_0)**1.5 * (T_0 + S) / (T + S)

def standardatmosphere(h):
    """ 
    Takes input of height 'h' and returns temperature, pressure, and density
    at the height provided using the Standard Atmospheric Model
    """
    # Library imports

    import numpy as np


    # Constants
    T0 = 288.15 # Kelvin   (ISA sea-level temperature)
        # Initial temperature

    P0 = 101325.0 # Pa     (ISA sea-level pressure, in Pascals)
        # Initial pressure

    g = 9.80665 # m/s^2    (standard gravity)
        # Acceleration due to gravity

    R = 287.05287 # J/kgK  (specific gas constant for dry air)
        # Ideal Gas constant

    bounds = [0,11000,20000,32000,47000,51000,71000,84852] # m  (ISA geopotential layer boundaries)
        # Thermal Atmospheric Boundaries

    grad = [-0.0065,0.0,0.0010,0.0028,0.0,-0.0028,-0.0020] # K/m (ISA lapse rates per layer)
        # Temperature gradients each layer

    # Initializing
    temp = np.zeros_like(bounds, dtype=float)
    temp[0] = T0
    pressure = np.zeros_like(bounds, dtype=float)
    pressure[0] = P0

    # Temperature and Pressure Calculations at each boundary
    for i in range(1, len(bounds)):
        dz = bounds[i] - bounds[i-1]
        if grad[i-1] != 0:
            temp[i] = temp[i-1] + grad[i-1] * dz
            # Pressure calculation requires the use of hydrostatic balance and the ideal gas law
            # Using these two equations we can get dP/P = -g/(R*T(alt))dz
            # This can get us to an equation: P + dP = P(1 - g/(RT(alt)))dz
            # The terms P + dP can be simplified to P2
            pressure[i] = pressure[i-1] * (temp[i] / temp[i-1])**(-g / (grad[i-1] * R))
        else:
            temp[i] = temp[i-1]
            pressure[i] = pressure[i-1] * np.exp(-g * dz / (R * temp[i-1]))

    # Clamp altitude to model range
    if h <= bounds[0]:
        i = 1
    elif h >= bounds[-1]:
        i = len(bounds) - 1
        h = bounds[-1]
    else:
        i = int(np.searchsorted(bounds, h))

    # Interpolate within the layer [bounds[i-1], bounds[i]]
    dz = h - bounds[i-1]

    if grad[i-1] != 0.0:
        T = temp[i-1] + grad[i-1] * dz
        P = pressure[i-1] * (T / temp[i-1]) ** (-g / (grad[i-1] * R))
    else:
        T = temp[i-1]
        P = pressure[i-1] * np.exp(-g * dz / (R * temp[i-1]))

    viscosity = sutherlands_law(T)
    rho = P / (R * T)
    a = np.sqrt(1.4 * 287 * T)
    return T, P, rho, viscosity, a

def heat_required(T_start, T_end, bounds, cp, latent, mass=1.0):
    """
    Energy (kJ) to go from T_start to T_end for a material with piecewise-constant cp and latent heats.
    - bounds: sorted list of phase-change temps [°C]
    - cp:     list of cp for each region (kJ/kg-K), length = len(bounds)+1
    - latent: list of latent heats at each bound (kJ/kg)
    Returns total energy in kJ.
    """
    if T_start == T_end:
        return 0.0

    sign = 1.0
    if T_end < T_start:
        T_start, T_end = T_end, T_start
        sign = -1.0

    import bisect
    i = bisect.bisect_right(bounds, T_start)
    T = T_start
    Q = 0.0

    for j, b in enumerate(bounds):
        if T < b < T_end:
            Q += mass * cp[i] * (b - T)
            Q += mass * latent[j]
            T = b
            i += 1

    # final sensible piece
    Q += mass * cp[i] * (T_end - T)
    return sign * Q

def height2flowvel(h_mm, angle=90, rho_mano=1000, rho_air=1.225, g=9.81):
    """
    h_mm        - Reading n the scale in mm
    angle       - Manometer angle to the horizon
    rho_mano    - Manometer fluid density
    rho_air     - Air density in the test section
    """
    h_v = (h_mm/1000) * np.sin(np.deg2rad(angle))
    dp = rho_mano * g * h_v
    V = np.sqrt(2*dp / rho_air)
    return V, dp, h_v