import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa

# ================== CONFIGURE THESE ==================
PORT = "COM6"
BAUDRATE = 115200

N_POINTS = 16   # points per sweep
N_SWEEPS = 12        # total sweeps
Z_STEP_INCH = 0.5    # height increase per sweep
INCH_TO_MM = 25.4
Z_STEP_MM = Z_STEP_INCH * INCH_TO_MM
# =====================================================


def open_serial(port, baudrate):
    ser = serial.Serial(port, baudrate, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()
    return ser


def run_sweep(ser, n_points):
    ser.reset_input_buffer()
    ser.write(b's\n')

    data = []
    print("  Waiting for data from Arduino...")

    while len(data) < n_points:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if "," not in line:
            continue

        parts = line.split(",")
        if len(parts) != 2:
            continue

        try:
            x = float(parts[0].strip())
            y = float(parts[1].strip())
        except ValueError:
            continue

        data.append((x, y))
        print(f"    Point {len(data)}/{n_points}: x={x:.2f}, y={y:.2f}")

    return np.array(data)


def main():
    print(f"Opening serial port {PORT}...")
    ser = open_serial(PORT, BAUDRATE)
    print("Connected.\n")

    sweeps = []  # will become shape (12,19,2)

    try:
        while len(sweeps) < N_SWEEPS:
            sweep_idx = len(sweeps) + 1
            print(f"=== Sweep {sweep_idx}/{N_SWEEPS} ===")
            input("Press Enter to begin sweep...")

            sweep_data = run_sweep(ser, N_POINTS)

            print("\nSweep data:")
            print(sweep_data)

            while True:
                choice = input("Keep this sweep? [k]eep / [r]edo / [q]uit: ").strip().lower()
                if choice in ("k", "r", "q"):
                    break
                print("  Please enter k, r, or q.")

            if choice == "q":
                print("Exiting.")
                return
            elif choice == "r":
                print("Discarding sweep.\n")
                continue
            else:
                sweeps.append(sweep_data)
                print("Saved.\n")

        # ===========================================================
        #   BUILD REGULAR SURFACE PLOT
        # ===========================================================

        print("All sweeps complete. Building surface plot...")

        sweeps = np.stack(sweeps, axis=0)  # (12,19,2)

        # Extract X, Y from sweeps
        X = sweeps[:, :, 0]   # shape (12,19)
        Y = sweeps[:, :, 1]

        # Create Z from height levels
        sweep_indices = np.arange(N_SWEEPS)
        Z_levels = sweep_indices[:, None] * Z_STEP_MM  # shape (12,1)
        Z = np.repeat(Z_levels, N_POINTS, axis=1)       # (12,19)

        # Prepare meshgrid of point index and sweep index
        point_index = np.arange(N_POINTS)
        sweep_index = np.arange(N_SWEEPS)
        P, S = np.meshgrid(point_index, sweep_index)

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Surface uses X,Y,Z but must match shapes (12,19)
        surf = ax.plot_surface(Y, X, Z, cmap="viridis", edgecolor='none')

        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_zlabel("Z (mm)")
        ax.set_title("3D Surface Plot of Lidar Sweeps")

        fig.colorbar(surf, shrink=0.5, aspect=10)

        plt.tight_layout()
        plt.show()

    finally:
        ser.close()
        print("Serial Port Closed.")


if __name__ == "__main__":
    main()
