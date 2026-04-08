import sys, math, pygame, random, os

os.system('cls')

pygame.init()

width, height = 1000, 500
black = (0, 0, 0)

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Realistic Motion of an Oval")

# ---------- Draw a centered oval on a tightly-sized surface ----------
w, h = 10, 50  # ellipse width/height in pixels (tall oval)
ball_orig = pygame.Surface((w, h), pygame.SRCALPHA)
pygame.draw.ellipse(ball_orig, (220, 235, 255), (0, 0, w, h))  # fills the surface exactly

bg = pygame.Surface((width, height)).convert()
bg.fill(black)

""" Physical parameters """
mass = 1000.0
grav = 800.0

# Semi-axes in local body frame
a = 0.5 * w
b = 0.5 * h

# Planar inertia for a solid elliptical lamina about the out-of-plane axis
I = 0.25 * mass * (a*a + b*b)

e = 0.5           # restitution
mu = 0.41          # Coulomb friction coefficient
air_damping = 0.9995      # mild global linear damping per frame
rot_damping = 0.9995      # mild global angular damping per frame
rolling_resist = 0.002     # small torque (μ-like) opposing rotation when grounded

""" State """
pos = pygame.Vector2(width//2, height//2)    # center of mass
vel = pygame.Vector2(1000.0, 0.0)
omega = math.radians(100.0)  # rad/s
angle = 0.0                  # rad
onfloor = False

""" Anti-jitter thresholds """
VN_EPS = 1e-2
PEN_TOL = 0.5
V_BOUNCE_STOP_FLOOR = 40.0
V_GROUNDED = 8.0
ROLL_SLIP_EPS = 1e-4

clock = pygame.time.Clock()
ongroundtime = 0
running = True

# ---------- Ellipse contact geometry helpers ----------
def body_dir_from_world_down(theta: float):
    """World down (0,-1) expressed in body coordinates (rotate by -theta)."""
    # R(-θ) * (0,-1) = (sinθ, -cosθ)
    return (math.sin(theta), -math.cos(theta))

def support_param_for_dir(dx: float, dy: float) -> float:
    """
    For ellipse x(u)=(a cos u, b sin u), support in direction d=(dx,dy) maximizes a*dx*cos u + b*dy*sin u.
    Condition: -a*dx*sin u + b*dy*cos u = 0  =>  tan u = (b*dy)/(a*dx).
    Use atan2 for robustness.
    """
    return math.atan2(b * dy, a * dx)

def support_point_and_height(theta: float):
    """Return (px, py, h_contact) where (px,py) is the contact point in BODY coords,
    and h_contact is the distance from center to boundary along world-down direction."""
    dx, dy = body_dir_from_world_down(theta)
    u = support_param_for_dir(dx, dy)
    px = a * math.cos(u)
    py = b * math.sin(u)
    # height along direction d = p · d  (in body coords)
    h_contact = px * dx + py * dy
    return u, px, py, h_contact

def radius_of_curvature_at_u(u: float) -> float:
    """
    Radius of curvature for axis-aligned ellipse at parameter u:
    ρ(u) = ((a^2 sin^2 u + b^2 cos^2 u)^(3/2)) / (a*b)
    """
    s = math.sin(u); c = math.cos(u)
    denom = a * b
    q = (a*a * s*s + b*b * c*c)
    return (q ** 1.5) / max(1e-9, denom)

# -----------------------------------------

while running:
    dt = clock.tick(60) / 1000.0

    # events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # global light damping (helps it settle)
    vel *= air_damping
    omega *= rot_damping

    # integrate
    vel.y += grav * dt
    pos += vel * dt

    # update rotation
    angle += omega * dt
    angle_true = math.degrees(angle)

    # render-ready transform + rect from pos
    ball_rot = pygame.transform.rotozoom(ball_orig, angle_true, 1)
    ballrect = ball_rot.get_rect(center=(int(pos.x), int(pos.y)))

    # ---------- MASK-BASED WALL COLLISION ----------
    ball_mask = pygame.mask.from_surface(ball_rot)
    outline_pts = ball_mask.outline()
    if not outline_pts:  # degenerate fallback
        outline_pts = [(0, 0),
                       (ballrect.width-1, 0),
                       (0, ballrect.height-1),
                       (ballrect.width-1, ballrect.height-1)]

    min_x, min_y = 10**9, 10**9
    max_x, max_y = -10**9, -10**9
    for (px, py) in outline_pts:
        sx = ballrect.left + px
        sy = ballrect.top  + py
        if sx < min_x: min_x = sx
        if sx > max_x: max_x = sx
        if sy < min_y: min_y = sy
        if sy > max_y: max_y = sy

    pen_left  = max(0, 0 - min_x)
    pen_right = max(0, max_x - (width - 1))
    pen_top   = max(0, 0 - min_y)
    pen_bot   = max(0, max_y - (height - 1))

    hit_left = hit_right = hit_floor = hit_ceil = False
    n_left = t_left = n_right = t_right = n_floor = t_floor = n_ceil = t_ceil = None

    if pen_left > ballrect.width:
        pos.x = width + px
        n_left = pygame.Vector2(1, 0)
        t_left = pygame.Vector2(0, 1)

    if pen_right > ballrect.width:
        pos.x = -px
        n_right = pygame.Vector2(-1, 0)
        t_right = pygame.Vector2(0, -1)

    if pen_bot > 0:
        pos.y -= pen_bot
        hit_floor = True
        n_floor = pygame.Vector2(0, -1)
        t_floor = pygame.Vector2(1, 0)

    if pen_top > 0:
        pos.y += pen_top
        hit_ceil = True
        n_ceil = pygame.Vector2(0, 1)
        t_ceil = pygame.Vector2(-1, 0)

    # Rebuild rect after any penetration correction
    ballrect = ball_rot.get_rect(center=(int(pos.x), int(pos.y)))

    """ Impulse Function """
    def apply_impulse(n, t, is_floor=False):
        global vel, omega, onfloor
        v_n = vel.dot(n)
        if v_n < -VN_EPS:
            e_eff = 0 if (is_floor and (-v_n) < V_BOUNCE_STOP_FLOOR) else e
            Jn = -(1 + e_eff) * mass * v_n

            # Tangential relative velocity at contact:
            # USE h_contact (lever arm), not R_roll.
            if is_floor:
                _, _, _, h_c = support_point_and_height(angle)
                lever = h_c
            else:
                # for walls/ceiling just approximate by max lever arm
                # (could compute wall-specific support similarly if desired)
                lever = max(a, b)

            v_t = vel.dot(t)
            u_t_minus = v_t + omega * lever

            denom = (1.0 / mass) + (lever * lever) / I
            Jt_star = -u_t_minus / denom
            Jt_max = mu * abs(Jn)
            Jt = max(-Jt_max, min(Jt_star, Jt_max))

            vel += (Jn * n + Jt * t) / mass
            omega += (lever * Jt) / I

            if is_floor:
                vn_after = vel.dot(n)
                if abs(vn_after) < V_GROUNDED:
                    vel -= vn_after * n
                    onfloor = True

    # apply impulses based on contacts
    if hit_left:  apply_impulse(n_left,  t_left,  is_floor=False)
    if hit_right: apply_impulse(n_right, t_right, is_floor=False)
    if hit_floor: apply_impulse(n_floor, t_floor, is_floor=True)
    if hit_ceil:  apply_impulse(n_ceil,  t_ceil,  is_floor=False)

    # ---------- Grounded handling with true ellipse geometry ----------
    # contact height and rolling radius at the actual support point
    u, _, _, h_c = support_point_and_height(angle)
    R_roll = radius_of_curvature_at_u(u)

    # grounded check using the true lowest point
    lowest_y = pos.y + h_c
    if (lowest_y >= height - PEN_TOL) and (abs(vel.y) <= V_GROUNDED):
        pos.y = height - h_c
        vel.y = 0.0
        onfloor = True
    else:
        if lowest_y < height - PEN_TOL:
            onfloor = False

    if onfloor:
        # Slip relative to correct rolling kinematics (v = ω R_roll)
        slip = vel.x - omega * R_roll

        if abs(slip) > ROLL_SLIP_EPS:
            # Friction force capped by μN
            N = mass * abs(grav)
            f_cap = mu * N

            # Try to remove slip smoothly within this frame, but cap it
            desired_f = -math.copysign(min(f_cap, abs(slip) * mass / max(1e-6, dt)), slip)

            # Linear/angular response: torque lever is h_contact
            dvx = (desired_f / mass) * dt
            domega = -(desired_f * h_c / I) * dt

            next_slip = (vel.x + dvx) - (omega + domega) * R_roll

            if slip * next_slip < 0 or abs(next_slip) < 1e-6:
                # snap exactly to rolling w/o slip
                v_roll = 0.5 * (vel.x + omega * R_roll)
                vel.x = v_roll
                omega = v_roll / R_roll if R_roll > 1e-6 else omega
            else:
                vel.x += dvx
                omega += domega

        # rolling resistance: tiny torque opposing rotation, helps it settle on its side
        if abs(omega) > 1e-5:
            tau_rr = -rolling_resist * mass * abs(grav) * R_roll * math.copysign(1.0, omega)
            omega += (tau_rr / I) * dt

        ongroundtime += 1
        
    # input
    keys = pygame.key.get_pressed()
    accel = 1000.0

    if keys[pygame.K_LEFT]:
        vel.x -= accel * dt
    if keys[pygame.K_RIGHT]:
        vel.x += accel * dt
    if keys[pygame.K_a]:
        omega += math.radians(90) * dt
    if keys[pygame.K_d]:
        omega -= math.radians(90) * dt
    if keys[pygame.K_UP]:
        vel.y -= accel * dt
    if keys[pygame.K_DOWN]:
        vel.y += accel * dt
    if keys[pygame.K_SPACE]:
        ongroundtime = 0
        onfloor = False
        pos = pygame.Vector2(width // 2, height // 2)
        vel = pygame.Vector2(random.randint(-1000, 1000), random.randint(-1000, 1000))
        omega = math.radians(random.randint(-200, 200))
        angle = 0.0
    if keys[pygame.K_q]:
        vel *= 1.05
    if keys[pygame.K_e]:
        omega *= 1.05

    # draw
    screen.blit(bg, (0, 0))
    screen.blit(ball_rot, ballrect)
    pygame.display.flip()

pygame.quit()
sys.exit()
