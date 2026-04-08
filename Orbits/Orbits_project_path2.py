import Orbits.Orbits_Functions as of
import numpy as np
from matplotlib import pyplot as plt
from datetime import datetime, timedelta

import os

os.system('cls')

#---------------------------- UTILITY FUNCTIONS ----------------------------#

def stitch_segments(segments):
    out = segments[0]
    for seg in segments[1:]:
        if out.shape[1] > 0 and seg.shape[1] > 0 and np.allclose(out[:, -1], seg[:, 0]):
            out = np.concatenate((out, seg[:, 1:]), axis=1)
        else:
            out = np.concatenate((out, seg), axis=1)
    return out

def propagate_segments(y_segments, tspan, teval=None):
    """
    Propagate a list of orbit state segments by a given time span.

    Parameters
    ----------
    y_segments : list of np.ndarray
        Each element can be either
          • shape (6,)  -> a single [r; v] state, or
          • shape (6,N) -> a segment of states (e.g., ODEprimer.y[0:6]).
        Propagation starts from the state itself (6,) or from the LAST column (6,N).
    tspan : list or tuple
        [t0, tf] time span (seconds) to propagate each orbit.
    teval : array-like or None
        Optional time evaluation points for ODEprimer.

    Returns
    -------
    new_segments : list of np.ndarray
        List of propagated 6×M arrays (ODE solution slices sol.y[0:6]).
    h_list, e_list, inc_list, raan_list, argp_list, ta_list : lists
        Classical orbital elements at each propagated segment’s final state.
    """
    new_segments = []
    h_list, e_list = [], []
    inc_list, raan_list, argp_list, ta_list = [], [], [], []

    for y in y_segments:
        y = np.asarray(y)

        # Get a 1-D initial state (rx,ry,rz,vx,vy,vz)
        if y.ndim == 1:
            if y.size != 6:
                raise ValueError("1-D state must have 6 elements.")
            r0 = y[:3]
            v0 = y[3:6]
        elif y.ndim == 2:
            if y.shape[0] != 6 or y.shape[1] < 1:
                raise ValueError("2-D segment must have shape (6, N>=1).")
            # Start from the *end* of the previous segment
            r0 = y[0:3, -1]
            v0 = y[3:6, -1]
        else:
            raise ValueError("State/segment must be 1-D (6,) or 2-D (6,N).")

        # Propagate
        sol = of.ODEprimer(r0, v0, tspan, teval=teval)

        # Final state and COEs
        rx, ry, rz, vx, vy, vz = sol.y[0:6, -1]
        state_end = np.array([rx, ry, rz, vx, vy, vz])
        h_vec, e_vec, inc, raan, argp, ta = of.ECI2COEs(state_end)

        new_segments.append(sol.y[0:6])
        h_list.append(h_vec)
        e_list.append(e_vec)
        inc_list.append(inc)
        raan_list.append(raan)
        argp_list.append(argp)
        ta_list.append(ta)

    return new_segments, h_list, e_list, inc_list, raan_list, argp_list, ta_list

def epoch_to_datetime(epoch_year, epoch_day):
    # Coerce to Python types
    y = int(float(epoch_year))
    d = float(epoch_day)

    if y < 100:
        y = 2000 + y if y < 57 else 1900 + y

    day_int = int(d)
    frac = d - day_int 
    base = datetime(y, 1, 1) + timedelta(days=day_int - 1)
    return base + timedelta(seconds=frac * 86400.0)


#---------------------------- TLEs ----------------------------#

""" MUST STAY IN SYNC WITH DEBRIS FOR 5 PERIODS """

