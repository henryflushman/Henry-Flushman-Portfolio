"""
Solar system visualization using precomputed ephemeris chunks.

Updated speed controls:
 - Initial speed  = 1.0 day/sec
 - REAL_TIME      = 1 simulated second per real second == 1/86400 day/sec
 - speed_down halves positive speed until REAL_TIME, then flips to -REAL_TIME
 - speed_up doubles positive speed; when negative, reduces magnitude toward +REAL_TIME
GUI overlay shows speed (days/sec) and simulated seconds per real second (s/s).
"""
from __future__ import annotations
import time
import atexit
from typing import Optional

import numpy as np
import pyvista as pv

from Ephemeris_Cache import EphemerisCache, PLANET_NAMES

from datetime import datetime, timedelta

# ---------------- CONFIG ---------------- #
CHUNK_YEARS = 25.0
STEP_DAYS = 1.0
MAX_YEARS = 500.0

# INITIAL speed now 1 day / real second
INITIAL_SPEED_DAYS_PER_SEC = 1.0

# Real-time definition: 1 simulated second per real second
REAL_TIME_DAYS_PER_SEC = 1.0 / 86400.0

TIMER_INTERVAL_MS = 40     # UI update interval in ms (25 Hz)

# J2000 reference (same epoch used by Ephemeris_Cache)
J2000_DATETIME = datetime(2000, 1, 1, 12, 0, 0)

# ---------------- CREATE EPHEMERIS CACHE ---------------- #
ephem = EphemerisCache(
    chunk_years=CHUNK_YEARS,
    step_days=STEP_DAYS,
    cache_dir="ephem_cache",
    max_chunk_in_memory=3,
    max_years=MAX_YEARS,
    max_workers=1,
)
atexit.register(ephem.shutdown)

# ---------------- BACKGROUND PLOTTER DETECTION ---------------- #
BackgroundPlotter = None
USE_BACKGROUND = False

# 1) Prefer pyvistaqt's BackgroundPlotter (new location)
try:
    from pyvistaqt import BackgroundPlotter as _BP  # type: ignore
    BackgroundPlotter = _BP
    USE_BACKGROUND = True
    print("Using BackgroundPlotter from pyvistaqt.")
except Exception:
    # 2) If pyvistaqt not installed, try to access any BackgroundPlotter attribute on pyvista
    try:
        BackgroundPlotter = getattr(pv, "BackgroundPlotter", None)
        if BackgroundPlotter is not None:
            USE_BACKGROUND = True
            print("Using BackgroundPlotter from pyvista (legacy).")
    except Exception:
        BackgroundPlotter = None
        USE_BACKGROUND = False
        print("BackgroundPlotter not available from pyvista or pyvistaqt; falling back to pv.Plotter.")

# ---------------- PLOTTER CREATION and SCENE BUILDING ---------------- #
def build_scene(p: pv.Plotter):
    p.add_axes()
    # Sun
    sun = pv.Sphere(radius=0.15)
    p.add_mesh(sun, color="yellow", emissive=True)

    # Planet visuals (not to scale)
    planet_radii = {
        "Mercury": 0.01,
        "Venus":   0.02,
        "Earth":   0.02,
        "Mars":    0.015,
        "Jupiter": 0.05,
        "Saturn":  0.045,
        "Uranus":  0.03,
        "Neptune": 0.03,
    }
    planet_colors = {
        "Mercury": "gray",
        "Venus":   "tan",
        "Earth":   "deepskyblue",
        "Mars":    "red",
        "Jupiter": "orange",
        "Saturn":  "gold",
        "Uranus":  "cyan",
        "Neptune": "royalblue",
    }

    planet_actors_local = []
    for name in PLANET_NAMES:
        sphere = pv.Sphere(radius=planet_radii.get(name, 0.02))
        actor = p.add_mesh(sphere, color=planet_colors.get(name, "white"))
        planet_actors_local.append(actor)

    # Camera
    p.camera.position = (0, -12, 8)
    p.camera.focal_point = (0, 0, 0)
    p.camera.up = (0, 0, 1)

    return planet_actors_local

# Create plotter (BackgroundPlotter if possible)
if USE_BACKGROUND and BackgroundPlotter is not None:
    try:
        plotter = BackgroundPlotter(window_size=(1280, 720))
    except Exception as e:
        print("BackgroundPlotter construction failed:", e)
        plotter = pv.Plotter(window_size=(1280, 720))
        USE_BACKGROUND = False
else:
    plotter = pv.Plotter(window_size=(1280, 720))

