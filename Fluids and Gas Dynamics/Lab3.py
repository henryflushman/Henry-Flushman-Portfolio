""" LAB 3: Thermocouples """

# --- Imports -----------------------------
import numpy as np
import matplotlib.pyplot as plt
import os
# -----------------------------------------
###########################################
# --- Load Data .txt File -----------------
# Variable constructor helper function
def VarsFromData(dataName, tcLabel="T1", dropMissing=True):
    data = np.genfromtxt(
        dataName,
        delimiter='\t',
        dtype=str,
        encoding="utf-16",
        autostrip=True
    )

    tList = []
    TList = []

    if data.ndim == 1:
        data = data.reshape(1, -1)

    for row in data:
        if row.size < 4:
            continue
        if row[0] != tcLabel:
            continue

        try:
            t = float(row[1])
        except ValueError:
            continue

        T_str = row[3].strip() if row[3] is not None else ""
        if T_str == "":
            if dropMissing:
                continue
            T = np.nan
        else:
            try:
                T = float(T_str)
            except ValueError:
                if dropMissing:
                    continue
                T = np.nan

        tList.append(t)
        TList.append(T)

    return np.array(tList, dtype=float), np.array(TList, dtype=float)

# Helper: steady-state average over a chosen time/sample window
def SteadyAvg(t, T, t_start, t_end):
    mask = (t >= t_start) & (t <= t_end)
    return np.mean(T[mask]), np.std(T[mask], ddof=1), mask
# -----------------------------------------
###########################################
# --- Load and save data to assigned variables

# Boiling callibration
t_T1_callibration_boil, T_T1_callibration_boil = VarsFromData('Lab3_data/BoilingWaterTC_Callibration.dat', tcLabel="T1")
t_T2_callibration_boil, T_T2_callibration_boil = VarsFromData('Lab3_data/BoilingWaterTC_Callibration.dat', tcLabel="T2")

# Freezing callibration
t_T1_callibration_freeze, T_T1_callibration_freeze = VarsFromData('Lab3_data/IceWaterTC_Callibration.dat', tcLabel="T1")
t_T2_callibration_freeze, T_T2_callibration_freeze = VarsFromData('Lab3_data/IceWaterTC_Callibration.dat', tcLabel="T2")

# Aluminum rod
t_T1_aluminum, T_T1_aluminum = VarsFromData('Lab3_data/06_aluminum_hot_cold.dat', tcLabel="T1")
t_T2_aluminum, T_T2_aluminum = VarsFromData('Lab3_data/06_aluminum_hot_cold.dat', tcLabel="T2")

# Copper rod  (you used T3 in your file)
t_T1_copper, T_T1_copper = VarsFromData('Lab3_data/06_copper_hot_cold.dat', tcLabel="T1")
t_T2_copper, T_T2_copper = VarsFromData('Lab3_data/06_copper_hot_cold.dat', tcLabel="T3")

# Steel rod (you used T3 in your file)
t_T1_steel, T_T1_steel = VarsFromData('Lab3_data/06_steel_hot_cold.dat', tcLabel="T1")
t_T2_steel, T_T2_steel = VarsFromData('Lab3_data/06_steel_hot_cold.dat', tcLabel="T3")
# -----------------------------------------
###########################################
# --- Checking Callibration Data ----------

boilT1 = plt.subplot(2, 1, 1)
boilT1.plot(t_T1_callibration_boil, T_T1_callibration_boil, 'black', label='TC1')
boilT1.axvline(9, linestyle='--', color='black')
boilT1.axvline(19, linestyle='--', color='black')
boilT1.axvline(7, linestyle='--', color='black')
boilT1.axvspan(9, 19, color='red', alpha=0.3, label='Steady State')
boilT1.axvspan(7, 9, color='green', alpha=0.3, label='Reaching Steady State')
plt.ylabel('Temperature [F]')
plt.title('Boiling Callibration')
plt.legend()

boilT2 = plt.subplot(2, 1, 2)
boilT2.plot(t_T2_callibration_boil, T_T2_callibration_boil, 'black', label='TC2')
boilT2.axvline(25, linestyle='--', color='black')
boilT2.axvline(34, linestyle='--', color='black')
boilT2.axvline(22, linestyle='--', color='black')
boilT2.axvspan(25, 34, color='blue', alpha=0.3, label='Steady State')
boilT2.axvspan(22, 25, color='green', alpha=0.3, label='Reaching Steady State')
plt.ylabel('Temperature [F]')
plt.xlabel('Time [s]')
plt.legend()
plt.show()

