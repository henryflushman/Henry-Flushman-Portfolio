import sys, math, pygame, random

pygame.init()

width, height = 1000, 500
black = (0, 0, 0)

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Realistic Motion of a Circle")

try:
    ball_orig = pygame.image.load('Personal Projects/Basketball_Simulator/basketball.png').convert_alpha()
    ball_orig = pygame.transform.rotozoom(ball_orig, 0, .1)
    bg_raw = pygame.image.load('Personal Projects/Basketball_Simulator/basketball_court.jpg').convert()  # no alpha, fastest blits
    bg = pygame.transform.smoothscale(bg_raw, (width, height))
except Exception:
    # Fallback: draw a nice circle if the image is missing
    size = 64
    ball_orig = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(ball_orig, (220, 235, 255), (size//2, size//2), size//2)
    bg_raw = pygame.image.load('Personal Projects/Basketball_Simulator/basketball_court.jpg').convert()  # no alpha, fastest blits
    bg = pygame.transform.smoothscale(bg_raw, (width, height))
    
""" Ball Characteristics """
mass = 1000
grav = 800
r = max(ball_orig.get_width(), ball_orig.get_height()) / 2
I = .5 * mass * r**2
e = .9
mu = .8

""" Initial Values """
pos = pygame.Vector2(width//2, height//2)
vel = pygame.Vector2(1000, 0)
omega = math.radians(100)
angle = 0
onfloor = False

""" Anti-jitter thresholds """
VN_EPS = 1e-2          # approach test
PEN_TOL = 0.5           # px
V_BOUNCE_STOP_FLOOR = 40   # px/s  → only floor: below this, treat as inelastic
V_GROUNDED = 8.0             # px/s  → only floor: consider "grounded" if |vy| below this
ROLL_SLIP_EPS = 1e-4

""" Counters """
clock = pygame.time.Clock()
ongroundtime = 0

running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    vel.y += grav * dt
    pos.y += vel.y * dt

    pos.x = pos.x + vel.x * dt

    hit_left = hit_right = hit_floor = hit_ceil = False
    n_left = t_left = n_right = t_right = n_floor = t_floor = n_ceil = t_ceil = None

    if pos.x + r > width:
        pos.x = width - r
        # Right Wall
        n_right = pygame.Vector2(-1,0)
        t_right = pygame.Vector2(0,-1)
        hit_right = True
    elif pos.x - r < 0:
        pos.x = r
        # Left Wall
        n_left = pygame.Vector2(1,0)
        t_left = pygame.Vector2(0,1)
        hit_left = True

    if pos.y + r > height:
        pos.y = height - r
        # Floor
        n_floor = pygame.Vector2(0,-1)
        t_floor = pygame.Vector2(1,0)
        hit_floor = True
    elif pos.y - r < 0:
        pos.y = r
        # Ceiling
        n_ceil = pygame.Vector2(0,1)
        t_ceil = pygame.Vector2(-1,0)
        hit_ceil = True

    """ Impulse Function """
    def apply_impulse(n, t, is_floor=False):
        global vel, omega, onfloor
        v_n = vel.dot(n)
        if v_n < -VN_EPS:
            e_eff = 0 if (is_floor and (-v_n) < V_BOUNCE_STOP_FLOOR) else e

            Jn = -(1 + e_eff) * mass * v_n

            v_t = vel.dot(t)
            u_t_minus = v_t + omega * r

            denom = (1.0 / mass) + (r * r) / I
            Jt_star = -u_t_minus / denom
            Jt_max = mu * abs(Jn)
            Jt = max(-Jt_max, min(Jt_star, Jt_max))

            vel += (Jn * n + Jt * t) / mass
            omega += (r * Jt) / I

            if is_floor:
                vn_after = vel.dot(n)
                if abs(vn_after) < V_GROUNDED:
                    vel -= vn_after * n
                    onfloor = True

    if hit_left:  apply_impulse(n_left, t_left, is_floor=False)
    if hit_right: apply_impulse(n_right, t_right, is_floor=False)
    if hit_floor: apply_impulse(n_floor, t_floor, is_floor=True)
    if hit_ceil:  apply_impulse(n_ceil, t_ceil, is_floor=False)

    if (pos.y + r >= height - PEN_TOL) and (abs(vel.y) <= V_GROUNDED):
        pos.y = height - r
        vel.y = 0.0
        onfloor = True
    else:
        if pos.y + r < height - PEN_TOL:
            onfloor = False

    if onfloor:
        # Kinetic friction on floor to reduce slip toward rolling w/o slipping
        # Slip = CM tangential speed - rim speed
        slip = vel.x - omega * r
        if abs(slip) > ROLL_SLIP_EPS:
            N = mass * abs(grav)  # normal force magnitude
            f = -mu * N * math.copysign(1.0, slip)  # opposes slip
            dvx = (f / mass) * dt
            domega = -(f * r / I) * dt

            next_slip = (vel.x + dvx) - (omega + domega) * r

            if slip * next_slip < 0 or abs(next_slip) < 1e-6:
                v_roll = .5 * (vel.x + omega * r)
                vel.x = v_roll
                omega = v_roll / r
            else:
                vel.x += dvx
                omega += domega

        ongroundtime += 1

        if ongroundtime > 120:
            ongroundtime = 0
            onfloor = False
            pos = pygame.Vector2(width//2, height//2)
            vel = pygame.Vector2(random.randint(-1000, 1000), random.randint(-1000, 1000))
            omega = math.radians(random.randint(-200, 200))
            angle = 0

    angle = angle + omega * dt
    angle_true = math.degrees(angle)

   # vel *= .999
   # omega *= .999



    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    accel = 1000.0  # px/s^2 (tune this)

    if keys[pygame.K_LEFT]:
        vel.x -= accel * dt
    if keys[pygame.K_RIGHT]:
        vel.x += accel * dt
    if keys[pygame.K_a]:
        omega += math.radians(90) * dt  # spin up CCW
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
        angle = 0
    if keys[pygame.K_q]:
        vel *= 1.05

    ball_rot = pygame.transform.rotozoom(ball_orig, angle_true, 1)
    ballrect = ball_rot.get_rect(center=(int(pos.x), int(pos.y)))

    screen.blit(bg, (0,0))
    screen.blit(ball_rot, ballrect)
    pygame.display.flip()


pygame.quit()
sys.exit()