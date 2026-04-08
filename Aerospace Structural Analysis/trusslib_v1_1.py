#####################################################################
# Library for Truss Calculations
# Based on the older trusslab_v0_4.py
# Developed for use in AERO 331 and AERO 431 (Winter 2026)
#
# Amuthan Ramabathiran
# Aerospace Engineering
# Cal Poly SLO
#
# Version 1.1, January 7, 2026.
# All features of previous GUI version retained.
# More convenient print functions for displacements and stresses.
#
#####################################################################

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import copy


class Truss:
    def __init__(self, joints, members, E, A, 
                 constraints, loads):
        self.TOL = 1e-6

        self.joints = np.array(joints)
        self.n_joints, self.dim = np.shape(self.joints)

        self.members = np.array(members, dtype=int)
        self.n_members, self.npe = np.shape(members)

        if type(E) == np.ndarray:
            self.Es = np.array(E)
        elif type(E) == list:
            self.Es = np.array(E)
        else:
            self.Es = E*np.ones(self.n_members)

        if type(A) == np.ndarray:
            self.As = np.array(A)
        elif type(A) == list:
            self.As = np.array(A)
        else:
            self.As = A*np.ones(self.n_members)

        self.joint_constraints=constraints
        self.loads = loads

        self.strains = np.zeros(self.n_members)
        self.stresses = np.zeros(self.n_members)

        self.Ls = self.compute_lengths()
        self.dcos = self.compute_direction_cosines()

        self.n_dofs = self.dim*self.n_joints
        self.dofs = np.zeros(self.n_dofs)

        self.K = np.zeros((self.n_dofs, self.n_dofs))
        self.F = np.zeros(self.n_dofs)

    def length(self, idx):
        id1, id2 = self.members[idx]
        coords1 = self.joints[id1]
        coords2 = self.joints[id2]
        return np.sqrt(np.sum((coords2 - coords1)**2))
    
    def dircos(self, idx):
        id1, id2 = self.members[idx]
        coords1 = self.joints[id1]
        coords2 = self.joints[id2]
        dr = np.sqrt(np.sum((coords2 - coords1)**2))
        return (coords2 - coords1)/dr

    def compute_lengths(self):
        Ls = np.zeros(self.n_members)
        for i in range(self.n_members):
            Ls[i] = self.length(i)
        return Ls
    
    def compute_direction_cosines(self):
        dcos = np.zeros((self.n_members, self.dim))
        for i in range(self.n_members):
            dcos[i] = self.dircos(i)
        return dcos

    def apply_constraints(self):
        clist = []
        for c in self.joint_constraints:
            self.dofs[self.dim*c[0] + c[1]] = c[2]
            clist.append(self.dim*c[0] + c[1])
        self.constraints = np.array(clist, dtype=int)

    def apply_loads(self):
        for l in self.loads:
            self.F[self.dim*l[0] + l[1]] = l[2]

    def compute_strains(self):
        for i in range(self.n_members):
            self.strains[i] = 0.0
            dcos = self.dcos[i]
            id1, id2 = self.members[i]
            for j in range(self.dim):
                self.strains[i] += dcos[j]*(
                    self.dofs[self.dim*id2 + j] 
                  - self.dofs[self.dim*id1 + j]
                )/self.Ls[i]

    def member_stiffness(self, idx):
        dcos = self.dcos[idx]
        if self.dim == 2:
            T = np.array([
                [dcos[0], dcos[1], 0, 0],
                [0, 0, dcos[0], dcos[1]]
            ])
        elif self.dim == 3:
            T = np.array([
                [dcos[0], dcos[1], dcos[2], 0, 0, 0],
                [0, 0, 0, dcos[0], dcos[1], dcos[2]]
            ])
        ke = (self.Es[idx]*self.As[idx]/self.Ls[idx])*np.array([
            [1, -1],
            [-1, 1]
        ])
        return T.T @ (ke @ T)

    def compute_stiffness(self):
        for i in range(self.n_members):
            K_member = self.member_stiffness(i)

            id1, id2 = self.members[i]
            if self.dim == 2:
                ids = [
                    self.dim*id1,
                    self.dim*id1 + 1,
                    self.dim*id2,
                    self.dim*id2 + 1,
                ]
            elif self.dim == 3:
                ids = [
                    self.dim*id1,
                    self.dim*id1 + 1,
                    self.dim*id1 + 2,
                    self.dim*id2,
                    self.dim*id2 + 1,
                    self.dim*id2 + 2
                ]

            for j in range(self.npe*self.dim):
                for k in range(self.npe*self.dim):
                    self.K[ids[j], ids[k]] += K_member[j, k]

    def enforce_constraints(self):
        n_support = 0
        K_support = []
        for i in range(self.n_dofs):
            if i in self.constraints:
                n_support += 1
                K_support.append(np.array(self.K[i]))
        self.n_support = n_support
        self.K_support = np.array(K_support)

        for i in range(self.n_dofs):
            if i in self.constraints:
                for j in range(self.n_dofs):
                    if j == i:
                        self.K[i, j] = 1.0
                    else:
                        self.K[i, j] = 0.0
                        self.K[j, i] = 0.0

    def compute_reactions(self):
        reactions = np.zeros(self.n_support)
        for i in range(self.n_support):
            reactions[i] = self.K_support[i] @ self.dofs
        self.reactions = reactions

    def compute_stresses(self):
        self.compute_strains()
        self.stresses = self.Es*self.strains

    def solve(self):
        self.compute_stiffness()
        self.apply_loads()

        self.apply_constraints()
        self.enforce_constraints()

        self.dofs = np.linalg.solve(self.K, self.F)

        self.compute_reactions()
        self.compute_stresses()

    def print_displacements(self, idx=None):
        if idx is None:
            for i in range(self.n_joints):
                if self.dim == 2:
                    print(f'{i+1}: [{self.dofs[2*i]}, {self.dofs[2*i+1]}]')
                elif self.dim == 3:
                    print(f'{i+1}: [{self.dofs[3*i]}, {self.dofs[3*i+1]}, {self.dofs[3*i+2]}]')
        else:
            if isinstance(idx, np.ndarray) or isinstance(idx, list):
                for i in idx:
                    if self.dim == 2:
                        print(f'{i}: [{self.dofs[2*(i-1)]}, {self.dofs[2*(i-1)+1]}]')
                    elif self.dim == 3:
                        print(f'{i}: [{self.dofs[3*(i-1)]}, {self.dofs[3*(i-1)+1]}, {self.dofs[3*(i-1)+2]}]')
            
            else:
                if self.dim == 2:
                    print(f'{idx}: [{self.dofs[2*(idx-1)]}, {self.dofs[2*(idx-1)+1]}]')
                elif self.dim == 3:
                    print(f'{idx}: [{self.dofs[3*(idx-1)]}, {self.dofs[3*(idx-1)+1]}, {self.dofs[3*(idx-1)+2]}]')

    def print_stresses(self, idx=None):
        if idx is None:
            for i in range(self.n_members):
                print(f'{i+1}: {self.stresses[i]}')
        else:
            if isinstance(idx, np.ndarray) or isinstance(idx, list):
                for i in idx:
                    print(f'{i}: {self.stresses[i-1]}')
            else:
                print(f'{idx}: {self.stresses[idx-1]}')
    
    def _set_equal_axes(self, ax):
        """
        Force equal axis scaling (optional).
        """
        if self.dim == 2:
            ax.set_aspect('equal', adjustable='box')

        elif self.dim == 3:
            x_limits = ax.get_xlim3d()
            y_limits = ax.get_ylim3d()
            z_limits = ax.get_zlim3d()

            x_range = abs(x_limits[1] - x_limits[0])
            y_range = abs(y_limits[1] - y_limits[0])
            z_range = abs(z_limits[1] - z_limits[0])

            max_range = max(x_range, y_range, z_range) / 2

            x_mid = np.mean(x_limits)
            y_mid = np.mean(y_limits)
            z_mid = np.mean(z_limits)

            ax.set_xlim3d([x_mid - max_range, x_mid + max_range])
            ax.set_ylim3d([y_mid - max_range, y_mid + max_range])
            ax.set_zlim3d([z_mid - max_range, z_mid + max_range])
    
    def draw(self, equal_axes=False):
        if self.dim == 2:
            _ = plt.figure()
            for i in range(self.n_members):
                id1, id2 = self.members[i]
                plt.plot(
                    [self.joints[id1, 0], self.joints[id2, 0]],
                    [self.joints[id1, 1], self.joints[id2, 1]],
                    '-', color='blue', linewidth=2
                )
            plt.scatter(self.joints[:,0], self.joints[:,1], c='red', s=20)
            plt.xlabel('x')
            plt.ylabel('y')
            self._set_equal_axes(ax)
            plt.show()
            

        elif self.dim == 3:
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')

            for i in range(self.n_members):
                id1, id2 = self.members[i]
                ax.plot(
                    [self.joints[id1, 0], self.joints[id2, 0]],
                    [self.joints[id1, 1], self.joints[id2, 1]],
                    [self.joints[id1, 2], self.joints[id2, 2]],
                    '-', color='blue', linewidth=2)

            ax.scatter(
                self.joints[:,0], self.joints[:,1], self.joints[:,2],
                c='red', s=20
            )

            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_zlabel('z')
            self._set_equal_axes(ax)
            plt.show()
            

    def plot(self, structure=True, magnification=1, 
             slice_axis='X', lo=-np.inf, hi=np.inf,
             equal_axes=False):
        slice_dir = -1

        if slice_axis == 'X':
            slice_dir = 0
        elif slice_axis == 'Y':
            slice_dir = 1
        elif slice_axis == 'Z':
            slice_dir = 2

        assert slice_dir >= 0, "Slice axis should be X, Y, or Z."

        fig = plt.figure()

        smin = min(self.stresses)
        smax = max(self.stresses)
        sref = max(-smin, smax)
        cmap_t = cm.Blues
        cmap_c = cm.Reds

        if self.dim == 2:
            ax = fig.add_subplot()
            ax.set_xlabel('x')
            ax.set_ylabel('y')

            if structure:
                for i in range(self.n_members):
                    id1, id2 = self.members[i]
                    ax.plot(
                        [self.joints[id1, 0], self.joints[id2, 0]],
                        [self.joints[id1, 1], self.joints[id2, 1]],
                        '--', color='lightgray', linewidth=1
                    )

                ax.scatter(self.joints[:,0], self.joints[:,1],
                           c='lightgray', s=10)

            for i in range(self.n_members):
                id1, id2 = self.members[i]
                x1 = self.joints[id1, 0] + magnification*self.dofs[2*id1 + 0]
                y1 = self.joints[id1, 1] + magnification*self.dofs[2*id1 + 1]
                x2 = self.joints[id2, 0] + magnification*self.dofs[2*id2 + 0]
                y2 = self.joints[id2, 1] + magnification*self.dofs[2*id2 + 1]

                lw = 3
                color = 'lightgray'
                if self.stresses[i] > self.TOL:
                    color = cmap_t(self.stresses[i]/sref)
                elif self.stresses[i] < -self.TOL:
                    color = cmap_c(-self.stresses[i]/sref)

                ax.plot(
                    [x1, x2], [y1, y2],
                    '-', linewidth=lw,
                    c=color
                )

            for i in range(self.n_joints):
                ax.scatter(
                    [self.joints[i,0] + magnification*self.dofs[2*i + 0]],
                    [self.joints[i,1] + magnification*self.dofs[2*i + 1]],
                    c='k', s=20
                )

        elif self.dim == 3:
            ax = fig.add_subplot(projection='3d')
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_zlabel('z')

            id_lo = np.where(self.joints[:,slice_dir] >= lo)[0]
            id_hi = np.where(self.joints[:,slice_dir] <= hi)[0]
            id_sec = np.intersect1d(id_lo, id_hi)
            sec_members = []
            id_mem = []
            for i, member in enumerate(self.members):
                if member[0] in id_sec and member[1] in id_sec:
                    sec_members.append(member)
                    id_mem.append(i)
            sec_members = np.array(sec_members, dtype=int)
            id_mem = np.array(id_mem, dtype=int)

            if structure:
                for i in range(self.n_members):
                    id1, id2 = self.members[i]
                    ax.plot(
                        [self.joints[id1, 0], self.joints[id2, 0]],
                        [self.joints[id1, 1], self.joints[id2, 1]],
                        [self.joints[id1, 2], self.joints[id2, 2]],
                        '--', color='lightgray', linewidth=1)

                ax.scatter(
                    self.joints[:,0], self.joints[:,1], self.joints[:,2],
                    c='lightgray', s=5
                )

            for i in range(len(sec_members)):
                id1, id2 = sec_members[i]
                x1 = self.joints[id1, 0] + magnification*self.dofs[3*id1 + 0]
                y1 = self.joints[id1, 1] + magnification*self.dofs[3*id1 + 1]
                z1 = self.joints[id1, 2] + magnification*self.dofs[3*id1 + 2]
                x2 = self.joints[id2, 0] + magnification*self.dofs[3*id2 + 0]
                y2 = self.joints[id2, 1] + magnification*self.dofs[3*id2 + 1]
                z2 = self.joints[id2, 2] + magnification*self.dofs[3*id2 + 2]

                lw = 3
                color = 'lightgray'
                if self.stresses[id_mem[i]] > self.TOL:
                    color = cmap_t(self.stresses[id_mem[i]]/sref)
                elif self.stresses[id_mem[i]] < -self.TOL:
                    color = cmap_c(-self.stresses[id_mem[i]]/sref)

                ax.plot(
                    [x1, x2], [y1, y2], [z1, z2],
                    '-', linewidth=lw,
                    c=color
                )

            for i in id_sec:
                ax.scatter(
                    [self.joints[i,0] + magnification*self.dofs[3*i + 0]],
                    [self.joints[i,1] + magnification*self.dofs[3*i + 1]],
                    [self.joints[i,2] + magnification*self.dofs[3*i + 2]],
                    c='k', s=10
                )
        if equal_axes:
            self._set_equal_axes(ax)
        plt.show()
    
    

