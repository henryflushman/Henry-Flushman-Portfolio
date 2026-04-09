# Imports
import Orbits.Orbits_Functions as of
import numpy as np
import matplotlib.pyplot as plt
import pyvista as pv
import os

os.system('cls')

# Constants
mu_s    = 1.32712e11
mu_e    = 398600
mu_v    = 324859
r_e     = 6378
r_v     = 6052

""" -------------------- Problem One --------------------- """

# Timing
t_i = of.julian_date(2026, 1, 1, 0, 0, 0, False)*86400
t_f1 = of.julian_date(2026, 9, 1, 0, 0, 0, False)*86400
t_f2 = of.julian_date(2026, 10, 1, 0, 0, 0, False)*86400
t_f3 = of.julian_date(2026, 11, 1, 0, 0, 0, False)*86400

dt1 = (t_f1 - t_i)
dt2 = (t_f2 - t_i)
dt3 = (t_f3 - t_i)

# R and V vectors
r_i, v_i = of.date_to_planet_rv(3, 2026, 1, 1, 0, 0, 0)
r_vi, v_vi = of.date_to_planet_rv(2, 2026, 1, 1, 0, 0, 0)
r_f1, v_f1 = of.date_to_planet_rv(2, 2026, 9, 1, 0, 0, 0)
r_f2, v_f2 = of.date_to_planet_rv(2, 2026, 10, 1, 0, 0, 0)
r_f3, v_f3 = of.date_to_planet_rv(2, 2026, 11, 1, 0, 0, 0)

# Departure and Arrival velocities
def vinf_of_lamberts(r_i, r_f, v_i, v_f, dt, label=""):
    # SHORT WAY
    try:
        v_i_s, v_f_s, _ = of.lamberts(r_i, r_f, dt, prograde=True, max_iter=25, tol=1e-8, mu=mu_s)
        vinf_i_s = v_i_s - v_i
        vinf_f_s = v_f_s - v_f
        short_way = np.array([v_i_s, v_f_s, vinf_i_s, vinf_f_s])
    except ValueError as e:
        print(f"[{label} | short] Lambert error:", e)
        short_way = np.full((4, 1), np.nan)
    # LONG WAY
    try:
        v_i_l, v_f_l, _ = of.lamberts(r_i, r_f, dt, prograde=False, max_iter=25, tol=1e-8, mu=mu_s)
        vinf_i_l = v_i_l - v_i
        vinf_f_l = v_f_l - v_f
        long_way = np.array([v_i_l, v_f_l, vinf_i_l, vinf_f_l])
    except ValueError as e:
        print(f"[{label} : long] Lambert error:", e)
        long_way = np.full((4, 1), np.nan)

    return short_way, long_way
    
lamb1_s, lamb1_l = vinf_of_lamberts(r_i, r_f1, v_i, v_f1, dt1, "lamberts1")
lamb2_s, lamb2_l = vinf_of_lamberts(r_i, r_f2, v_i, v_f2, dt2, "lamberts2")
lamb3_s, lamb3_l = vinf_of_lamberts(r_i, r_f3, v_i, v_f3, dt3, "lamberts3")

# Parking Orbit in Earth
r_park = r_e + 500
v_park = np.sqrt(mu_e/r_park)

# Venus Orbit
ra_v = r_v + 10000
rp_v = r_v + 2000
a_v = (ra_v+rp_v)/2
vp_v = np.sqrt(mu_v*(2/rp_v - 1/a_v))

# Delta v calculations
def dv_calc(vinf_i, vinf_f):
    vp_hyp_e = np.sqrt(np.linalg.norm(vinf_i)**2+(2*mu_e)/r_park)
    vp_hyp_v = np.sqrt(np.linalg.norm(vinf_f)**2+(2*mu_v)/rp_v)
    dv1 = vp_hyp_e - v_park
    dv2 = vp_hyp_v - vp_v
    return dv1 + dv2

dv1_s = dv_calc(lamb1_s[2], lamb1_s[3])
dv1_l = dv_calc(lamb1_l[2], lamb1_l[3])

dv2_s = dv_calc(lamb2_s[2], lamb2_s[3])
dv2_l = dv_calc(lamb2_l[2], lamb2_l[3])