freezeT1 = plt.subplot(2, 1, 1)
freezeT1.plot(t_T1_callibration_freeze, T_T1_callibration_freeze, 'black', label='TC1')
freezeT1.axvline(7, linestyle='--', color='black')
freezeT1.axvline(16, linestyle='--', color='black')
freezeT1.axvline(5, linestyle='--', color='black')
freezeT1.axvspan(7, 16, color='red', alpha=0.3, label='Steady State')
freezeT1.axvspan(5, 7, color='green', alpha=0.3, label='Reaching Steady State')
plt.ylabel('Temperature [F]')
plt.title('Freezing Callibration')
plt.legend()

freezeT2 = plt.subplot(2, 1, 2)
freezeT2.plot(t_T2_callibration_freeze, T_T2_callibration_freeze, 'black', label='TC2')
freezeT2.axvline(20, linestyle='--', color='black')
freezeT2.axvline(30, linestyle='--', color='black')
freezeT2.axvline(17, linestyle='--', color='black')
freezeT2.axvspan(20, 30, color='blue', alpha=0.3, label='Steady State')
freezeT2.axvspan(17, 20, color='green', alpha=0.3, label='Reaching Steady State')
plt.ylabel('Temperature [F]')
plt.xlabel('Time [s]')
plt.legend()
plt.show()

# -----------------------------------------
# --- CALIBRATION steady-state averages (using YOUR chosen windows)

boilActual = 212.0
freezeActual = 32.0

T1_boil_avg, T1_boil_std, _ = SteadyAvg(t_T1_callibration_boil,   T_T1_callibration_boil,   9, 19)
T2_boil_avg, T2_boil_std, _ = SteadyAvg(t_T2_callibration_boil,   T_T2_callibration_boil,   25, 34)

T1_freeze_avg, T1_freeze_std, _ = SteadyAvg(t_T1_callibration_freeze, T_T1_callibration_freeze, 7, 16)
T2_freeze_avg, T2_freeze_std, _ = SteadyAvg(t_T2_callibration_freeze, T_T2_callibration_freeze, 20, 30)

print("\n===== CALIBRATION RESULTS (STEADY-STATE AVG) =====")

print("\nBoiling Water (212°F)")
print(f"T1 Avg: {T1_boil_avg:.2f} °F (std {T1_boil_std:.2f}) | Error: {T1_boil_avg - boilActual:.2f} °F")
print(f"T2 Avg: {T2_boil_avg:.2f} °F (std {T2_boil_std:.2f}) | Error: {T2_boil_avg - boilActual:.2f} °F")

print("\nIce Water (32°F)")
print(f"T1 Avg: {T1_freeze_avg:.2f} °F (std {T1_freeze_std:.2f}) | Error: {T1_freeze_avg - freezeActual:.2f} °F")
print(f"T2 Avg: {T2_freeze_avg:.2f} °F (std {T2_freeze_std:.2f}) | Error: {T2_freeze_avg - freezeActual:.2f} °F")

# ------------------------------------------
############################################
# --- Sample steady-state averages (using YOUR partitions)

# Your partitions:
# Aluminum boiling: 15..410, freezing: 580..820
# Copper   boiling: 0..220,  freezing: 230..680
# Steel    boiling: 10..245, freezing: 260..500

# Aluminum
al_boil_start, al_boil_end = 50, 300
al_freeze_start, al_freeze_end = 620, 820
Al_T1_boil_avg,  Al_T1_boil_std,  _ = SteadyAvg(t_T1_aluminum, T_T1_aluminum, al_boil_start, al_boil_end)
Al_T2_boil_avg,  Al_T2_boil_std,  _ = SteadyAvg(t_T2_aluminum, T_T2_aluminum, al_boil_start, al_boil_end)
Al_T1_free_avg,  Al_T1_free_std,  _ = SteadyAvg(t_T1_aluminum, T_T1_aluminum, al_freeze_start, al_freeze_end)
Al_T2_free_avg,  Al_T2_free_std,  _ = SteadyAvg(t_T2_aluminum, T_T2_aluminum, al_freeze_start, al_freeze_end)