planet_actors = build_scene(plotter)

# ---------------- SIMULATION STATE ---------------- #
state = {
    "sim_time_days": 0.0,
    "speed": INITIAL_SPEED_DAYS_PER_SEC,
    "paused": False,
    "last_wall_time": time.perf_counter(),
    "focus_index": None,
}

MAX_DAYS = MAX_YEARS * 365.25 if MAX_YEARS is not None else None
CALLBACK_STYLE: Optional[str] = None

# ---------------- GUI: Qt widget (when available) or 2D overlay fallback ---------------- #
_use_qt_controls = False
_qt_labels = None         # tuple of (time_label, speed_label, focus_label) when Qt used
_recenter_button = None
_overlay_actor = None     # 2D text actor when Qt not available

# Try to import Qt for native widget controls if using BackgroundPlotter
QtWidgets = None
if USE_BACKGROUND:
    try:
        # Try PyQt5 then PySide2
        try:
            from PyQt5 import QtWidgets  # type: ignore
        except Exception:
            from PySide2 import QtWidgets  # type: ignore
        _use_qt_controls = True
    except Exception:
        _use_qt_controls = False

def recenter_on_sun() -> None:
    """Recenter the camera on the Sun (world origin) and clear focus."""
    state["focus_index"] = None
    plotter.camera.focal_point = (0.0, 0.0, 0.0)
    plotter.render()

def _create_qt_control_widget(plotter_obj) -> Optional[object]:
    """Create a small Qt control widget attached to the BackgroundPlotter window."""
    global _qt_labels, _recenter_button
    if not _use_qt_controls:
        return None

    try:
        app = getattr(plotter_obj, "app", None)
        if app is None:
            parent = None
            try:
                parent = QtWidgets.QApplication.activeWindow()
            except Exception:
                parent = None
        else:
            try:
                parent = app.activeWindow()
            except Exception:
                parent = None

        # create a small widget
        widget = QtWidgets.QWidget(parent)
        widget.setWindowFlags(widget.windowFlags() | getattr(QtWidgets, "WindowStaysOnTopHint", 0))
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        time_label = QtWidgets.QLabel("Time: -")
        speed_label = QtWidgets.QLabel("Speed: -")
        focus_label = QtWidgets.QLabel("Focus: -")
        btn = QtWidgets.QPushButton("Recenter on Sun (c)")
        btn.clicked.connect(lambda: recenter_on_sun())

        layout.addWidget(time_label)
        layout.addWidget(speed_label)
        layout.addWidget(focus_label)
        layout.addWidget(btn)

        widget.setFixedWidth(260)
        widget.setFixedHeight(120)

        if parent is not None:
            try:
                geo = parent.geometry()
                widget.move(geo.x() + geo.width() - widget.width() - 20, geo.y() + 20)
            except Exception:
                pass

        widget.show()
        _qt_labels = (time_label, speed_label, focus_label)
        _recenter_button = btn
        return widget
    except Exception as e:
        print("Failed to create Qt control widget:", e)
        return None

def _update_overlay_text(plotter_obj) -> None:
    """Update the 2D overlay text (fallback when no Qt available)."""
    global _overlay_actor
    sim_days = state["sim_time_days"]
    sim_dt = J2000_DATETIME + timedelta(days=float(sim_days))
    dt_str = sim_dt.strftime("%Y-%m-%d %H:%M:%S")
    speed_text = _format_speed_text(state["speed"])
    focus_idx = state["focus_index"]
    focus_name = PLANET_NAMES[focus_idx] if (focus_idx is not None and 0 <= focus_idx < len(PLANET_NAMES)) else "Sun" if focus_idx is None else "None"

    status = f"Time: {dt_str}\nDays: {sim_days:.2f}\nSpeed: {speed_text}\nFocus: {focus_name}\n(c) Recenter"
    try:
        if _overlay_actor is not None:
            try:
                plotter_obj.remove_actor(_overlay_actor)
            except Exception:
                pass
        _overlay_actor = plotter_obj.add_text(status, position="upper_left", font_size=10, color="white")
    except Exception:
        pass

# create Qt widget if possible and using BackgroundPlotter
_qt_control_widget = None
if USE_BACKGROUND and _use_qt_controls:
    _qt_control_widget = _create_qt_control_widget(plotter)

# ---------------- UTILS ---------------- #
def _format_speed_text(speed: float) -> str:
    """Return a human friendly speed string: days/sec and simulated seconds per real second."""
    sim_secs_per_real = speed * 86400.0  # simulated seconds per real second
    # direction
    dir_str = "fwd" if speed > 0 else ("rev" if speed < 0 else "stopped")
    return f"{speed:.6e} d/s ({sim_secs_per_real:+.3f} s/s, {dir_str})"