TLEs_original = [
    [
        "DELTA 2 DEB",
        "1 25138U 98002E   25321.77251655  .00000756  00000-0  47462-3 0  9993",
        "2 25138  26.8788 345.9874 0323619 168.6975 354.1864 13.72117421392909"
    ],
    [
        "DELTA 1 DEB",
        "1 10227U 77065BE  25321.71492541  .00006135  00000-0  20445-2 0  9995",
        "2 10227  28.9572 330.4974 0675997 286.1808  66.5427 13.52266693346021"
    ],
    [
        "ATLAS 5 CENTAUR DEB",
        "1 46656U 18079CJ  25321.49577821 -.00000102  00000-0  00000-0 0  9992",
        "2 46656  13.3737  20.3709 4531874 347.7674   4.2683  1.96953546 36789"
    ],
    [
        "TITAN 3C TRANSTAGE DEB",
        "1 38695U 68081V   25321.21743478 -.00000041  00000-0  00000+0 0  9998",
        "2 38695   1.8787  19.2505 0430881 271.1786  96.3341  0.99387212 61242"
    ]
]





#---------------------------- LEGEND ----------------------------#
# 0 - Before common epoch
# 1 - After propagating to common epoch
# 2 - After 5 periods of GEO debris
# 3 - Reaching point of circularization of GEO orbit
# 4 - Inc and RAAN change to match MEO
# 5 - Beginning of Hohmann transfer to MEO
# 6 - Arrival at MEO


#---------------------------- BRING TO COMMON EPOCH ----------------------------#

# Initializing
epochs = []
COEs_1_all = []
y0_1_all = []
T_list = []
ECI0 = []
h1_list, e1_list = [], []
inc1_list, raan1_list, argp1_list, ta1_list = [], [], [], []
h0_list, e0_list = [], []
inc0_list, raan0_list, argp0_list, ta0_list = [], [], [], []

# Parse Epochs from TLEs
for tle in TLEs_original:
    _, _, time = of.parse_tle(tle)
    epoch_year, epoch_day = time
    epochs.append(epoch_to_datetime(epoch_year, epoch_day))
    
# Propagation Values
time_initial = max(epochs)
mu = 398600

# Propoagate to common epoch
for tle, time_now in zip(TLEs_original, epochs):
    COEs_1, ECI, _ = of.parse_tle(tle)
    inclination, raan, eccentricity, arg_perigee, h, TA, rev_number = COEs_1
    h0_list.append(h)
    e0_list.append(eccentricity)
    inc0_list.append(inclination)
    raan0_list.append(raan)
    argp0_list.append(arg_perigee)
    ta0_list.append(TA)
    ECI0.append(ECI)
    r0, v0 = of.COEs2ECI(COEs_1[4], COEs_1[2], COEs_1[0], COEs_1[1], COEs_1[3], COEs_1[5])
    
    ds = (time_initial - time_now).total_seconds()
    if ds != 0.0:
        sol_new = of.ODEprimer(r0, v0, [0.0, ds])
        
        rx, ry, rz, vx, vy, vz = sol_new.y[0:6, -1]
        r0 = np.array([rx, ry, rz])
        v0 = np.array([vx, vy, vz])
        
    y0_1 = np.hstack((r0, v0))
    COEs_1 = of.ECI2COEs(y0_1)
    h_vec, e_vec, inc, raan, argp, ta = COEs_1
    a = np.linalg.norm(h_vec)**2/(mu*(1-np.linalg.norm(e_vec)**2))
    T = 2*np.pi*np.sqrt(a**3/mu)
    h1_list.append(h_vec)
    e1_list.append(e_vec)
    inc1_list.append(inc)
    raan1_list.append(raan)
    argp1_list.append(argp)
    ta1_list.append(ta)
    y0_1_all.append(y0_1)
    T_list.append(T)


    
#---------------------------- PROPAGATE 5 PERIODS OF GEO DEBRIS ----------------------------#

# Calculate 5 periods of GEO debris
T5_geo = T_list[3]*5   # seconds

# Propagation Values
tspan_2 = [0.0, T5_geo] # 5 periods of first debris
t_eval_2 = None           # ADD IN TVAL AT THE END

# Propagate orbits forward by 5 periods of GEO debris
y0_2_all, h2_list, e2_list, inc2_list, raan2_list, argp2_list, ta2_list = propagate_segments(
    y0_1_all, tspan_2, teval=t_eval_2
)

#---------------------------- PROPAGATE TO CIRCULARIZE GEO DEBRIS ----------------------------#

