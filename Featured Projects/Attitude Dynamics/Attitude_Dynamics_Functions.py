from re import I
import numpy as np
import sympy as sp
from numpy import sin, cos, pi, sign

def ref_axb(a_vec, b_vec, F):
    """ Computes a cross b in which a and b are both in the same reference frame
    This results in an expression F^T (a' x b)
    """

    if F.rows != F.cols:
        raise ValueError("F must be a square matrix")
    
    if a_vec.cols > 1 or b_vec.cols > 1:
        raise ValueError("a and b must both be column vectors")
    
    x_vec = F[:, 0]
    y_vec = F[:, 1]
    z_vec = F[:, 2]

    F_rowvec = np.array([x_vec, y_vec, z_vec])
    F_cross = np.cross(F_rowvec, F_rowvec.T)
    
    a = np.dot(F.T, a_vec)
    b = np.dot(F.T, b_vec)

def Rx_deg(x):
    x = np.deg2rad(x)
    return np.array([[1, 0, 0],
                     [0, np.cos(x), -np.sin(x)],
                     [0, np.sin(x),  np.cos(x)]])

def Ry_deg(y):
    y = np.deg2rad(y)
    return np.array([[ np.cos(y), 0, np.sin(y)],
                     [ 0,         1, 0        ],
                     [-np.sin(y), 0, np.cos(y)]])

def Rz_deg(z):
    z = np.deg2rad(z)
    return np.array([[ np.cos(z), -np.sin(z), 0],
                     [ np.sin(z),  np.cos(z), 0],
                     [ 0,          0,         1]])

def rotation_sequence(angles_deg, axes):
    assert len(angles_deg) == len(axes), "angles and axes must have same length"
    R = np.eye(3)
    for ang, ax in zip(angles_deg, axes):
        if   ax == 1: R = Rx_deg(ang) @ R
        elif ax == 2: R = Ry_deg(ang) @ R
        elif ax == 3: R = Rz_deg(ang) @ R
        else:
            raise ValueError("axis must be 1 (X), 2 (Y), or 3 (Z)")
    return R

def rotm_to_euler321(R, degrees=False):
    """
    Convert a rotation matrix to Euler angles (Z-Y-X / yaw-pitch-roll).
    
    Parameters
    ----------
    R : array_like, shape (3, 3)
        Rotation matrix (orthonormal, det ≈ +1).
    degrees : bool, optional
        If True, return angles in degrees. Default is radians.
    
    Returns
    -------
    yaw : float
        Rotation about Z-axis.
    pitch : float
        Rotation about Y-axis.
    roll : float
        Rotation about X-axis.
    
    Notes
    -----
    Convention: R = Rz(yaw) * Ry(pitch) * Rx(roll)
    """
    R = np.asarray(R)
    assert R.shape == (3, 3), "Input must be a 3x3 matrix"

    # Extract elements
    r11, r12, r13 = R[0, :]
    r21, r22, r23 = R[1, :]
    r31, r32, r33 = R[2, :]

    # Compute Euler angles
    pitch = np.arctan2(-r31, np.hypot(r32, r33))
    roll  = np.arctan2(r32, r33)
    yaw   = np.arctan2(r21, r11)

    if degrees:
        yaw, pitch, roll = np.degrees([yaw, pitch, roll])

    return yaw, pitch, roll

def euler321_to_quat(phi, theta, psi):
    """Radians -> quaternion [qw, qx, qy, qz]"""
    c1, c2, c3 = cos(psi/2), cos(theta/2), cos(phi/2)
    s1, s2, s3 = sin(psi/2), sin(theta/2), sin(phi/2)
    # yaw-psi (Z), pitch-theta (Y), roll-phi (X)
    qw = c1*c2*c3 + s1*s2*s3
    qx = c1*c2*s3 - s1*s2*c3
    qy = c1*s2*c3 + s1*c2*s3
    qz = s1*c2*c3 - c1*s2*s3
    q = np.array([qw, qx, qy, qz])
    return q/np.linalg.norm(q)

def quat_to_euler321(q):
    """Quaternion [qx, qy, qz, qw] -> radians (phi, theta, psi)
    Vector-first convention (matches integration form [ex, ey, ez, eta])
    """
    qx, qy, qz, qw = q
    # Direction cosine matrix (body from inertial) for Hamilton convention
    R11 = 1 - 2*(qy**2 + qz**2)
    R21 = 2*(qx*qy + qz*qw)
    R31 = 2*(qx*qz - qy*qw)
    R32 = 2*(qy*qz + qx*qw)
    R33 = 1 - 2*(qx**2 + qy**2)

    # 3-2-1 extraction (roll-pitch-yaw)
    phi   = np.arctan2(R32, R33)   # roll
    theta = -np.arcsin(R31)        # pitch
    psi   = np.arctan2(R21, R11)   # yaw

    return np.array([phi, theta, psi])