# ---------------- UPDATE CALLBACK ---------------- #
def _format_sim_time(sim_days: float) -> str:
    dt = J2000_DATETIME + timedelta(days=float(sim_days))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def update_scene(pl: Optional[pv.Plotter] = None) -> None:
    """
    Update simulation state, planet positions and GUI info.
    """
    now = time.perf_counter()
    dt_real = now - state["last_wall_time"]
    if dt_real > 1.0:
        dt_real = 1.0
    state["last_wall_time"] = now

    if not state["paused"]:
        state["sim_time_days"] += state["speed"] * dt_real
        if MAX_DAYS is not None:
            if state["sim_time_days"] > MAX_DAYS:
                state["sim_time_days"] = MAX_DAYS
                state["paused"] = True
                print("Reached end of precomputed range.")
            elif state["sim_time_days"] < 0:
                state["sim_time_days"] = 0.0

    try:
        positions = ephem.positions_at(state["sim_time_days"])
    except Exception as e:
        print("Ephemeris retrieval error:", e)
        return

    for actor, pnt in zip(planet_actors, positions):
        try:
            actor.SetPosition(float(pnt[0]), float(pnt[1]), float(pnt[2]))
        except Exception:
            pass

    # update camera focus if following a planet
    if state["focus_index"] is not None:
        idx = state["focus_index"]
        if 0 <= idx < len(positions):
            center = positions[idx]
            cam = plotter.camera
            cam.focal_point = (float(center[0]), float(center[1]), float(center[2]))

    # update GUI: Qt labels or 2D overlay
    sim_days = state["sim_time_days"]
    dt_str = _format_sim_time(sim_days)
    speed_txt = _format_speed_text(state["speed"])
    focus_idx = state["focus_index"]
    focus_name = PLANET_NAMES[focus_idx] if (focus_idx is not None and 0 <= focus_idx < len(PLANET_NAMES)) else "Sun" if focus_idx is None else "None"

    if _qt_control_widget is not None and _qt_labels is not None:
        try:
            t_lbl, s_lbl, f_lbl = _qt_labels
            t_lbl.setText(f"Time: {dt_str}")
            s_lbl.setText(f"Speed: {speed_txt}")
            f_lbl.setText(f"Focus: {focus_name}")
        except Exception:
            pass
    else:
        _update_overlay_text(plotter)

    # Render for timer invocations
    try:
        if pl is None:
            if hasattr(plotter, "render"):
                plotter.render()
    except Exception:
        pass

# ---------------- SPEED CONTROL RULES (requested behavior) ---------------- #
def speed_up():
    """
    Increase forward speed:
      - If currently positive, double it.
      - If negative (time running backwards), halve magnitude (move toward zero).
      - If zero, set to +REAL_TIME.
    """
    s = state["speed"]
    if s > 0.0:
        state["speed"] = s * 2.0
    elif s < 0.0:
        # reduce magnitude (move toward forward); if it crosses zero, set to +REAL_TIME
        state["speed"] = s * 0.5
        if abs(state["speed"]) < REAL_TIME_DAYS_PER_SEC * 0.5:
            state["speed"] = REAL_TIME_DAYS_PER_SEC
    else:
        state["speed"] = REAL_TIME_DAYS_PER_SEC

    print(f"Speed increased -> {_format_speed_text(state['speed'])}")

def speed_down():
    """
    Decrease speed and eventually reverse:
      - If currently positive and greater than REAL_TIME, halve it.
      - If halving would go below REAL_TIME, flip to -REAL_TIME.
      - If currently at REAL_TIME (positive) and user decreases, flip straight to -REAL_TIME.
      - If negative, double magnitude (faster backward).
      - If zero, set to -REAL_TIME.
    """
    s = state["speed"]

    if s > 0.0:
        # if current speed is larger than real-time, halve it
        if s > REAL_TIME_DAYS_PER_SEC:
            new_s = s * 0.5
            # if halving would go below REAL_TIME threshold, flip to negative real-time
            if new_s < REAL_TIME_DAYS_PER_SEC:
                state["speed"] = -REAL_TIME_DAYS_PER_SEC
            else:
                state["speed"] = new_s
        else:
            # s <= REAL_TIME_DAYS_PER_SEC -> flip to backward real-time
            state["speed"] = -REAL_TIME_DAYS_PER_SEC
    elif s < 0.0:
        # already running backward: make it faster backward (double magnitude)
        state["speed"] = s * 2.0
    else:
        # s == 0
        state["speed"] = -REAL_TIME_DAYS_PER_SEC

    print(f"Speed decreased -> {_format_speed_text(state['speed'])}")