dv3_s = dv_calc(lamb3_s[2], lamb3_s[3])
dv3_l = dv_calc(lamb3_l[2], lamb3_l[3])

dvs = [dv1_s, dv2_s, dv3_s]
dvl = [dv1_l, dv2_l, dv3_l]
labels = ['Sept.', 'Oct.', 'Nov.']

for s, l, date in zip(dvs, dvl, labels):
    print(f"Delta V required to arrive on {date} 1 - \nShort Way: {s:.2f} km/s\nLong Way: {l:.2f}km/s")
    
""" ------------------------------------------------ PLOTTING -------------------------------------------------- """

plotting =  input("Would you like to plot? [type y] : ")

if plotting == "y":
    # Planetary and Spacecraft Propagations
    def store_rvec_prop(ti, tf, r, v):
        tspan = [ti, tf]
        sol = of.ODEprimer(r, v, tspan, None, mu=mu_s)
        return sol.y[0:3,:].T

    rprop_e = store_rvec_prop(t_i, t_i+365*24*60*60, r_i, v_i)
    rprop_v = store_rvec_prop(t_i, t_i+365*24*60*60, r_vi, v_vi)
    rprop_sc1 = store_rvec_prop(t_i, t_f1, r_i, lamb1_s[0])
    rprop_sc2 = store_rvec_prop(t_i, t_f2, r_i, lamb2_s[0])
    rprop_sc3 = store_rvec_prop(t_i, t_f3, r_i, lamb3_s[0])


    # Turning propagations to trajectory lines
    traj_e = pv.lines_from_points(rprop_e)
    traj_v = pv.lines_from_points(rprop_v)
    traj_sc1 = pv.lines_from_points(rprop_sc1)
    traj_sc2 = pv.lines_from_points(rprop_sc2)
    traj_sc3 = pv.lines_from_points(rprop_sc3)

    # Plot initializing
    ps = pv.Plotter()
    cubemap = pv.examples.download_cubemap_space_4k()
    _ = ps.add_actor(cubemap.to_skybox())
    ps.set_environment_texture(cubemap, is_srgb=True)

    # Adding stellar body mesh
    # Sun
    sun = pv.examples.planets.load_sun(radius=696000*15)
    sun.translate((0., 0., 0.), inplace=True)
    sun_tex = pv.examples.planets.download_sun_surface(texture=True)
    ps.add_mesh(sun, texture=sun_tex, smooth_shading=True, emissive=True)

    # Earth
    earth = pv.examples.planets.load_earth(radius=6378*100*8)
    earth.translate(rprop_e[-1,:], inplace=True)
    earth_tex = pv.examples.load_globe_texture()
    ps.add_mesh(earth, texture=earth_tex, smooth_shading=True)

    # Venus
    venus = pv.examples.planets.load_venus(radius=r_v*100*8)
    venus.translate(rprop_v[-1,:], inplace=True)
    venus_tex = pv.examples.planets.download_venus_surface(texture=True)
    ps.add_mesh(venus, texture=venus_tex, smooth_shading=True)

    # Trajectories
    ps.add_mesh(traj_e, color='white')
    ps.add_mesh(traj_v, color='white')
    ps.add_mesh(traj_sc1, color='yellow')
    ps.add_mesh(traj_sc2, color='green')
    ps.add_mesh(traj_sc3, color='red')

    # Departure and Arrival Locations
    ps.add_point_labels(
        points=[rprop_e[0], rprop_sc1[-1], rprop_sc2[-1], rprop_sc3[-1]],
        labels=["Departure", "Arrival 1", "Arrival 2", "Arrival 3"],
        point_size=20,
        shape_opacity=0.4,
        text_color="White"
    )

    sun_light = pv.Light(
        light_type='scene light',
        color='white',
        intensity=2.0,
        position=(0,0,0),
    )
    sun_light.positional = True          # make it a point light
    ps.add_light(sun_light)

    ps.show()


    #----------------------------------- Long Way ---------------------------------------#

    # Propagation
    rprop_sc1 = store_rvec_prop(t_i, t_f1, r_i, lamb1_l[0])
    rprop_sc2 = store_rvec_prop(t_i, t_f2, r_i, lamb2_l[0])
    rprop_sc3 = store_rvec_prop(t_i, t_f3, r_i, lamb3_l[0])

    # Turning propagations to trajectory lines
    traj_e = pv.lines_from_points(rprop_e)
    traj_v = pv.lines_from_points(rprop_v)
    traj_sc1 = pv.lines_from_points(rprop_sc1)
    traj_sc2 = pv.lines_from_points(rprop_sc2)
    traj_sc3 = pv.lines_from_points(rprop_sc3)

    # Plot initializing
    ps = pv.Plotter()
    cubemap = pv.examples.download_cubemap_space_4k()
    _ = ps.add_actor(cubemap.to_skybox())
    ps.set_environment_texture(cubemap, is_srgb=True)

    # Adding stellar body mesh
    # Sun
    sun = pv.examples.planets.load_sun(radius=696000*15)
    sun.translate((0., 0., 0.), inplace=True)
    sun_tex = pv.examples.planets.download_sun_surface(texture=True)
    ps.add_mesh(sun, texture=sun_tex, smooth_shading=True, emissive=True)

    # Earth
    earth = pv.examples.planets.load_earth(radius=6378*100*8)
    earth.translate(rprop_e[-1,:], inplace=True)
    earth_tex = pv.examples.load_globe_texture()
    ps.add_mesh(earth, texture=earth_tex, smooth_shading=True)

    # Venus
    venus = pv.examples.planets.load_venus(radius=r_v*100*8)
    venus.translate(rprop_v[-1,:], inplace=True)
    venus_tex = pv.examples.planets.download_venus_surface(texture=True)
    ps.add_mesh(venus, texture=venus_tex, smooth_shading=True)

    # Trajectories
    ps.add_mesh(traj_e, color='white')
    ps.add_mesh(traj_v, color='white')
    ps.add_mesh(traj_sc1, color='red')
    ps.add_mesh(traj_sc2, color='yellow')
    ps.add_mesh(traj_sc3, color='green')

    # Departure and Arrival Locations
    ps.add_point_labels(
        points=[rprop_e[0], rprop_sc1[-1], rprop_sc2[-1], rprop_sc3[-1]],
        labels=["Departure", "Arrival 1", "Arrival 2", "Arrival 3"],
        point_size=20,
        shape_opacity=0.4,
        text_color="White"
    )

    sun_light = pv.Light(
        light_type='scene light',
        color='white',
        intensity=2.0,
        position=(0,0,0),
    )
    sun_light.positional = True          # make it a point light
    ps.add_light(sun_light)

    ps.show()