# Change in time from ta_2 to circularization point
dt_3 = of.time_between_true_anom(ta2_list[3], np.deg2rad(180), np.linalg.norm(e2_list[3]), np.linalg.norm(h2_list[3])) # SECONDS

# Propagation Values
tspan3 = [0.0, dt_3]
teval3 =  None
# Propagate orbits to circularization point
y0_3_all, h3_list, e3_list, inc3_list, raan3_list, argp3_list, ta3_list = propagate_segments(
    y0_2_all, tspan3, teval=teval3
)


#---------------------------- PROPAGATE TO INC RAAN CHANGE ----------------------------#

# Change in time from ta_3 to inc raan change
ra_geo = 37858 + 6378
T_geo_circ = 2*np.pi*np.sqrt(ra_geo**3/mu)
dt_4 = ((180+88.3298)/360)*T_geo_circ

# Propagation Values
tspan4 = [0.0, dt_4]
teval4 = None

# Propagate orbits to inc raan change
y0_4_all, h4_list, e4_list, inc4_list, raan4_list, argp4_list, ta4_list = propagate_segments(
    y0_3_all, tspan4, teval=teval4
)


#---------------------------- PROPAGATE TO HOHMANN TRANSFER DEPARTURE TO MEO ----------------------------#

# Change in time from inc raan change to hohmann transfer start
dt_5 = ((np.rad2deg(argp4_list[2])- 88.3298)/360)*T_geo_circ # SECONDS

# Propagation Values
tspan5 = [0.0, dt_5]
teval5 = None

# Propagate orbits to hohmann transfer start
y0_5_all, h5_list, e5_list, inc5_list, raan5_list, argp5_list, ta5_list = propagate_segments(
    y0_4_all, tspan5, teval=teval5
)


#---------------------------- PROPAGATE TO MEO ARRIVAL ----------------------------#

# Position vector at GEO transfer start
r_circ_sc, v_circ_sc = of.COEs2ECI(np.linalg.norm(h0_list[3]), 0, inc0_list[2], raan0_list[2], argp0_list[3], ta5_list[3])
ECI_circ_sc = np.hstack((r_circ_sc, v_circ_sc))
ECI_circ_sc = np.hstack((r_circ_sc, v_circ_sc)).reshape(6,)
y0_5_sc, _, _, _, _, _, _ = propagate_segments(
    [ECI_circ_sc], [0.0, dt_5], teval=teval5
)
ra_h_t = y0_5_sc[0][0:3, -1]
v5_sc = y0_5_sc[0][3:6, -1]
# Position vector at MEO transfer arrival
dt_fill_in = of.time_between_true_anom(ta5_list[2], np.deg2rad(180), np.linalg.norm(e5_list[2]), np.linalg.norm(h5_list[2]))  # SECONDS
y0_fill_in, _, _, _, _, _, _ = propagate_segments(
    y0_5_all, [0.0, dt_fill_in], teval=None
)
rp_h_t = y0_fill_in[2][0:3, -1]

ra_h_t_norm = np.linalg.norm(ra_h_t)
rp_h_t_norm = np.linalg.norm(rp_h_t)

#---- Velocity vector at perigee and apogee of Hohmann transfer ----#

# Classical orbital elements
a_h_t = (ra_h_t_norm + rp_h_t_norm)/2
e_h_t = (ra_h_t_norm - rp_h_t_norm)/(ra_h_t_norm + rp_h_t_norm)
p_h_t = a_h_t*(1-e_h_t**2)
h_h_t = np.sqrt(mu*p_h_t)

# Vector calculations
h_direction_ht = np.cross(ra_h_t, v5_sc)
h_direction_ht = h_direction_ht/np.linalg.norm(h_direction_ht)

v_direction_p_ht = np.cross(h_direction_ht, rp_h_t)
v_hat_p_ht = v_direction_p_ht / np.linalg.norm(v_direction_p_ht)
v_vec_p_ht = np.sqrt(mu*(2/rp_h_t_norm - 1/a_h_t)) * v_hat_p_ht