# ---------------- OTHER CONTROLS ---------------- #
def toggle_pause():
    state["paused"] = not state["paused"]
    print("Paused" if state["paused"] else "Running")

def reset_time():
    state["sim_time_days"] = 0.0
    print("Simulation time reset to J2000.")

def print_speed():
    print(f"Current speed: {_format_speed_text(state['speed'])}")

def focus_planet(idx):
    def _f():
        state["focus_index"] = idx
        print(f"Focusing on {PLANET_NAMES[idx]}")
    return _f

# Register key events (multiple bindings for robustness)
plotter.add_key_event("space", toggle_pause)

plotter.add_key_event("=", speed_up)
plotter.add_key_event("+", speed_up)
plotter.add_key_event("Up", speed_up)

plotter.add_key_event("-", speed_down)
plotter.add_key_event("_", speed_down)
plotter.add_key_event("Down", speed_down)

plotter.add_key_event("0", reset_time)
plotter.add_key_event("s", print_speed)  # press 's' to print current speed

# Recenter: keyboard 'c' also provided
plotter.add_key_event("c", lambda: recenter_on_sun())

# Number keys 1–8 to focus on each planet
for i in range(len(PLANET_NAMES)):
    key = str(i + 1)
    plotter.add_key_event(key, focus_planet(i))

# ---------------- REGISTER CALLBACK (force timer when possible) ---------------- #
def register_update_callback(p: pv.Plotter, interval_ms: int = TIMER_INTERVAL_MS) -> None:
    global CALLBACK_STYLE

    # 1) Preferred: add_timer_callback(func, interval=ms)
    if hasattr(p, "add_timer_callback"):
        try:
            try:
                p.add_timer_callback(lambda: update_scene(None), interval=interval_ms)
            except TypeError:
                p.add_timer_callback(lambda: update_scene(None), interval_ms)
            CALLBACK_STYLE = "timer"
            print("Registered update with add_timer_callback (timer).")
            return
        except Exception as e:
            print("add_timer_callback attempt failed:", e)

    # 2) Next: add_callback(func, interval) on some Plotter variants
    if hasattr(p, "add_callback"):
        try:
            p.add_callback(lambda: update_scene(None), interval_ms)
            CALLBACK_STYLE = "callback"
            print("Registered update with add_callback.")
            return
        except Exception as e:
            print("add_callback attempt failed:", e)

    # 3) VTK interactor repeating timer if available
    iren = getattr(p, "iren", None)
    if iren is not None:
        try:
            create_timer = getattr(iren, "CreateRepeatingTimer", None)
            if callable(create_timer):
                create_timer(int(interval_ms))
                iren.AddObserver("TimerEvent", lambda obj, ev: update_scene(None))
                CALLBACK_STYLE = "iren"
                print("Registered update with VTK interactor repeating timer (iren).")
                return
            else:
                print("iren available but no CreateRepeatingTimer method.")
        except Exception as e:
            print("iren timer attempt failed:", e)

    # 4) Fallback: on-render callback (only runs when plotter renders)
    if hasattr(p, "add_on_render_callback"):
        try:
            p.add_on_render_callback(lambda pl: update_scene(pl))
            CALLBACK_STYLE = "on_render"
            print("Registered update with add_on_render_callback (fallback).")
            print("Note: on-render callbacks run only when the plotter renders.")
            print("If you want continuous updates, install pyvistaqt (pip install pyvistaqt) so BackgroundPlotter is available.")
            return
        except Exception as e:
            print("add_on_render_callback attempt failed:", e)

    CALLBACK_STYLE = None
    print("Warning: could not register a periodic update callback for pyvista. Scene will update only when manually rendered or when interacting with the window.")

# register
register_update_callback(plotter, TIMER_INTERVAL_MS)
print("CALLBACK_STYLE =", CALLBACK_STYLE)

# Ensure overlay initially matches starting state
if _qt_control_widget is None:
    _update_overlay_text(plotter)

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    if USE_BACKGROUND:
        app = getattr(plotter, "app", None)
        if app is not None:
            try:
                if hasattr(app, "exec_"):
                    app.exec_()
                else:
                    app.exec()
            except Exception:
                try:
                    while True:
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    pass
        else:
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
    else:
        plotter.show()