os.system('cls')


"""---------------------- Problem 2 -----------------------"""

# Constants
T_sc = 284*24*60*60     # seconds
ra_sc = 149598000       # km
alt_p = 10000           # km


# Semi Major Axis
a_sc = (mu_s*(T_sc/(2*np.pi))**2)**(1/3)

# Vis Viva
v_sc = np.sqrt(mu_s*(2/ra_sc - 1/a_sc))

# Earth's Speed
v_e = np.sqrt(mu_s/ra_sc)

# Hyperbolic excess speed when Earth catches the spacecraft
vinf = v_e - v_sc

# Flyby around Earth
rp_sc = r_e + alt_p
ecc_sc = 1 + (rp_sc*vinf**2)/mu_e
delta = 2*np.arcsin(1/ecc_sc)

# Vector form
vvec_sc = np.array([v_sc, 0, 0])
vvec_e = np.array([v_e, 0, 0])
vinf1_vec = vvec_sc - vvec_e

# Finding phi 1
# Should be 180 as it is the angle between vinf1 
# and the velocity of the earth which are opposite from eachother
phi1 = np.deg2rad(180)

# Finding phi 2
phi2 = phi1 - delta

# Hyperbolic excess speed when leaving Earth
vinf2_vec = np.array([vinf*np.cos(phi2), vinf*np.sin(phi2), 0])

# Velocity of the spacecraft in Heliocentric frame
v2_sc = vvec_e + vinf2_vec

