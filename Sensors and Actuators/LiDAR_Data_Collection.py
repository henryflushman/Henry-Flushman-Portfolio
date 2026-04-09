"""
lidar_data_collect.py

Long-term data collection at a single height for error analysis.

Protocol expected from Arduino:
  - Python sends:   "START\\n"
  - Arduino outputs several lines: "angle_deg, distance_mm"
  - Arduino ends the sweep with a line exactly: "SWEEP_DONE"

This script:
  - Repeatedly triggers sweeps for up to DURATION_SEC seconds
    (or until you hit Ctrl+C).
  - Logs every point to a CSV file for JMP analysis.

Output CSV columns:
  sweep_index, point_index, elapsed_time_s, angle_deg, dist_mm
"""

import time
import serial
import numpy as np

# ================== USER SETTINGS ==================

PORT = "COM6"         # <-- change to your port (e.g. "COM3", "/dev/ttyACM0")
BAUDRATE = 115200

DURATION_SEC = 300.0  # how long to collect data (seconds)
OUTFILE = "lidar_error_data.csv"

# Arduino protocol tokens
START_COMMAND = b"START\n"     # what we send to start one sweep
SWEEP_DONE_TOKEN = "SWEEP_DONE"  # what Arduino prints when finished

# Optional sanity range for distances (mm). Values outside this range are still
# logged, but you can filter them later in JMP.
MIN_DIST_MM = 0.0
MAX_DIST_MM = 4000.0

# ==================================================


def get_sweep(ser):
    """
    Trigger ONE sweep and return a list of (angle_deg, dist_mm) tuples.

    Protocol:
      - Clear input buffer
      - Send START_COMMAND
      - Read lines until SWEEP_DONE_TOKEN
    """
    ser.reset_input_buffer()
    ser.write(START_COMMAND)
    ser.flush()

    sweep = []

    while True:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if not line:
            continue  # timeout/empty; keep waiting

        if line == SWEEP_DONE_TOKEN:
            break  # end of this sweep

        if "," not in line:
            # Some debug print from Arduino; ignore
            print(f"  [info] non-data line: {line}")
            continue

        try:
            angle_str, dist_str = line.split(",", 1)
            angle_deg = float(angle_str.strip())
            dist_mm = float(dist_str.strip())
        except ValueError:
            print(f"  [warn] could not parse line: {line}")
            continue

        sweep.append((angle_deg, dist_mm))

    return sweep


def collect_error_data():
    """
    Collect sweeps for up to DURATION_SEC seconds (or until Ctrl+C),
    then save all raw points to OUTFILE.
    """
    rows = []  # [sweep_index, point_index, elapsed_time_s, angle_deg, dist_mm]
    sweep_index = 0

    print(f"Opening serial port {PORT} at {BAUDRATE} baud...")
    with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
        time.sleep(2.0)  # allow Arduino to reset
        print("Connected.")
        print(f"Collecting for up to {DURATION_SEC:.1f} seconds.")
        print("Press Ctrl+C to stop early.\n")

        start_time = time.time()

        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed >= DURATION_SEC:
                    print("Time limit reached.")
                    break

                print(f"Starting sweep {sweep_index} at t={elapsed:.1f} s")
                sweep = get_sweep(ser)
                sweep_time = time.time() - start_time

                print(f"  Got {len(sweep)} points.")

                for point_index, (angle_deg, dist_mm) in enumerate(sweep):
                    rows.append([
                        sweep_index,
                        point_index,
                        sweep_time,
                        angle_deg,
                        dist_mm,
                    ])

                sweep_index += 1

        except KeyboardInterrupt:
            print("\nData collection interrupted by user (Ctrl+C).")

    if not rows:
        print("No data collected. Not writing file.")
        return

    data = np.array(rows, dtype=float)
    header = "sweep_index,point_index,elapsed_time_s,angle_deg,dist_mm"
    np.savetxt(OUTFILE, data, delimiter=",", header=header, comments="")

    print(f"\nSaved {len(rows)} measurements to '{OUTFILE}'.")
    print("You can now open this CSV in JMP for error analysis.")


if __name__ == "__main__":
    collect_error_data()