def _extrude(joints_cs, members_cs, dz, nz, Es_cs, As_cs, xtype=0, xdim=2):
    joints = copy.deepcopy(joints_cs)
    members = copy.deepcopy(members_cs)
    Es = copy.deepcopy(Es_cs)
    As = copy.deepcopy(As_cs)

    n_cs = len(joints_cs)

    for i in range(nz):
        for joint in joints_cs:
            new_joint = copy.copy(joint)
            new_joint[xdim] += (i + 1) * dz
            joints.append(new_joint)

    for i in range(nz):
        for j, member in enumerate(members_cs):
            new_member = copy.copy(member)
            new_member[0] += (i + 1) * n_cs
            new_member[1] += (i + 1) * n_cs
            members.append(new_member)
            Es.append(Es_cs[j])
            As.append(As_cs[j])

    for i in range(nz):
        for j in range(n_cs):
            members.append([i*n_cs + j, (i+1)*n_cs + j])
            Es.append(Es_cs[0]) # arbitrary choice!
            As.append(As_cs[0]) # arbitrary choice!

    for i in range(nz):
        for j, member in enumerate(members_cs):
            j1 = member[0]
            j2 = member[1]
            if xtype == 0:
                members.append([i*n_cs + j1, (i+1)*n_cs + j2])
                Es.append(Es_cs[j])
                As.append(As_cs[j])
            elif xtype == 1:
                members.append([i*n_cs + j2, (i+1)*n_cs + j1])
                Es.append(Es_cs[j])
                As.append(As_cs[j])
            elif xtype == 2:
                members.append([i*n_cs + j1, (i+1)*n_cs + j2])
                Es.append(Es_cs[j])
                As.append(As_cs[j])
                members.append([i*n_cs + j2, (i+1)*n_cs + j1])
                Es.append(Es_cs[j])
                As.append(As_cs[j])

    return joints, members, Es, As