# Delta v
dvvec_sc = v2_sc - vvec_sc
dv_sc2 = np.linalg.norm(dvvec_sc)
print(f"The total change in velocity induced by the flyby is: {dv_sc2:.2f}")
input("Enter to continue:")


"""---------------------- Problem 3 -----------------------"""

os.system('cls')

# Constants
Isp = 5000                          # seconds
T = 6                               # N

# Initial values for burn 1
m1 = 600                            # kg
t_span_burn1 = [0, 2*24*60*60]      # seconds
rvec1 = np.array([16378, 0, 0])     # km
vvec1 = np.array([0, 4.9333, 0])    # km/s
y0_burn1 = np.hstack((rvec1, vvec1, m1))

# Propagate burn 1
sol_burn1 = of.burn_propagate(t_span_burn1, y0_burn1, T, Isp, in_v_dir=False)

# Initial values for coast
t_span_coast = [0, 24*60*60]        # seconds
r0_coast = sol_burn1.y[0:3,-1]      # km
v0_coast = sol_burn1.y[3:6,-1]      # km/s

# Propagate coast
sol_coast = of.ODEprimer(r0_coast, v0_coast, t_span_coast)

# Initial values for burn 2
m2 = sol_burn1.y[6,-1]              # kg
t_span_burn2 = [0, 1.1*24*60*60]    # seconds
rvec2 = sol_coast.y[0:3,-1]         # km
vvec2 = sol_coast.y[3:6,-1]         # km/s
y0_burn2 = np.hstack((rvec2, vvec2, m2))

# Propagate burn 2
sol_burn2 = of.burn_propagate(t_span_burn2, y0_burn2, T, Isp, in_v_dir=False)

# ECI to COEs of final trajectory
rvec_f = sol_burn2.y[0:3,-1]        # km
vvec_f = sol_burn2.y[3:6,-1]        # km/s
y0vec_f = np.hstack((rvec_f, vvec_f))
h_vec, ecc_vec, inc, RAAN, argp, TA = of.ECI2COEs(y0vec_f)

# Radius of perigee for final trajectory
h = np.linalg.norm(h_vec)           # km^3/s^2
ecc = np.linalg.norm(ecc_vec)
rp_f = h**2/(mu_e*(1+ecc))          # km
altp_f = rp_f - r_e

# Final mass
m_f = sol_burn2.y[6,-1]

# Final mass check
mdot = T/(Isp*9.80665)
mfinal_check = m1 - mdot*3.2*24*60*60

print(f"The altitude of perigee for the SpaceCrafts final trajectory is: {altp_f:.0f} km")
print(f"The final amount of fuel left is: {m_f:.0f} kg")

plotting =  input("Would you like to plot? [type y] : ")

if plotting == "y":
    rprop_tot = [sol_burn1.y, sol_coast.y, sol_burn2.y]
    labels = ["Burn 1", "Coast", "Burn 2"]
    colors = ["orange", "green", "red"]
    of.plot_orbit(rprop_tot, labels, colors)
    

"""---------------------- Problem 4 -----------------------"""

os.system('cls')

# Constants
r0 = np.array([-5959.72, -4338.9, 3992.93]) # km
v0 = np.array([4.20251, -4.4142, -0.58846]) # km/s
dt = 35*60                                  # seconds

rprop = of.UnAnom_propagator(r0, v0, dt, 15)
rprop = np.array(rprop)

r_f = np.linalg.norm(rprop[-1,0:3])
print(f"The position of the spacecraft at 35 minutes is: {r_f:.0f}")
print(np.linalg.norm(r0), np.linalg.norm(v0))

traj = pv.lines_from_points(rprop)

light = pv.Light()
light.set_direction_angle(30, -20)

ps = pv.Plotter()
cubemap = pv.examples.download_cubemap_space_4k()
_ = ps.add_actor(cubemap.to_skybox())
ps.set_environment_texture(cubemap, is_srgb=True)
ps.add_light(light)

# Earth
earth = pv.examples.planets.load_earth(radius=6378)
earth.translate((0,0,0), inplace=True)
earth_tex = pv.examples.load_globe_texture()
ps.add_mesh(earth, texture=earth_tex, smooth_shading=True)

# Trajectory
ps.add_mesh(traj, color='yellow')

ps.show()