# Copper
cu_boil_start, cu_boil_end = 0, 215
cu_freeze_start, cu_freeze_end = 290, 450
Cu_T1_boil_avg,  Cu_T1_boil_std,  _ = SteadyAvg(t_T1_copper, T_T1_copper, cu_boil_start, cu_boil_end)
Cu_T2_boil_avg,  Cu_T2_boil_std,  _ = SteadyAvg(t_T2_copper, T_T2_copper, cu_boil_start, cu_boil_end)
Cu_T1_free_avg,  Cu_T1_free_std,  _ = SteadyAvg(t_T1_copper, T_T1_copper, cu_freeze_start, cu_freeze_end)
Cu_T2_free_avg,  Cu_T2_free_std,  _ = SteadyAvg(t_T2_copper, T_T2_copper, cu_freeze_start, cu_freeze_end)

# Steel
st_boil_start, st_boil_end = 10, 245
st_freeze_start, st_freeze_end = 330, 500
St_T1_boil_avg,  St_T1_boil_std,  _ = SteadyAvg(t_T1_steel, T_T1_steel, st_boil_start, st_boil_end)
St_T2_boil_avg,  St_T2_boil_std,  _ = SteadyAvg(t_T2_steel, T_T2_steel, st_boil_start, st_boil_end)
St_T1_free_avg,  St_T1_free_std,  _ = SteadyAvg(t_T1_steel, T_T1_steel, st_freeze_start, st_freeze_end)
St_T2_free_avg,  St_T2_free_std,  _ = SteadyAvg(t_T2_steel, T_T2_steel, st_freeze_start, st_freeze_end)

print("\n===== SAMPLE RESULTS (STEADY-STATE AVG) =====")

print("\nAluminum:")
print(f"  Boiling:  T1 {Al_T1_boil_avg:.2f}±{Al_T1_boil_std:.2f} °F | T2 {Al_T2_boil_avg:.2f}±{Al_T2_boil_std:.2f} °F")
print(f"  Freezing: T1 {Al_T1_free_avg:.2f}±{Al_T1_free_std:.2f} °F | T2 {Al_T2_free_avg:.2f}±{Al_T2_free_std:.2f} °F")

print("\nCopper:")
print(f"  Boiling:  T1 {Cu_T1_boil_avg:.2f}±{Cu_T1_boil_std:.2f} °F | T2 {Cu_T2_boil_avg:.2f}±{Cu_T2_boil_std:.2f} °F")
print(f"  Freezing: T1 {Cu_T1_free_avg:.2f}±{Cu_T1_free_std:.2f} °F | T2 {Cu_T2_free_avg:.2f}±{Cu_T2_free_std:.2f} °F")

print("\nSteel:")
print(f"  Boiling:  T1 {St_T1_boil_avg:.2f}±{St_T1_boil_std:.2f} °F | T2 {St_T2_boil_avg:.2f}±{St_T2_boil_std:.2f} °F")
print(f"  Freezing: T1 {St_T1_free_avg:.2f}±{St_T1_free_std:.2f} °F | T2 {St_T2_free_avg:.2f}±{St_T2_free_std:.2f} °F")

# ------------------------------------------
############################################

# Masks for plots (reuse your same partitions)
m_al_t1_boil  = (t_T1_aluminum >= al_boil_start) & (t_T1_aluminum <= al_boil_end)
m_al_t2_boil  = (t_T2_aluminum >= al_boil_start) & (t_T2_aluminum <= al_boil_end)
m_al_t1_freez = (t_T1_aluminum >= al_freeze_start) & (t_T1_aluminum <= al_freeze_end)
m_al_t2_freez = (t_T2_aluminum >= al_freeze_start) & (t_T2_aluminum <= al_freeze_end)

m_cu_t1_boil  = (t_T1_copper >= cu_boil_start) & (t_T1_copper <= cu_boil_end)
m_cu_t2_boil  = (t_T2_copper >= cu_boil_start) & (t_T2_copper <= cu_boil_end)
m_cu_t1_freez = (t_T1_copper >= cu_freeze_start) & (t_T1_copper <= cu_freeze_end)
m_cu_t2_freez = (t_T2_copper >= cu_freeze_start) & (t_T2_copper <= cu_freeze_end)

m_st_t1_boil  = (t_T1_steel >= st_boil_start) & (t_T1_steel <= st_boil_end)
m_st_t2_boil  = (t_T2_steel >= st_boil_start) & (t_T2_steel <= st_boil_end)
m_st_t1_freez = (t_T1_steel >= st_freeze_start) & (t_T1_steel <= st_freeze_end)
m_st_t2_freez = (t_T2_steel >= st_freeze_start) & (t_T2_steel <= st_freeze_end)

# --- Final Plots: TWO SEPARATE FIGURES (Boiling + Freezing), aligned start time ---
# (All lines black, bigger markers; shapes encode material)

