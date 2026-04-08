#-----------------------------------------------------------------------------#
# Library for calculations involving fiber reinforced composites.
# 
# Amuthan Ramabathiran (aramabat@calpoly.edu)
# Aerospace Engineering, Cal Poly SLO
# 
# Developed for AERO 331 and 431.
#
# Version 1.0 (May 2025): Classes for setting up Ply and Laminate.
# Version 1.1 (Jan 2026): Added useful plotting functionality.
#-----------------------------------------------------------------------------#

import numpy as np
import matplotlib.pyplot as plt

class Ply:
    def __init__(self, E1=1.4e11, E2=1e10, nu12=0.3, G12=7.0e9, 
                 theta=0.0, zL=-0.5e-3, zH=0.5e-3):
        self.E1 = E1
        self.E2 = E2
        self.nu12 = nu12
        self.G12 = G12

        self.theta = theta*np.pi/180
        self.zL = zL
        self.zH = zH
        self.t = zH - zL
        self.zbar = 0.5*(zL + zH)

        self.update()

    def set_material_properties(self, E1, E2, nu12, G12):
        self.E1 = E1
        self.E2 = E2
        self.nu12 = nu12
        self.G12 = G12
        self.update()

    def set_orientation(self, theta):
        self.theta = theta*np.pi/180
        self.update()

    def set_ply_location(self, zL, zH):
        self.zL = zL
        self.zH = zH
        self.t = zH - zL
        self.zbar = 0.5*(zL + zH)

    def update(self): 
        self.nu21 = self.nu12*self.E2/self.E1

        self.S = self.compute_S()
        self.Q = self.compute_Q()

        self.Sbar = self.compute_Sbar()
        self.Qbar = self.compute_Qbar()

        self.compute_apparent_engineering_moduli()

    def compute_S(self):
        return np.array([
            [1/self.E1, -self.nu21/self.E2, 0.0],
            [-self.nu12/self.E1, 1/self.E2, 0.0],
            [0.0, 0.0, 1/self.G12]
        ])
    
    def compute_Q(self):
        den = 1.0 - self.nu12*self.nu21
        return np.array([
            [self.E1/den, self.nu12*self.E2/den, 0.0],
            [self.nu21*self.E1/den, self.E2/den, 0.0],
            [0.0, 0.0, self.G12]
        ])
    
    def Ts(self):
        c = np.cos(self.theta)
        s = np.sin(self.theta)
        return np.array([
            [c*c, s*s, 2*c*s],
            [s*s, c*c, -2*c*s],
            [-c*s, c*s, c*c - s*s]
        ])
    
    def iTs(self):
        c = np.cos(-self.theta)
        s = np.sin(-self.theta)
        return np.array([
            [c*c, s*s, 2*c*s],
            [s*s, c*c, -2*c*s],
            [-c*s, c*s, c*c - s*s]
        ])
    
    def Te(self):
        c = np.cos(self.theta)
        s = np.sin(self.theta)
        return np.array([
            [c*c, s*s, c*s],
            [s*s, c*c, -c*s],
            [-2*c*s, 2*c*s, c*c - s*s]
        ])
    
    def iTe(self):
        c = np.cos(-self.theta)
        s = np.sin(-self.theta)
        return np.array([
            [c*c, s*s, c*s],
            [s*s, c*c, -c*s],
            [-2*c*s, 2*c*s, c*c - s*s]
        ])
    
    def compute_Qbar(self):
        return self.iTs() @ (self.Q @ self.Te())
    
    def compute_Sbar(self):
        return self.iTe() @ (self.S @ self.Ts())
    
    def compute_apparent_engineering_moduli(self):
        c = np.cos(self.theta)
        s = np.sin(self.theta)
        
        self.Ex = 1/(c**4/self.E1 + (1/self.G12 - 2*self.nu12/self.E1)*c*c*s*s + s**4/self.E2)
        self.Ey = 1/(s**4/self.E1 + (1/self.G12 - 2*self.nu12/self.E1)*c*c*s*s + c**4/self.E2)
        self.Gxy = 1/(1/self.G12 + 4*(1/self.E1 + 1/self.E2 + 2*self.nu12/self.E1 - 1/self.G12)*c*c*s*s)
        self.nuxy = self.Ex*(self.nu12/self.E1 - (1/self.E1 + 1/self.E2 + 2*self.nu12/self.E1 - 1/self.G12)*c*c*s*s)
        self.etax = self.Ex*((2/self.E1 + 2*self.nu12/self.E1 - 1/self.G12)*s*c**3 - (2/self.E2 + 2*self.nu12/self.E1 - 1/self.G12)*c*s**3)
        self.etay = self.Ey*((2/self.E1 + 2*self.nu12/self.E1 - 1/self.G12)*c*s**3 - (2/self.E2 + 2*self.nu12/self.E1 - 1/self.G12)*s*c**3)