v_direction_a_ht = np.cross(h_direction_ht, ra_h_t)
v_hat_a_ht = v_direction_a_ht / np.linalg.norm(v_direction_a_ht)
v_vec_a_ht = np.sqrt(mu*(2/ra_h_t_norm - 1/a_h_t)) * v_hat_a_ht

# Initial state vector at hohmann transfer to MEO
y0_5_sc = np.hstack((ra_h_t, v_vec_a_ht))

# Delta V calculations
delv_h_departure = np.linalg.norm(v_vec_a_ht - v5_sc)
delv_h_arrival = np.linalg.norm(y0_fill_in[2][3:6, -1] - v_vec_p_ht)

# Change of time through hohmann transfer to MEO
dt_6 = np.pi*np.sqrt(a_h_t**3/mu)

# Propagation Values
tspan6 = [0.0, dt_6]
teval6 = None

# Propagate orbits to hohmann transfer start
y0_6_all, h6_list, e6_list, inc6_list, raan6_list, argp6_list, ta6_list = propagate_segments(
    y0_5_all, tspan6, teval=teval6
)

#---------------------------- PROPAGATE TO MEO PERIGEE FOR PHASE CHANGE ----------------------------#

# Change in time from MEO arrival to perigee for phase change
dt_7 = of.time_between_true_anom(np.deg2rad(180), np.deg2rad(0), np.linalg.norm(e6_list[2]), np.linalg.norm(h6_list[2]))  # SECONDS

# Propagation Values
tspan7 = [0.0, dt_7]
teval7 = None

# Propagate orbits to perigee for phase change
y0_7_all, h7_list, e7_list, inc7_list, raan7_list, argp7_list, ta7_list = propagate_segments(
    y0_6_all, tspan7, teval=teval7
)

#---------------------------- PROPAGATE PHASE CHANGE MEO ----------------------------#

# Radius of perigee and apogee of MEO debris
h_meo = np.linalg.norm(h7_list[2])
e_meo = np.linalg.norm(e7_list[2])
rp_meo = (h_meo**2/mu)/(1+e_meo)
ra_meo = (h_meo**2/mu)/(1-e_meo)
rp_7_vec = y0_7_all[2][0:3, -1]
vp_7_vec = y0_7_all[2][3:6, -1]

# Direction of burn
v7_hat = vp_7_vec / np.linalg.norm(vp_7_vec)

# Change in time and velocity for phase change
delv_phase_change_MEO_1, delv_phase_change_MEO_2, dt_8 = of.phase_change_delta_v(rp_meo, ra_meo, np.rad2deg(ta7_list[2]))

# Delta v Vector
delv_h_arrival_vec = delv_phase_change_MEO_1 * v7_hat
delv_h_depart_vec = delv_phase_change_MEO_2 * v7_hat

# Propagation Values
tspan8 = [0.0, dt_8]
teval8 = None

# Propagate orbits through phase change
y0_8_all, h8_list, e8_list, inc8_list, raan8_list, argp8_list, ta8_list = propagate_segments(
    y0_7_all, tspan8, teval=teval8
)

#---------------------------- PROPAGATE 5 PERIODS OF MEO DEBRIS ----------------------------#

# Calculate 5 periods of MEO debris
T5_meo = T_list[2]*5   # seconds

# Propagation Values
tspan_9 = [0.0, T5_meo] # 5 periods of MEO debris
t_eval_9 = None           # ADD IN TVAL AT THE END

# Propagate orbits forward by 5 periods of GEO debris
y0_9_all, h9_list, e9_list, inc9_list, raan9_list, argp9_list, ta9_list = propagate_segments(
    y0_8_all, tspan_9, teval=t_eval_9
)

#---------------------------- FIND OPTIMAL DEPARTURE AND ARRIVAL DATE FOR LAMBERT 1 ------------------------#

