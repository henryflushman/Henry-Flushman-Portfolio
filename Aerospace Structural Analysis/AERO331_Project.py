import numpy as np
from numpy import sin, cos, tan, pi
from trusslib_v1_1 import Truss


def report_member_lengths_and_forces(truss, joints, members, A=None, force_sign_convention="stress*A"):
    """
    Drop-in reporter for truss member geometry + axial forces.

    Parameters
    ----------
    truss : Truss
        Solved truss object (call truss.solve() first).
    joints : list[list[float]]
        Joint coordinates used to build the truss.
    members : list[list[int]]
        Connectivity used to build the truss.
    A : float or None
        Cross-sectional area. If provided and truss.stresses exists, axial force = stress * A.
    force_sign_convention : str
        Just a label in the output.

    Returns
    -------
    rows : list[dict]
        One dict per member.
    """
    J = np.asarray(joints, dtype=float)
    M = np.asarray(members, dtype=int)

    # Compute lengths from geometry
    p_i = J[M[:, 0], :]
    p_j = J[M[:, 1], :]
    L = np.linalg.norm(p_j - p_i, axis=1)

    stress = None
    force = None

    if hasattr(truss, "stresses"):
        try:
            stress = np.asarray(truss.stresses, dtype=float).reshape(-1)
        except Exception:
            stress = None

    if (stress is not None) and (A is not None):
        force = stress * float(A)

    if force is None and hasattr(truss, "forces"):
        try:
            force = np.asarray(truss.forces, dtype=float).reshape(-1)
        except Exception:
            force = None

    if force is None:
        force = np.full(len(M), np.nan)

    rows = []
    header = (
        f"{'Mem':>4}  {'i-j':>7}  {'Length':>10}  {'Force (lb)':>12}  {'Stress (psi)':>13}  {'State':>10}"
    )
    print("\n" + header)
    print("-" * len(header))

    for k in range(len(M)):
        i, j = int(M[k, 0]), int(M[k, 1])
        Li = float(L[k])
        Fi = float(force[k]) if np.isfinite(force[k]) else np.nan
        Si = float(stress[k]) if (stress is not None and k < len(stress)) else np.nan

        if np.isfinite(Fi):
            state = "Tension" if Fi > 0 else ("Comp" if Fi < 0 else "Zero")
        else:
            state = "Unknown"

        rows.append({
            "member": k + 1,
            "i": i,
            "j": j,
            "Li": Li,
            "force_lb": Fi,
            "stress_psi": Si,
            "state": state
        })

        print(f"{k+1:4d}  {i:2d}-{j:<2d}  {Li:10.4f}  {Fi:12.4f}  {Si:13.4f}  {state:>10}")

    if (stress is not None) and (A is not None):
        print(f"\nForce computed as {force_sign_convention} with A = {A} in^2.\n")
    else:
        print("\nForce could not be computed from stress*A (missing A or stresses). "
              "Tried truss.forces; if still Unknown, your Truss class may not expose member forces.\n")

    return rows


################################
# --- Geometry -----------------

H = 7.0            # in, bottom cell height
H2 = H + 12.0      # in, second ring height
H3 = H2 + 12.0     # in, third ring height

Rb = 7.5 / 2       # in
Rt = 3.0 / 2       # in
E = 0.44e6         # psi
b = 3 / 16         # in
h = 1 / 16         # in
A = b * h          # in^2
I = b * h**3 / 12  # in^4

n = 3              # 3-sided tower
K = 1              # pinned-pinned

################################
# --- Defining Joints ----------

theta = np.linspace(0, 2 * pi, n, endpoint=False)

# Base nodes (z = 0)
baseNodes = [
    [Rb * cos(t), Rb * sin(t), 0.0] for t in theta
]

# Ring 1 nodes (z = H)
ring1Nodes = [
    [Rt * cos(t), Rt * sin(t), H] for t in theta
]

# Ring 2 nodes (z = H2)
ring2Nodes = [
    [Rt * cos(t), Rt * sin(t), H2] for t in theta
]

# Ring 3 nodes (z = H3)
ring3Nodes = [
    [Rt * cos(t), Rt * sin(t), H3] for t in theta
]