class Laminate:
    def __init__(self, theta=[90,0,0,90], t=1.0e-3, E1=1.4e11, E2=1e10, nu12=0.3, G12=7.0e9):
        self.n_ply = len(theta)
        self.theta = np.array(theta)
        self.z = np.linspace(-t/2, t/2, self.n_ply+1)
        self.t = t
        self.ply = [Ply(E1=E1, E2=E2, G12=G12, nu12=nu12, 
                        theta=self.theta[i], zL=self.z[i], zH=self.z[i+1]) 
                    for i in range(self.n_ply)]
        self.zbar = np.array([ply.zbar for ply in self.ply])
        self.update()

    def reset_layup(self, theta=None, z=None):
        if theta is not None:
            assert len(theta) == self.n_ply, "List of orientations does not correspond to number of plies!"
            self.theta = np.array(theta)

        if z is not None:
            assert len(z) - 1 == self.n_ply, "List of z coordinates does not correspond to number of plies!"
            self.z = z   
            self.t = z[-1] - z[0]
            
        for i, ply in enumerate(self.ply):
            if theta is not None:
                ply.set_orientation(theta[i])
            if z is not None:
                ply.set_ply_location(z[i], z[i+1])

        if z is not None:
            self.zbar = np.array([0.5*(ply.zL + ply.zH) for ply in self.ply])

        self.update()

    def update(self):
        self.A = np.zeros((3, 3))
        self.B = np.zeros((3, 3))
        self.D = np.zeros((3, 3))

        for ply in self.ply:
            self.A += ply.Qbar * (ply.zH - ply.zL)
            self.B -= ply.Qbar * (ply.zH**2 - ply.zL**2) / 2
            self.D += ply.Qbar * (ply.zH**3 - ply.zL**3) / 3

        self.ABD = np.zeros((6, 6))
        for i in range(3):
            for j in range(3):
                self.ABD[i,j] = self.A[i,j]
            for j in range(3,6):
                self.ABD[i,j] = self.B[i,j-3]
        for i in range(3,6):
            for j in range(3):
                self.ABD[i,j] = self.B[i-3,j]
            for j in range(3,6):
                self.ABD[i,j] = self.D[i-3,j-3]

    def find_ply(self, z):
        assert z >= self.z[0] and z <= self.z[-1], "Invalid z coordinate!"
        i_ply = self.n_ply - 1
        for i in range(self.n_ply):
            if z >= self.z[i] and z < self.z[i+1]:
                i_ply = i
                break
        return i_ply
    

def plot_midplane_deformation_2d(epsilonbar, magnification=1):
    exx, eyy, exy = epsilonbar * magnification
    exy = exy/2.0
    x = np.linspace(-1,1,20)
    y = np.linspace(-1,1,20)
    x, y = np.meshgrid(x, y)
    u = exx * x + exy * y
    v = exy * x + eyy * y
    xd = x + u
    yd = y + v
    plt.scatter(x.ravel(), y.ravel(), c='grey', s=10)
    plt.scatter(xd.ravel(), yd.ravel(), c='blue', s=20)
    plt.xlabel('x')
    plt.ylabel('y')
    plt.grid()
    plt.gca().set_aspect('equal')
    plt.show()


def plot_midplane_deformation_3d(epsilonbar, kappabar, magnification=1, zlim=None):
    exx, eyy, exy = epsilonbar * magnification
    kxx, kyy, kxy = kappabar * magnification
    exy = exy/2.0
    kxy = kxy/2.0

    x = np.linspace(-1,1,20)
    y = np.linspace(-1,1,20)
    x, y = np.meshgrid(x, y)

    u = exx * x + exy * y
    v = exy * x + eyy * y
    w = 0.5 * kxx * x*x + 0.5 * kyy * y*y + 2 * kxy * x*y

    xd = x + u
    yd = y + v
    w0 = 0*x + 0*y

    ax = plt.figure().add_subplot(projection='3d')
    
    ax.plot_wireframe(x, y, w0, color='grey', lw=0.5)
    ax.plot_surface(xd, yd, w, cmap='jet')
    
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')

    if zlim is not None:
        ax.set_zlim(*zlim)

    plt.show()


def plot_laminate_stress_z(laminate, epsilonbar=None, kappabar=None, component='XX'):
    assert epsilonbar is not None or kappabar is not None, 'Either midplane strain or midplane curvature is required.'

    idx=0
    if component == 'XX':
        idx = 0
    elif component == 'YY':
        idx = 1
    elif component == 'XY':
        idx = 2
    else:
        raise ValueError('Component should be XX, YY, or XY.')

    t = laminate.t
    n_plot = 200
    list_z = np.linspace(-t/2, t/2, n_plot)
    list_s = np.zeros(n_plot)

    for i, z in enumerate(list_z):
        i_ply = laminate.find_ply(z)
        stress = np.zeros(3)
        if epsilonbar is not None:
            stress += laminate.ply[i_ply].Qbar @ epsilonbar
        if kappabar is not None:
            stress -= z * (laminate.ply[i_ply].Qbar @ kappabar)
        list_s[i] = stress[idx]

    plt.plot(list_s, list_z, 'b-', lw=3)

    if idx == 0:
        plt.xlabel(r'$\sigma_{xx}$')
    elif idx == 1:
        plt.xlabel(r'$\sigma_{yy}$')
    elif idx == 2:
        plt.xlabel(r'$\sigma_{xy}$')
    plt.ylabel(r'$z$')

    plt.grid()
    plt.show()



    