def setup_truss(filename):
    joints = []
    members = []
    constraints = []
    loads = []
    Es = []
    As = []

    dim = 0
    n_joints = 0
    n_members = 0
    n_constraints = 0
    n_loads = 0
    n_layers = 0
    depth = 0.0

    with open(filename, 'r') as f:
        # Dimension
        line = f.readline() # Start of Block 1
        words = line.split()
        assert words[0] == 'DIM', 'Block 1 Line 1 should start with DIM.'
        
        if int(words[1]) == 2:
            dim = 2
        elif int(words[1]) == 3:
            dim = 3

        line = f.readline() # End of Block 1

        # Extrusion information
        line = f.readline() # Start of Block 2
        words = line.split()
        assert words[0] == 'EXTRUDE', 'Block 2 Line 1 should start with EXTRUDE.'

        extrude_dir = -1
        if words[1] == 'X':
            extrude_dir = 0
        elif words[1] == 'Y':
            extrude_dir = 1
        elif words[1] == 'Z':
            extrude_dir = 2

        line = f.readline()
        words = line.split()
        assert words[0] == 'PATTERN', 'Block 2 Line 2 should start with PATTERN.'

        extrude_type = -1
        if extrude_dir >= 0:
            if words[1] == 'FORWARD':
                extrude_type = 0
            elif words[1] == 'BACKWARD':
                extrude_type = 1
            elif words[1] == 'CROSS':
                extrude_type = 2

        line = f.readline()
        words = line.split()
        assert words[0] == 'LAYERS', 'Block 2 Line 3 should start with LAYERS.'

        if extrude_dir >= 0:
            n_layers = int(words[1])

        line = f.readline()
        words = line.split()
        assert words[0] == 'DEPTH', 'Block 2 Line 4 should start with DEPTH.'

        if extrude_dir >= 0:
            depth = float(words[1])

        line = f.readline() # End of Block 2

        # Joints
        line = f.readline() # Start of Block 3
        words = line.split()
        assert words[0] == 'JOINTS', 'Block 3 Line 1 should start with JOINTS.'

        n_joints = int(words[1])
        
        if dim == 2:
            for _ in range(n_joints):
                line = f.readline()
                words = line.split()
                joints.append([float(words[1]), float(words[2])])
        elif dim == 3:
            if extrude_dir >= 0:
                if extrude_dir == 0:
                    for _ in range(n_joints):
                        line = f.readline()
                        words = line.split()
                        joints.append([0.0, float(words[1]), float(words[2])])
                elif extrude_dir == 1:
                    for _ in range(n_joints):
                        line = f.readline()
                        words = line.split()
                        joints.append([float(words[1]), 0.0, float(words[2])])
                elif extrude_dir == 2: 
                    for _ in range(n_joints):
                        line = f.readline()
                        words = line.split()
                        joints.append([float(words[1]), float(words[2]), 0.0])
            else:
                for _ in range(n_joints):
                    line = f.readline()
                    words = line.split()
                    joints.append([float(words[1]), float(words[2]), float(words[3])])

        line = f.readline() # End of Block 3

        # Members
        line = f.readline() # Start of Block 4
        words = line.split()
        assert words[0] == 'MEMBERS', 'Block 4 Line 1 should start with MEMBERS.'

        n_members = int(words[1])

        for _ in range(n_members):
            line = f.readline()
            words = line.split()
            members.append([int(words[1])-1, int(words[2])-1])
            Es.append(float(words[3]))
            As.append(float(words[4]))

        if extrude_dir >= 0:
            joints, members, Es, As = _extrude(
                joints, members, depth, n_layers, Es, As, 
                extrude_type, extrude_dir
            )

        line = f.readline() # End of Block 4

        # Constraints
        line = f.readline() # Start of Block 5
        words = line.split()
        assert words[0] == 'CONSTRAINTS', 'Block 5 Line 1 should start with CONSTRAINTS.'

        n_constraints = int(words[1])

        for _ in range(n_constraints):
            line = f.readline()
            words = line.split()
            c_node = int(words[1]) - 1
            c_axis = words[2]
            c_val = float(words[3])

            c_dir = -1

            if c_axis == 'X':
                c_dir = 0
            elif c_axis == 'Y':
                c_dir = 1

            if dim == 3:
                if c_axis == 'Z':
                    c_dir = 2
            
            if dim == 2:
                assert c_dir >= 0, 'Constraint direction should be X or Y.'
            elif dim == 3:
                assert c_dir >= 0, 'Constraint direction should be X or Y or Z.'

            constraints.append([c_node, c_dir, c_val])

        line = f.readline() # End of Block 5
            
        # Loads
        line = f.readline() # Start of Block 6
        words = line.split()
        assert words[0] == 'LOADS', 'Block 6 Line 1 should start with LOADS.'

        n_loads = int(words[1])

        for _ in range(n_loads):
            line = f.readline()
            words = line.split()
            l_node = int(words[1]) - 1
            l_axis = words[2]
            l_val = float(words[3])

            l_dir = -1

            if l_axis == 'X':
                l_dir = 0
            elif l_axis == 'Y':
                l_dir = 1

            if dim == 3:
                if l_axis == 'Z':
                    l_dir = 2
            
            if dim == 2:
                assert l_dir >= 0, 'Load direction should be X or Y.'
            elif dim == 3:
                assert l_dir >= 0, 'Load direction should be X or Y or Z.'

            loads.append([l_node, l_dir, l_val])

        # End of Block 6

    return Truss(joints, members, Es, As, constraints, loads)