def plot_segment(ax, t, T, mask, marker, label, markevery=25, msize=11):
    t_seg = t[mask]
    T_seg = T[mask]
    if t_seg.size == 0:
        return

    t_rel = t_seg - t_seg[0]

    ax.plot(
        t_rel,
        T_seg,
        linestyle='-',
        marker=marker,
        color='k',
        linewidth=2,
        markersize=msize,
        markevery=markevery,
        label=label
    )

# ------------------- BOILING FIGURE -------------------
fig_boil = plt.figure(figsize=(13, 6))
ax_boil = plt.gca()

plot_segment(ax_boil, t_T1_aluminum, T_T1_aluminum, m_al_t1_boil, '^', 'Aluminum T1', markevery=25, msize=5)
plot_segment(ax_boil, t_T2_aluminum, T_T2_aluminum, m_al_t2_boil, '^', 'Aluminum T2', markevery=25, msize=5)

plot_segment(ax_boil, t_T1_copper,   T_T1_copper,   m_cu_t1_boil, 'o', 'Copper T1',   markevery=25, msize=5)
plot_segment(ax_boil, t_T2_copper,   T_T2_copper,   m_cu_t2_boil, 'o', 'Copper T2',   markevery=25, msize=5)

plot_segment(ax_boil, t_T1_steel,    T_T1_steel,    m_st_t1_boil, 's', 'Steel T1',    markevery=25, msize=5)
plot_segment(ax_boil, t_T2_steel,    T_T2_steel,    m_st_t2_boil, 's', 'Steel T2',    markevery=25, msize=5)

ax_boil.set_title('Boiling — All Samples (time aligned to start at 0)')
ax_boil.set_xlabel('Time since start of segment [s]')
ax_boil.set_ylabel('Temperature [F]')
ax_boil.grid(True, alpha=0.3)
ax_boil.legend(ncol=3, fontsize=9)

plt.tight_layout()
plt.show()

# ------------------- FREEZING FIGURE -------------------
fig_freeze = plt.figure(figsize=(13, 6))
ax_freeze = plt.gca()

plot_segment(ax_freeze, t_T1_aluminum, T_T1_aluminum, m_al_t1_freez, '^', 'Aluminum T1', markevery=20, msize=5)
plot_segment(ax_freeze, t_T2_aluminum, T_T2_aluminum, m_al_t2_freez, '^', 'Aluminum T2', markevery=20, msize=5)

plot_segment(ax_freeze, t_T1_copper,   T_T1_copper,   m_cu_t1_freez, 'o', 'Copper T1',   markevery=20, msize=5)
plot_segment(ax_freeze, t_T2_copper,   T_T2_copper,   m_cu_t2_freez, 'o', 'Copper T2',   markevery=20, msize=5)

plot_segment(ax_freeze, t_T1_steel,    T_T1_steel,    m_st_t1_freez, 's', 'Steel T1',    markevery=20, msize=5)
plot_segment(ax_freeze, t_T2_steel,    T_T2_steel,    m_st_t2_freez, 's', 'Steel T2',    markevery=20, msize=5)

ax_freeze.set_title('Freezing — All Samples (time aligned to start at 0)')
ax_freeze.set_xlabel('Time since start of segment [s]')
ax_freeze.set_ylabel('Temperature [F]')
ax_freeze.grid(True, alpha=0.3)
ax_freeze.legend(ncol=3, fontsize=9)

plt.tight_layout()
plt.show()

# ---------------------

steel_D = 0.629/100   # m
copper_D = 0.640/100  # m
alum_D  = 0.633/100   # m

steel_A = (np.pi/4)*steel_D**2
copper_A = (np.pi/4)*copper_D**2
alum_A = (np.pi/4)*alum_D**2

# -------------------- Convection + Heat Rate Calculations --------------------

def F_to_K(TF):
    return (TF - 32.0) * (5/9) + 273.15

def calc_h_natural(Ts_F, Tinf_F, Lc, Pr=0.71, k_air=0.028, nu=1.7e-5):
    """
    Natural convection h using: Nu = 0.59*(Gr*Pr)^(1/4)
    Air properties are approximations at ~300-350K:
      k_air ~ 0.028 W/m-K
      nu    ~ 1.7e-5 m^2/s
    Use your lab's property table if you have one.
    """
    g = 9.81

    Ts = F_to_K(Ts_F)
    Tinf = F_to_K(Tinf_F)
    Tf = 0.5*(Ts + Tinf)           # film temp [K]
    beta = 1.0 / Tf                # 1/K (ideal gas)

    Gr = g * beta * (Ts - Tinf) * (Lc**3) / (nu**2)
    Ra = abs(Gr) * Pr
    Nu = 0.59 * (Ra**0.25)

    h = Nu * k_air / Lc
    return h, Gr, Nu