# State vectors of MEO and LEO1
r9_vec_meo, v9_vec_meo = of.COEs2ECI(np.linalg.norm(h1_list[2]), np.linalg.norm(e0_list[2]), np.deg2rad(inc0_list[2]), np.deg2rad(raan0_list[2]), np.deg2rad(argp0_list[2]), np.deg2rad(ta9_list[2]))
y09_meo = np.hstack((r9_vec_meo, v9_vec_meo))
r9_vec_leo1, v9_vec_leo1 = of.COEs2ECI(np.linalg.norm(h1_list[0]), np.linalg.norm(e0_list[1]), np.deg2rad(inc0_list[1]), np.deg2rad(raan0_list[1]), np.deg2rad(argp0_list[1]), np.deg2rad(ta9_list[1]))
y09_leo1 = np.hstack((r9_vec_leo1, v9_vec_leo1))

# Porkchop plot
valid_dep_and_arr1 = of.lamberts_porkchop(y09_meo, y09_leo1, t1_max=2.5*3600, t2_max=8*3600, t_step=300)
lambert1 = valid_dep_and_arr1[0]


#---------------------------- PROPAGATE TO LAMBERT DEPARTURE -------------------------------#

# Time until lambert departure
dt_10 = lambert1["t1_sec"]

# Propagation Values
tspan_10 = [0.0, dt_10] # to lambert departure
t_eval_10 = None           # ADD IN TVAL AT THE END

# Propagate orbits forward to lambert departure
y0_10_all, h10_list, e10_list, inc10_list, raan10_list, argp10_list, ta10_list = propagate_segments(
    y0_9_all, tspan_10, teval=t_eval_10
)

#---------------------------- PROPAGATE LAMBERT TO LEO 1 ----------------------------#

# Change in time through lambert transfer to LEO 1
dt_11 = (lambert1["t2_sec"] - lambert1["t1_sec"]) # SECONDS

# Propagation Values
tspan_11 = [0.0, dt_11]
t_eval_11 = None

# Propagate orbits through lambert transfer to LEO 1
y0_11_all, h11_list, e11_list, inc11_list, raan11_list, argp11_list, ta11_list = propagate_segments(
    y0_10_all, tspan_11, teval=t_eval_11
)

#---------------------------- PROPAGATE 5 PERIODS OF LEO 1 DEBRIS ----------------------------#

# Calculate 5 periods of LEO 1 debris
T5_leo1 = T_list[1]*5   # seconds

# Propagation Values
tspan_12 = [0.0, T5_leo1] # 5 periods of LEO 1 debris
t_eval_12 = None           # ADD IN TVAL AT THE END

# Propagate orbits forward by 5 periods of GEO debris
y0_12_all, h12_list, e12_list, inc12_list, raan12_list, argp12_list, ta12_list = propagate_segments(
    y0_11_all, tspan_12, teval=t_eval_12
)



#---------------------------- FIND OPTIMAL DEPARTURE AND ARRIVAL DATE FOR LAMBERT 2 ------------------------#

# State vectors of MEO and LEO1
r12_vec_leo1, v12_vec_leo1 = of.COEs2ECI(np.linalg.norm(h1_list[1]), np.linalg.norm(e0_list[1]), np.deg2rad(inc0_list[1]), np.deg2rad(raan0_list[1]), np.deg2rad(argp0_list[1]), np.deg2rad(ta11_list[1]))
y012_leo1 = np.hstack((r12_vec_leo1, v12_vec_leo1))
r12_vec_leo2, v12_vec_leo2 = of.COEs2ECI(np.linalg.norm(h1_list[0]), np.linalg.norm(e0_list[0]), np.deg2rad(inc0_list[0]), np.deg2rad(raan0_list[0]), np.deg2rad(argp0_list[0]), np.deg2rad(ta11_list[0]))
y012_leo2 = np.hstack((r12_vec_leo2, v12_vec_leo2))

# Porkchop plot
valid_dep_and_arr2 = of.lamberts_porkchop(y012_leo1, y012_leo2, t1_max=2.5*3600, t2_max=8*3600, t_step=300)
lambert2 = valid_dep_and_arr2[0]

#---------------------------- PROPAGATE LAMBERT TO LEO 2 ----------------------------#

# Time until lambert departure
dt_13 = lambert2["t1_sec"]

# Propagation Values
tspan_13 = [0.0, dt_13] # to lambert departure
t_eval_13 = None           # ADD IN TVAL AT THE END