def eulerangles_from_bodyrates(w_b, angles):
    p, q, r = np.asarray(w_b, dtype=float)
    angles = np.asarray(angles, dtype=float)
    phi, theta, psi = angles

    sphi,  cphi  = np.sin(phi),  np.cos(phi)
    stheta, ctheta = np.sin(theta), np.cos(theta)
    ttheta = np.tan(theta)

    phidot   = p + sphi*ttheta*q + cphi*ttheta*r
    thetadot = q*cphi - p*sphi
    psidot   = sphi/ctheta*q + cphi/ctheta*r
    return np.array([phidot, thetadot, psidot], dtype=float)


def angvel_to_quat(w_b, q0):
    eta = q0[3]
    eps = q0[:3]
    epsx = np.array([[   0,   -eps[2],  eps[1]],
                     [ eps[2],    0,   -eps[0]],
                     [-eps[1],  eps[0],   0   ]], dtype=float)
    eps_dot = 0.5*(eta*np.eye(3) + epsx) @ w_b
    eta_dot = -0.5*eps @ w_b
    return np.array([eps_dot[0], eps_dot[1], eps_dot[2], eta_dot], dtype=float)


def angvel_to_quateuler(t, y0, wb):
    """
    Angular velocity to quaternion derivative.

    Parameters
    ----------
    t : float
        Time (s)
    y0 : array_like
        Initial quaternion [eps1, eps2, eps3, eta] and Euler angles [phi, theta, psi]
    wb : array_like
        Angular velocity [p, q, r]

    Returns
    -------
    array_like
        Quaternion derivative [phi_dot, theta_dot, psi_dot, eps1_dot, eps2_dot, eps3_dot, eta_dot]
    """
    y0 = np.asarray(y0, dtype=float)
    wb = np.asarray(wb, dtype=float)
    
    phi, theta, psi, eps1, eps2, eps3, eta = y0
    p, q, r = wb
    
    # Euler angles
    phi_dot = p + q*np.sin(phi)*np.tan(theta) + r*np.cos(phi)*np.tan(theta)
    theta_dot = q*np.cos(phi) - p*np.sin(phi)
    psi_dot = (np.sin(phi)/np.cos(theta))*q + (np.cos(phi)/np.cos(theta))*r
    # Quaternion
    eps = np.array([eps1, eps2, eps3])
    epsx = np.array([
        [0, -eps3, eps2],
        [eps3, 0, -eps1],
        [-eps2, eps1, 0]
    ])
    eps_dot = 0.5*(eta*np.eye(3) + epsx) @ wb
    eta_dot = -0.5* (eps @ wb)
    return np.array([phi_dot, theta_dot, psi_dot, eps_dot[0], eps_dot[1], eps_dot[2], eta_dot], dtype=float)

def torq_to_eulerquat(t, y0, T, I):
    T = np.asarray(T, dtype=float)
    y0 = np.asarray(y0, dtype=float)
    I = np.asarray(I, dtype=float)
    p, q, r, phi, theta, psi, eps1, eps2, eps3, eta = y0
    Tx, Ty, Tz = T
    Ix, Iy, Iz = I
    
    wb = np.array([p, q, r])
    wb_dot = np.linalg.solve(I, T - np.cross(wb, I @ wb))
    p_dot, q_dot, r_dot = wb_dot
    
    p_dot = wb_dot[0]
    q_dot = wb_dot[1]
    r_dot = wb_dot[2]
    
    eulermatrix = np.array([
        [np.cos(theta), np.sin(phi)*np.sin(theta),  np.cos(phi)*np.sin(theta)],
        [ 0,            np.cos(phi)*np.cos(theta), -np.sin(phi)*np.cos(theta)],
        [ 0,            np.sin(phi),                np.cos(phi)              ]
    ])

    euler_dot = (1/np.cos(theta)) * (eulermatrix @ np.array([p,q,r]))
    
    phi_dot = euler_dot[0]
    theta_dot = euler_dot[1]
    psi_dot = euler_dot[2]
    
    # Quaternion
    eps = np.array([eps1, eps2, eps3])
    epsx = np.array([
        [0, -eps3, eps2],
        [eps3, 0, -eps1],
        [-eps2, eps1, 0]
    ])
    eps_dot = 0.5*(eta*np.eye(3) + epsx) @ wb
    eta_dot = -0.5* (eps @ wb)
    quat_dot = np.array([eps_dot[0], eps_dot[1], eps_dot[2], eta_dot], dtype=float)
    
    return np.array([p_dot, q_dot, r_dot, phi_dot, theta_dot, psi_dot, quat_dot[0], quat_dot[1], quat_dot[2], quat_dot[3]])