def calc_q_for_rod(T1_avg_F, T2_avg_F, Tinf_F, k_rod, D_rod, L_rod, Lc=0.1524):
    """
    Uses your screenshot equations:
      Rcond = L/(kA)
      Rconv = 1/(2π r L h)
      q = (Thot - Tcold)/(Rcond + Rconv)
    """
    # Choose hot/cold automatically from the two thermocouples
    Thot_F = max(T1_avg_F, T2_avg_F)
    Tcold_F = min(T1_avg_F, T2_avg_F)

    # Surface temperature estimate for convection
    Ts_F = 0.5*(T1_avg_F + T2_avg_F)

    # Convection coefficient
    h, Gr, Nu = calc_h_natural(Ts_F, Tinf_F, Lc)

    # Areas / resistances
    A_cross = (np.pi/4) * D_rod**2
    r = D_rod/2
    Rcond = L_rod / (k_rod * A_cross)
    Rconv = 1.0 / (2*np.pi*r*L_rod*h)

    # Heat transfer rate (W)
    q = (Thot_F - Tcold_F) / (Rcond + Rconv)

    return {
        "Thot_F": Thot_F,
        "Tcold_F": Tcold_F,
        "Ts_F": Ts_F,
        "h": h,
        "Gr": Gr,
        "Nu": Nu,
        "Rcond": Rcond,
        "Rconv": Rconv,
        "q": q
    }

# ---- Ambient given in your screenshot ----
Tinf_F = 130.0
Lc = 0.1524  # 7 inches in meters

# ---- Make sure diameters are in meters! ----
steel_D = 0.629/100
copper_D = 0.640/100
alum_D  = 0.633/100

# ---- Your k values (W/m-K) ----
steel_cond  = 43.0
copper_cond = 399.0
alum_cond   = 237.0

# ---- Your rod lengths (m) ----
L_steel  = 0.249
L_copper = 0.2413
L_alum   = 0.24484

# -------------------- Use YOUR steady-state averages --------------------
# Example: Aluminum boiling segment averages you already computed:
#   Al_T1_boil_avg, Al_T2_boil_avg, etc.

al_boil = calc_q_for_rod(Al_T1_boil_avg, Al_T2_boil_avg, Tinf_F, alum_cond, alum_D, L_alum, Lc=Lc)
cu_boil = calc_q_for_rod(Cu_T1_boil_avg, Cu_T2_boil_avg, Tinf_F, copper_cond, copper_D, L_copper, Lc=Lc)
st_boil = calc_q_for_rod(St_T1_boil_avg, St_T2_boil_avg, Tinf_F, steel_cond, steel_D, L_steel, Lc=Lc)

al_free = calc_q_for_rod(Al_T1_free_avg, Al_T2_free_avg, Tinf_F, alum_cond, alum_D, L_alum, Lc=Lc)
cu_free = calc_q_for_rod(Cu_T1_free_avg, Cu_T2_free_avg, Tinf_F, copper_cond, copper_D, L_copper, Lc=Lc)
st_free = calc_q_for_rod(St_T1_free_avg, St_T2_free_avg, Tinf_F, steel_cond, steel_D, L_steel, Lc=Lc)

def print_results(name, res):
    print(f"\n--- {name} ---")
    print(f"Thot = {res['Thot_F']:.2f} F,  Tcold = {res['Tcold_F']:.2f} F,  Ts ~ {res['Ts_F']:.2f} F")
    print(f"Gr = {res['Gr']:.3e},  Nu = {res['Nu']:.3f},  h = {res['h']:.3f} W/m^2-K")
    print(f"Rcond = {res['Rcond']:.6f} K/W,  Rconv = {res['Rconv']:.6f} K/W")
    print(f"q = {res['q']:.3f} W")

print_results("Aluminum (Boiling segment)", al_boil)
print_results("Copper   (Boiling segment)", cu_boil)
print_results("Steel    (Boiling segment)", st_boil)

print_results("Aluminum (Freezing segment)", al_free)
print_results("Copper   (Freezing segment)", cu_free)
print_results("Steel    (Freezing segment)", st_free)