# Propagate orbits forward to lambert departure
y0_13_all, h13_list, e13_list, inc13_list, raan13_list, argp13_list, ta13_list = propagate_segments(
    y0_12_all, tspan_13, teval=t_eval_13
)

#---------------------------- PROPAGATE LAMBERT TO LEO 1 ----------------------------#

# Change in time through lambert transfer to LEO 1
dt_14 = (lambert2["t2_sec"] - lambert2["t1_sec"]) # SECONDS

# Propagation Values
tspan_14 = [0.0, dt_14]
t_eval_14 = None

# Propagate orbits through lambert transfer to LEO 1
y0_14_all, h14_list, e14_list, inc14_list, raan14_list, argp14_list, ta14_list = propagate_segments(
    y0_13_all, tspan_14, teval=t_eval_14
)

#---------------------------- PROPAGATE 5 PERIODS OF LEO 2 DEBRIS ----------------------------#

# Calculate 5 periods of MEO debris
T5_leo2 = T_list[0]*5   # seconds

# Propagation Values
tspan_15 = [0.0, T5_leo2] # 5 periods of LEO 2 debris
t_eval_15 = None           # ADD IN TVAL AT THE END

# Propagate orbits forward by 5 periods of GEO debris
y0_15_all, h15_list, e15_list, inc15_list, raan15_list, argp15_list, ta15_list = propagate_segments(
    y0_14_all, tspan_15, teval=t_eval_15
)

#-------------------------------- FULL DEBRIS PROPAGATION -----------------------------------#

# Total mission time
dt_total = T5_geo + dt_3 + dt_4 + dt_5 + dt_6 + dt_7 + dt_8 + T5_meo + dt_10 + dt_11 + T5_leo1 + dt_13 + dt_14 + T5_leo2

fps = 60
video_length = 60.0

def local_teval_for_stage(dt):
    frames_tot = int(round(fps * video_length))
    if dt <= 0:
        return np.array([0.0], dtype=float)          # zero-duration stage

    # guarantee at least 2 samples (start & end)
    n = max(2, int(round(frames_tot * (dt / dt_total))))
    t = np.linspace(0.0, float(dt), n, dtype=float)
    t[0] = 0.0
    t[-1] = float(dt)
    return t

# Propagation values
tspan_total = [0.0, dt_total]
dt_step = 60.0
teval_global = np.arange(0.0, dt_total+dt_step, dt_step)

# Propagation
#y0_tot_debris, _, _, _, _, _, _ = propagate_segments(
#    y0_1_all, tspan=tspan_total, teval=teval_global
#)

#---------------------------- SPACECRAFT PROPAGATION --------------------------------#

#--------- 1 to 4 ----------#

# Spacecraft follows the same trajectory as titan from start of mission until inc and raan change
dt_1_4_sc = T5_geo + dt_3 + dt_4

# Propagation values
tspan_1_4 = [0.0, dt_1_4_sc]
teval_1_4_sc = local_teval_for_stage(dt_1_4_sc)

# Propagation
y0_1_4_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_1_all[3]], tspan=tspan_1_4, teval=teval_1_4_sc
)

#----------- 5 ------------#

# Spacecraft after the inc raan
dt_5_sc = dt_5

# Propagation values
tspan_5_sc = [0.0, dt_5_sc]
teval_5_sc = local_teval_for_stage(dt_5_sc)

# Propagation
y0_5_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [ECI_circ_sc], tspan=tspan_5_sc, teval=teval_5_sc
)

#----------- 6 -----------#

# Spacecraft during hohmann transfer
dt_6_sc = dt_6
y0_6_sc = np.hstack((ra_h_t, v_vec_a_ht))

# Propagation values
tspan_6_sc = [0.0, dt_6_sc]
teval_6_sc = local_teval_for_stage(dt_6_sc)

# Propagation
y0_6_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_6_sc], tspan=tspan_6_sc, teval=teval_6_sc
)

#----------- 7 ------------#