joints = baseNodes + ring1Nodes + ring2Nodes + ring3Nodes

#################################
# --- Defining Members ----------

members = []

# Ring helper indices:
# Base:   0,1,2
# Ring 1: 3,4,5
# Ring 2: 6,7,8
# Ring 3: 9,10,11

# -------------------------------
# Perimeter rings
# -------------------------------

# Base ring
for i in range(n):
    members.append([i, (i + 1) % n])

# Ring 1
for i in range(n):
    members.append([n + i, n + (i + 1) % n])

# Ring 2
for i in range(n):
    members.append([2 * n + i, 2 * n + (i + 1) % n])

# Ring 3
for i in range(n):
    members.append([3 * n + i, 3 * n + (i + 1) % n])

# -------------------------------
# Vertical members
# -------------------------------

# Base -> Ring 1
for i in range(n):
    members.append([i, n + i])

# Ring 1 -> Ring 2
for i in range(n):
    members.append([n + i, 2 * n + i])

# Ring 2 -> Ring 3
for i in range(n):
    members.append([2 * n + i, 3 * n + i])

# -------------------------------
# Bracing
# -------------------------------
# Face i is the panel between:
# lower ring nodes i and i+1
# upper ring nodes i and i+1

# Bottom cell:
# - face 0: full X
# - face 1: one diagonal
# - face 2: one diagonal

# Face 0 X-brace: base/ring1 panel between nodes (0,1) and (3,4)
members.append([0, n + 1])  # 0 -> 4
members.append([1, n])  # 1 -> 3

# Face 1 single diagonal: panel between nodes (1,2) and (4,5)
members.append([1, n + 2])  # 1 -> 5

# Face 2 single diagonal: panel between nodes (2,0) and (5,3)
members.append([0, n + 2])  # 2 -> 3

# Middle cell: one diagonal per face
# Face 0: ring1/ring2 panel between (3,4) and (6,7)
members.append([n + 0, 2 * n + 1])  # 3 -> 7

# Face 1: ring1/ring2 panel between (4,5) and (7,8)
members.append([n + 1, 2 * n + 2])  # 4 -> 8

# Face 2: ring1/ring2 panel between (5,3) and (8,6)
members.append([n + 2, 2 * n + 0])  # 5 -> 6

# Top cell: one diagonal per face
# Face 0: ring2/ring3 panel between (6,7) and (9,10)
members.append([2 * n + 0, 3 * n + 2])  # 6 -> 10

# Face 1: ring2/ring3 panel between (7,8) and (10,11)
members.append([2 * n + 1, 3 * n])  # 7 -> 11

# Face 2: ring2/ring3 panel between (8,6) and (11,9)
members.append([2 * n + 2, 3 * n + 1])  # 8 -> 9

#################################
# --- Constraints ---------------

constraints = []
for i in range(n):
    constraints.append([i, 0, 0.0])
    constraints.append([i, 1, 0.0])
    constraints.append([i, 2, 0.0])

#################################
# --- Loads ---------------------

loads = []
P = -(10.0 / n)

# Load applied at Ring 2 nodes, z-direction
for i in range(n):
    loads.append([2 * n + i, 2, P])

#################################
# --- Building ------------------

truss = Truss(joints, members, E, A, constraints, loads)

truss.solve()
report_member_lengths_and_forces(truss, joints=joints, members=members, A=A)

#################################
# --- Buckling ------------------

F = np.asarray(truss.stresses) * A
L = np.asarray(truss.Ls)
E_members = np.asarray(truss.Es)

Pcr = (pi**2 * E_members * I) / ((K * L)**2)

comp = np.where(F < 0)[0]

lam = np.full(truss.n_members, np.inf)
lam[comp] = Pcr[comp] / np.abs(F[comp])

i_crit = np.argmin(lam)

#################################
# --- Results -------------------

truss.print_stresses()

print("First buckling member (1-based):", i_crit + 1)
print("Buckling load factor lambda:", lam[i_crit])
print("Member axial force at current load (lb):", F[i_crit])
print("Member Euler Pcr (lb):", Pcr[i_crit])

truss.draw(equal_axes=True)
truss.plot(equal_axes=True)