# Spacecraft moving to perigee of MEO
dt_7_sc = dt_7
r7_sc, v7_sc = of.COEs2ECI(np.linalg.norm(h0_list[2]), np.linalg.norm(e0_list[2]), inc0_list[2], raan0_list[2], argp0_list[2], np.deg2rad(180))
y0_7_sc = np.hstack((r7_sc, v7_sc))

# Propagation values
tspan_7_sc = [0.0, dt_7_sc]
teval_7_sc = local_teval_for_stage(dt_7_sc)

# Propagation
y0_7_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_7_sc], tspan=tspan_7_sc, teval=teval_7_sc
)

#----------- 8 ----------#
                                                                                                                                                                                                                                       
# Spacecraft in phasing orbit
dt_8_sc = dt_8
rp_8_sc = rp_7_vec
vp_8_sc = vp_7_vec + delv_h_arrival_vec
y0_8_sc = np.hstack((rp_8_sc, vp_8_sc))

# Propagation values
tspan_8_sc = [0.0, dt_8_sc]
teval_8_sc = local_teval_for_stage(dt_8_sc)

# Propagation
y0_8_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_8_sc], tspan=tspan_8_sc, teval=teval_8_sc
)

#------------ 9 to 10 ------------#

# 5 orbits of MEO and coasting to lambert 1 departure
dt_9_10_sc = T5_meo + dt_10

# Propagation values
tspan_9_10_sc = [0.0, dt_9_10_sc]
teval_9_10_sc = local_teval_for_stage(dt_9_10_sc)

# Propagation
y0_9_10_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_9_all[2][0:6, 0]], tspan=tspan_9_10_sc, teval=teval_9_10_sc
)

#---------------- 11 ----------------#

# Lambert 1 transfer
dt_11_sc = dt_11
y0_11_sc = np.hstack((lambert1["r_depart_km"], lambert1["v_depart_transfer_kms"]))

# Propagation values
tspan_11_sc = [0.0, dt_11_sc]
teval_11_sc = local_teval_for_stage(dt_11_sc)

# Propagation
y0_11_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_11_sc], tspan=tspan_11_sc, teval=teval_11_sc
)

#---------------- 12 to 13 -----------------#

# Lambert arrival, 5 periods of LEO1, and coast to lambert 2 departure
dt_12_13_sc = T5_leo1 + dt_13

# Propagation values
tspan_12_13_sc = [0.0, dt_12_13_sc]
teval_12_13_sc = local_teval_for_stage(dt_12_13_sc)

# Propagation
y0_12_13_sc_prop, _, _, _, _, _ , _ = propagate_segments(
    [y0_12_all[1][0:6, 0]], tspan=tspan_12_13_sc, teval=teval_12_13_sc
)

#---------------- 14 ----------------#

# Lambert 2 transfer
dt_14_sc = dt_14
y0_12_sc = np.hstack((lambert2["r_depart_km"], lambert2["v_depart_transfer_kms"]))

# Propagation values
tspan_14_sc = [0.0, dt_14_sc]
teval_14_sc = local_teval_for_stage(dt_14_sc)

# Propagation
y0_14_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_12_sc], tspan=tspan_14_sc, teval=teval_14_sc
)

#----------------- 15 -------------------#

# 5 Periods of LEO 2
dt_15_sc = T5_leo2

# Propagation values
tspan_15_sc = [0.0, dt_15_sc]
teval_15_sc = local_teval_for_stage(dt_15_sc)

# Propagation
y0_15_sc_prop, _, _, _, _, _, _ = propagate_segments(
    [y0_15_all[0][0:6, 0]], tspan=tspan_15_sc, teval=teval_15_sc
)


sc_segments = [
    y0_1_4_sc_prop[0], y0_5_sc_prop[0], y0_6_sc_prop[0], y0_7_sc_prop[0], y0_8_sc_prop[0],
    y0_9_10_sc_prop[0], y0_11_sc_prop[0], y0_12_13_sc_prop[0], y0_14_sc_prop[0], y0_15_sc_prop[0]
]

y0_hohmann = np.hstack((y0_7_sc_prop[0], y0_8_sc_prop[0], y0_9_10_sc_prop[0]))

of.plot_orbit(y0_hohmann, "PHASING ORBIT")