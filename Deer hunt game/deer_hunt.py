import pygame
import random
import math
import sys
import os

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# ── Constants ──────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS  = 60
WHITE   = (255, 255, 255)
BLACK   = (0,   0,   0)
RED     = (220,  30,  30)
GREEN   = ( 34, 139,  34)
DGREEN  = ( 0,  100,   0)
BROWN   = (139,  90,  43)
DBROWN  = ( 90,  60,  20)
SKY1    = ( 30, 100, 180)
SKY2    = ( 80, 160, 230)
ORANGE  = (255, 140,   0)
YELLOW  = (255, 220,  50)
CREAM   = (255, 240, 200)
GRAY    = (160, 160, 160)
LGRAY   = (210, 210, 210)
DGRAY   = ( 80,  80,  80)
GOLD    = (255, 200,   0)
PINK    = (255, 100, 100)

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("🦌  DEER HUNTER  🎯")
clock = pygame.time.Clock()

# ── Sound synthesis ────────────────────────────────────────────────────────────
def make_sound(freq, duration, wave="sine", volume=0.4):
    sample_rate = 22050
    n = int(sample_rate * duration)
    buf = []
    for i in range(n):
        t = i / sample_rate
        fade = min(1.0, (n - i) / (n * 0.3))
        if wave == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave == "noise":
            v = random.uniform(-1, 1)
        elif wave == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        sample = int(v * fade * volume * 32767)
        sample = max(-32768, min(32767, sample))
        buf.append(sample)
    arr = pygame.sndarray.make_sound(
        pygame.sndarray.array(
            pygame.mixer.Sound(buffer=bytes([0]*4))
        )[:1]  # dummy – rebuilt below
    )
    # build manually
    import array as arr_mod
    data = arr_mod.array('h', buf)
    snd = pygame.mixer.Sound(buffer=bytes(data.tobytes() * 2))  # stereo
    return snd

try:
    SND_SHOOT  = make_sound(180, 0.18, "noise", 0.6)
    SND_HIT    = make_sound(300, 0.25, "square", 0.5)
    SND_MISS   = make_sound(220, 0.15, "sine", 0.3)
    SND_RELOAD = make_sound(440, 0.12, "square", 0.4)
    SND_LEVEL  = make_sound(660, 0.4,  "sine", 0.5)
    SOUNDS_OK  = True
except Exception:
    SOUNDS_OK  = False

def play(snd):
    if SOUNDS_OK:
        try: snd.play()
        except: pass

# ── Font helpers ───────────────────────────────────────────────────────────────
def font(size, bold=False):
    return pygame.font.SysFont("consolas", size, bold=bold)

F_HUGE  = font(72, True)
F_BIG   = font(40, True)
F_MED   = font(26, True)
F_SMALL = font(18)
F_TINY  = font(14)

def txt(surface, text, x, y, f, color, anchor="topleft", shadow=True):
    if shadow:
        s = f.render(text, True, (0, 0, 0))
        r = s.get_rect(**{anchor: (x+2, y+2)})
        surface.blit(s, r)
    s = f.render(text, True, color)
    r = s.get_rect(**{anchor: (x, y)})
    surface.blit(s, r)
    return r

# ── Particle system ────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=4, gravity=0.15):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = self.max_life = life
        self.size = size
        self.gravity = gravity

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.gravity
        self.vx *= 0.98
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        r = max(1, int(self.size * alpha))
        c = tuple(int(ch * alpha) for ch in self.color)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), r)

    @property
    def dead(self): return self.life <= 0

particles = []

def blood_burst(x, y, count=25):
    for _ in range(count):
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(2, 8)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed - random.uniform(0, 3)
        col = (random.randint(160,220), random.randint(0,20), random.randint(0,20))
        particles.append(Particle(x, y, vx, vy, col,
                                   random.randint(20, 45), random.randint(3,7)))

def muzzle_flash(x, y):
    for _ in range(18):
        angle = random.uniform(-0.4, 0.4)
        speed = random.uniform(4, 14)
        vx = math.cos(angle) * speed
        vy = -abs(math.sin(angle)) * speed * 0.3
        col = random.choice([(255,220,50),(255,160,0),(255,255,180)])
        particles.append(Particle(x, y, vx, vy, col, random.randint(6,14),
                                   random.randint(3,8), gravity=0.3))

def star_burst(x, y):
    for _ in range(20):
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(1, 6)
        col = random.choice([GOLD, YELLOW, WHITE, ORANGE])
        particles.append(Particle(x, y,
                                   math.cos(angle)*speed,
                                   math.sin(angle)*speed - 2,
                                   col, random.randint(25,40), random.randint(3,6), 0.05))

def smoke_puff(x, y):
    for _ in range(8):
        vx = random.uniform(-1, 1)
        vy = random.uniform(-3, -1)
        col = (random.randint(180,220),)*3
        particles.append(Particle(x, y, vx, vy, col, random.randint(15,30), random.randint(4,10), -0.02))

# ── Background ─────────────────────────────────────────────────────────────────
def build_background():
    surf = pygame.Surface((W, H))
    # sky gradient
    for y in range(H//2):
        t = y / (H//2)
        r = int(SKY1[0]*(1-t) + SKY2[0]*t)
        g = int(SKY1[1]*(1-t) + SKY2[1]*t)
        b = int(SKY1[2]*(1-t) + SKY2[2]*t)
        pygame.draw.line(surf, (r,g,b), (0,y), (W,y))

    # sun
    pygame.draw.circle(surf, (255,240,100), (900, 80), 60)
    pygame.draw.circle(surf, (255,255,180), (900, 80), 48)
    for i in range(12):
        angle = i * 30 * math.pi/180
        x1 = 900 + int(math.cos(angle)*65)
        y1 = 80  + int(math.sin(angle)*65)
        x2 = 900 + int(math.cos(angle)*90)
        y2 = 80  + int(math.sin(angle)*90)
        pygame.draw.line(surf, (255,220,50), (x1,y1), (x2,y2), 3)

    # distant mountains
    pts = [(0,300),(120,230),(240,270),(360,210),(480,250),(600,200),(720,240),(840,185),(960,225),(1080,200),(1200,230),(W,260),(W,H//2),(0,H//2)]
    pygame.draw.polygon(surf, (80,110,150), pts)
    pts2= [(0,320),(180,270),(300,290),(450,260),(600,280),(750,255),(900,270),(1050,250),(1200,270),(W,280),(W,H//2+10),(0,H//2+10)]
    pygame.draw.polygon(surf, (100,130,160), pts2)

    # ground gradient
    for y in range(H//2, H):
        t = (y - H//2) / (H//2)
        r = int(50*(1-t) + 30*t)
        g = int(120*(1-t) + 80*t)
        b = int(30*(1-t) + 15*t)
        pygame.draw.line(surf, (r,g,b), (0,y), (W,y))

    # ground detail patches
    random.seed(42)
    for _ in range(60):
        x = random.randint(0, W)
        y = random.randint(H//2+20, H-20)
        w = random.randint(30,120)
        h = random.randint(8,25)
        c = (random.randint(25,55), random.randint(90,130), random.randint(10,35))
        pygame.draw.ellipse(surf, c, (x-w//2, y-h//2, w, h))

    return surf

def draw_tree(surf, x, y, scale=1.0, seed=0):
    rng = random.Random(seed)
    # trunk
    tw = int(14*scale)
    th = int(70*scale)
    pygame.draw.rect(surf, DBROWN, (x-tw//2, y-th, tw, th))
    pygame.draw.rect(surf, BROWN,  (x-tw//2, y-th, tw//3, th))
    # foliage layers
    for i, (dy, r, col) in enumerate([
        (0,  int(55*scale), (20,100,20)),
        (-int(30*scale), int(50*scale), (30,120,30)),
        (-int(55*scale), int(42*scale), (40,140,40)),
        (-int(75*scale), int(32*scale), (50,160,50)),
    ]):
        cx = x + rng.randint(-4,4)
        cy = y - th + dy
        pygame.draw.circle(surf, col, (cx,cy), r)
        # highlight
        pygame.draw.circle(surf, (col[0]+20,col[1]+30,col[2]+10),
                           (cx-r//4, cy-r//4), r//3)

def draw_bush(surf, x, y, scale=1.0, seed=0):
    rng = random.Random(seed)
    base = (30,110,30)
    for dx,dy,r in [(-18,0,20),(18,0,20),(0,-12,22),(0,5,18)]:
        pygame.draw.circle(surf, (base[0]+rng.randint(-10,10),
                                   base[1]+rng.randint(-10,10),
                                   base[2]+rng.randint(-5,5)),
                           (int(x+dx*scale), int(y+dy*scale)), int(r*scale))

BG = build_background()

# Pre-build trees/bushes layer
DECOR = pygame.Surface((W, H), pygame.SRCALPHA)
random.seed(99)
TREE_RECTS = []
for i in range(18):
    tx = random.randint(0, W)
    ty = random.randint(H//2+20, H-80)
    sc = random.uniform(0.7, 1.4)
    draw_tree(DECOR, tx, ty, sc, i)
    TREE_RECTS.append(pygame.Rect(tx-int(20*sc), ty-int(140*sc), int(40*sc), int(140*sc)))

BUSH_RECTS = []
for i in range(25):
    bx = random.randint(0, W)
    by = random.randint(H//2+30, H-20)
    sc = random.uniform(0.6, 1.2)
    draw_bush(DECOR, bx, by, sc, i+50)
    BUSH_RECTS.append(pygame.Rect(bx-int(25*sc), by-int(30*sc), int(50*sc), int(35*sc)))

# ── Crosshair ──────────────────────────────────────────────────────────────────
class Crosshair:
    def __init__(self):
        self.x = W//2
        self.y = H//2
        self.size = 22
        self.sway = 0.0
        self.sway_vel = 0.0
        self.recoil = 0

    def update(self, mx, my):
        self.x = mx
        self.y = my
        self.sway_vel += random.uniform(-0.15, 0.15)
        self.sway_vel *= 0.9
        self.sway += self.sway_vel
        if self.recoil > 0:
            self.recoil -= 1

    def draw(self, surf, ammo):
        s = self.size + self.recoil*3
        col = RED if ammo > 0 else GRAY
        # outer ring
        pygame.draw.circle(surf, col, (self.x, self.y), s, 2)
        # crosshairs
        pygame.draw.line(surf, col, (self.x-s-8, self.y), (self.x-6, self.y), 2)
        pygame.draw.line(surf, col, (self.x+6, self.y), (self.x+s+8, self.y), 2)
        pygame.draw.line(surf, col, (self.x, self.y-s-8), (self.x, self.y-6), 2)
        pygame.draw.line(surf, col, (self.x, self.y+6), (self.x, self.y+s+8), 2)
        # center dot
        pygame.draw.circle(surf, col, (self.x, self.y), 3)

# ── Deer ───────────────────────────────────────────────────────────────────────
class Deer:
    def __init__(self, level=1):
        side = random.choice(["left","right"])
        self.dir   = 1 if side=="left" else -1
        self.x     = -120.0 if side=="left" else W+120.0
        self.y     = float(random.randint(H//2+70, H-60))
        base_speed = 1.8 + level * 0.35
        self.speed = random.uniform(base_speed, base_speed+1.5)
        self.scale = random.uniform(0.75, 1.25)
        self.anim  = random.uniform(0, 6.28)  # stagger walk phases
        self.alive = True
        self.dying = False
        self.die_timer = 0
        self.hit_flash = 0
        self.score_val = int(100 * self.scale)
        self.pause_timer = 0
        self.variant = random.randint(0, 2)   # 0=doe  1=buck  2=stag

    @property
    def rect(self):
        sc  = self.scale
        sw  = int(90*sc)
        sh  = int(58*sc)
        # body center in screen space (canvas 150w,118h, blit at midbottom)
        offset_x = int(20*sc) if self.dir == 1 else -int(20*sc)
        cx = int(self.x) - offset_x
        cy = int(self.y) - int(90*sc)
        return pygame.Rect(cx - sw//2, cy, sw, sh)

    def update(self):
        if self.dying:
            self.die_timer += 1
            return self.die_timer > 90

        if self.pause_timer > 0:
            self.pause_timer -= 1
        else:
            self.x    += self.dir * self.speed
            self.anim += self.speed * 0.12   # anim tied to walk speed
            if random.random() < 0.003:
                self.pause_timer = random.randint(30, 90)

        self.hit_flash = max(0, self.hit_flash - 1)
        if self.x < -180 or self.x > W+180:
            return True
        return False

    def draw(self, surf):
        if self.dying:
            alpha = max(0, 255 - int(self.die_timer * 2.8))
            s = self._render()
            s.set_alpha(alpha)
            surf.blit(s, s.get_rect(midbottom=(int(self.x), int(self.y))))
            return
        s = self._render()
        if self.hit_flash > 0:
            wh = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            wh.fill((255, 255, 255, 160))
            s.blit(wh, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(s, s.get_rect(midbottom=(int(self.x), int(self.y))))

    def _render(self):
        sc  = self.scale
        CW  = int(150*sc)
        CH  = int(118*sc)
        srf = pygame.Surface((CW, CH), pygame.SRCALPHA)

        pausing = self.pause_timer > 0 or self.dying

        # ── palette ──────────────────────────────────────────────────────────
        BC   = [(185,135,70),(148,100,50),(198,128,68)][self.variant]
        DARK = (max(0,BC[0]-42), max(0,BC[1]-36), max(0,BC[2]-22))
        BELY = (222,198,150)
        NOSE_C = (50,34,28)
        HOOF_C = (34,24,14)

        def p(v): return int(v*sc)   # scale helper

        # ── body bob ─────────────────────────────────────────────────────────
        bob = 0 if pausing else p(2.4 * math.sin(self.anim * 2.0))

        # ── body polygon (right-facing) ───────────────────────────────────────
        # Spine arcs from rump(x≈14) up to withers(x≈88), belly ≈y68
        body = [
            (p(14), p(52)+bob),          # rump bottom
            (p(10), p(36)+bob),          # rump top
            (p(30), p(24)+bob),          # lower back
            (p(54), p(20)+bob),          # mid-spine (peak)
            (p(78), p(25)+bob),          # withers
            (p(93), p(37)+bob),          # neck base / chest top
            (p(97), p(52)+bob),          # chest front
            (p(90), p(68)+bob),          # belly front
            (p(54), p(72)+bob),          # belly mid
            (p(22), p(70)+bob),          # belly rear
        ]
        belly_hi = [
            (p(26), p(70)+bob),
            (p(54), p(74)+bob),
            (p(83), p(70)+bob),
            (p(80), p(67)+bob),
            (p(52), p(70)+bob),
            (p(24), p(68)+bob),
        ]

        # ── diagonal gait ─────────────────────────────────────────────────────
        # Pair A (near-front + far-rear) and Pair B (far-front + near-rear)
        pA = 0.0 if pausing else math.sin(self.anim)
        pB = 0.0 if pausing else math.sin(self.anim + math.pi)

        gnd = CH - p(5)    # ground line on canvas

        def draw_leg(ax, ay, phase_v, is_front, is_far):
            # Two-segment leg: thigh → knee → hoof
            col_hi = tuple(max(0,c-18) for c in BC) if is_far else DARK
            UL = p(25)   # upper segment length
            LL = p(23)   # lower segment length

            # Upper angle from vertical
            if is_front:
                ua = 0.10 + phase_v * 0.40
            else:
                # rear leg: hock bends backward — characteristic deer look
                ua = -0.08 + phase_v * 0.34

            kx = ax + int(math.sin(ua) * UL)
            ky = ay + int(math.cos(ua) * UL)

            # Lower segment — rear has backward-angled hock
            la = ua * 0.55 + (0.10 if is_front else -0.14)
            hx = kx + int(math.sin(la) * LL)
            hy = min(ky + int(math.cos(la) * LL), gnd)

            tw = max(2, p(5))
            lw = max(2, p(4))
            pygame.draw.line(srf, col_hi, (ax, ay), (kx, ky), tw)
            pygame.draw.line(srf, HOOF_C, (kx, ky), (hx, hy), lw)
            # split hoof
            pygame.draw.ellipse(srf, HOOF_C, (hx-p(5), hy-p(3), p(10), p(5)))
            pygame.draw.line(srf, (20,14,8), (hx, hy-p(2)), (hx, hy+p(2)), 1)

        # Hip / shoulder attachment points
        fhx, fhy = p(80), p(68)+bob   # front hip
        rhx, rhy = p(30), p(68)+bob   # rear hip
        off = p(4)                     # near/far depth offset

        # ── draw order: far legs → body → near legs → neck/head ──────────────

        # 1. FAR legs (behind body)
        draw_leg(fhx - off, fhy, pB, True,  True)    # far front
        draw_leg(rhx - off, rhy, pA, False, True)    # far rear

        # 2. BODY
        pygame.draw.polygon(srf, BC,   body)
        pygame.draw.polygon(srf, BELY, belly_hi)
        pygame.draw.polygon(srf, DARK, body, max(1, p(2)))

        # White rump patch + fluffy tail
        pygame.draw.ellipse(srf, (228,218,196), (p(8), p(33)+bob, p(15), p(22)))
        pygame.draw.ellipse(srf, (245,242,234), (p(8), p(27)+bob, p(12), p(11)))

        # 3. NEAR legs (in front of body)
        draw_leg(fhx + off, fhy, pA, True,  False)   # near front
        draw_leg(rhx + off, rhy, pB, False, False)   # near rear

        # 4. NECK
        nb_x, nb_y = p(94), p(38)+bob
        nt_x, nt_y = p(120), p(15)+bob
        neck = [
            (nb_x - p(7), nb_y + p(6)),
            (nb_x + p(4), nb_y - p(7)),
            (nt_x + p(5), nt_y + p(7)),
            (nt_x - p(5), nt_y + p(13)),
        ]
        throat = [
            (nb_x - p(3), nb_y + p(5)),
            (nb_x + p(2), nb_y - p(4)),
            (nt_x + p(1), nt_y + p(10)),
            (nt_x - p(3), nt_y + p(13)),
        ]
        pygame.draw.polygon(srf, BC,   neck)
        pygame.draw.polygon(srf, BELY, throat)

        # 5. HEAD
        hcx = nt_x + p(7)
        hcy = nt_y + p(3) + bob
        HW, HH = p(17), p(13)
        pygame.draw.ellipse(srf, BC, (hcx-HW//2, hcy-HH//2, HW, HH))

        # Long deer snout
        snout_x = hcx + HW//2 - p(2)
        snout_y = hcy - p(4)
        pygame.draw.ellipse(srf, BC,     (snout_x,        snout_y,       p(22), p(10)))
        pygame.draw.ellipse(srf, NOSE_C, (snout_x+p(16),  snout_y,       p(7),  p(10)))
        pygame.draw.circle( srf, DARK,   (snout_x+p(18),  snout_y+p(3)), max(1, p(2)))

        # Eye
        ex, ey = hcx + p(3), hcy - p(2)
        pygame.draw.circle(srf, (16, 10, 6),       (ex, ey), p(4))
        pygame.draw.circle(srf, (215, 195, 165),   (ex-p(1), ey-p(1)), max(1, p(1)))

        # Large whitetail ears
        for eox, eoy in [(-4, -9), (8, -7)]:
            ecx, ecy = hcx+p(eox), hcy+p(eoy)
            pygame.draw.ellipse(srf, BC,            (ecx-p(5), ecy-p(12), p(10), p(16)))
            pygame.draw.ellipse(srf, (192,155,152), (ecx-p(3), ecy-p(10), p(6),  p(12)))

        # Antlers for buck / stag
        if self.variant >= 1:
            ax, ay = hcx - p(2), hcy - HH//2 - p(4)
            beams = [
                [(-2,-8), (-5,-18), (-9,-26)],
                [( 4,-7), ( 9,-17), (14,-25)],
            ]
            if self.variant == 2:
                beams[0] += [(-13,-20), (-7,-13)]
                beams[1] += [(18,-18),  (12,-11)]
            for beam in beams:
                prev = (ax, ay)
                for dx, dy in beam:
                    cur = (ax+p(dx), ay+p(dy))
                    pygame.draw.line(srf, BROWN, prev, cur, max(1, p(3)))
                    prev = cur

        # Flip for left-facing deer
        if self.dir == -1:
            srf = pygame.transform.flip(srf, True, False)
        return srf

# ── HUD helpers ────────────────────────────────────────────────────────────────
def draw_rounded_rect(surf, color, rect, radius=12, alpha=None):
    if alpha is not None:
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill((*color, alpha))
        surf.blit(s, rect.topleft)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=radius)

def draw_ammo_bar(surf, ammo, max_ammo, x, y):
    for i in range(max_ammo):
        cx = x + i*(22)
        cy = y
        if i < ammo:
            # bullet shape
            pygame.draw.rect(surf, (200,200,50), (cx, cy+4, 8, 16), border_radius=3)
            pygame.draw.ellipse(surf, (240,220,60), (cx, cy, 8, 10))
        else:
            pygame.draw.rect(surf, (60,60,60), (cx, cy+4, 8, 16), border_radius=3)
            pygame.draw.ellipse(surf, (80,80,80), (cx, cy, 8, 10))

def draw_progress_bar(surf, x, y, w, h, val, maxx, col_fill, col_bg=(40,40,40), label=""):
    draw_rounded_rect(surf, col_bg, pygame.Rect(x,y,w,h), 6)
    fw = int(w * val / maxx)
    if fw > 0:
        draw_rounded_rect(surf, col_fill, pygame.Rect(x,y,fw,h), 6)
    pygame.draw.rect(surf, GRAY, (x,y,w,h), 2, border_radius=6)
    if label:
        txt(surf, label, x+w//2, y+h//2, F_TINY, WHITE, "center", False)

# ── Floating text ──────────────────────────────────────────────────────────────
class FloatText:
    def __init__(self, x, y, text, color=GOLD, size="med"):
        self.x, self.y = float(x), float(y)
        self.text = text
        self.color = color
        self.life = 70
        self.f = F_MED if size=="med" else F_BIG

    def update(self): self.y -= 1.2; self.life -= 1
    def draw(self, surf):
        alpha = min(255, self.life * 5)
        s = self.f.render(self.text, True, self.color)
        s.set_alpha(alpha)
        r = s.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(s, r)
    @property
    def dead(self): return self.life <= 0

float_texts = []

# ── Screen flash ───────────────────────────────────────────────────────────────
class Flash:
    def __init__(self, color, duration):
        self.color = color
        self.life = self.max_life = duration

    def draw(self, surf):
        alpha = int(120 * self.life / self.max_life)
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        s.fill((*self.color, alpha))
        surf.blit(s, (0,0))

    def update(self): self.life -= 1
    @property
    def dead(self): return self.life <= 0

flashes = []

# ── Scope overlay ──────────────────────────────────────────────────────────────
scope_active = False
scope_surf = None

def toggle_scope():
    global scope_active, scope_surf
    scope_active = not scope_active
    if scope_active:
        scope_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        scope_surf.fill((0,0,0,0))
        cx, cy = W//2, H//2
        r = 180
        # dark vignette
        for pr in range(r, W, 3):
            alpha = min(230, int((pr-r)*1.2))
            pygame.draw.circle(scope_surf,(0,0,0,alpha),(cx,cy),pr,3)
        pygame.draw.circle(scope_surf,(0,0,0,220),(cx,cy),W,W-r-2)
        # scope glass
        pygame.draw.circle(scope_surf,(30,60,30,60),(cx,cy),r)
        pygame.draw.circle(scope_surf,(80,255,80,80),(cx,cy),r,3)
        # crosshair
        pygame.draw.line(scope_surf,(80,255,80,180),(cx-r,cy),(cx+r,cy),2)
        pygame.draw.line(scope_surf,(80,255,80,180),(cx,cy-r),(cx,cy+r),2)
        for i in range(1,4):
            d = i*r//4
            pygame.draw.line(scope_surf,(80,255,80,120),(cx-8,cy-d),(cx+8,cy-d),1)
            pygame.draw.line(scope_surf,(80,255,80,120),(cx-8,cy+d),(cx+8,cy+d),1)
            pygame.draw.line(scope_surf,(80,255,80,120),(cx-d,cy-8),(cx-d,cy+8),1)
            pygame.draw.line(scope_surf,(80,255,80,120),(cx+d,cy-8),(cx+d,cy+8),1)

# ── Wind indicator ─────────────────────────────────────────────────────────────
wind_angle = random.uniform(0, 2*math.pi)
wind_speed = random.uniform(0.5, 3.0)
wind_timer = 0

def update_wind():
    global wind_angle, wind_speed, wind_timer
    wind_timer += 1
    if wind_timer % 300 == 0:
        wind_angle += random.uniform(-0.5, 0.5)
        wind_speed = max(0.2, wind_speed + random.uniform(-0.5, 0.5))
        wind_speed = min(5.0, wind_speed)

def draw_wind(surf, x, y):
    draw_rounded_rect(surf,(20,20,40), pygame.Rect(x-5,y-5,110,50),8,180)
    txt(surf,"WIND",x+2,y,F_TINY,LGRAY)
    end_x = x+55 + int(math.cos(wind_angle)*20)
    end_y = y+25 + int(math.sin(wind_angle)*20)
    pygame.draw.line(surf,YELLOW,(x+55,y+25),(end_x,end_y),3)
    pygame.draw.circle(surf,YELLOW,(end_x,end_y),4)
    pygame.draw.circle(surf,DGRAY,(x+55,y+25),3)
    txt(surf,f"{wind_speed:.1f}m/s",x+2,y+28,F_TINY,(180,220,255))

# ── Game states ────────────────────────────────────────────────────────────────
STATE_MENU   = "menu"
STATE_PLAY   = "play"
STATE_PAUSE  = "pause"
STATE_LEVEL  = "level"
STATE_OVER   = "over"

class Game:
    MAX_AMMO   = 8
    RELOAD_TIME= 120
    LEVEL_DEER = [5, 8, 12, 16, 20, 25, 30, 40]
    LEVEL_TIME = [90, 80, 75, 70, 65, 60, 55, 50]

    def __init__(self):
        self.reset_all()

    def reset_all(self):
        self.state       = STATE_MENU
        self.score       = 0
        self.hi_score    = 0
        self.level       = 1
        self.deer_list   = []
        self.ammo        = self.MAX_AMMO
        self.reloading   = False
        self.reload_timer= 0
        self.time_left   = self.LEVEL_TIME[0]
        self.time_frac   = 0.0
        self.deer_killed = 0
        self.deer_goal   = self.LEVEL_DEER[0]
        self.crosshair   = Crosshair()
        self.spawn_timer = 0
        self.spawn_rate  = 90
        self.combo       = 0
        self.combo_timer = 0
        self.total_shots = 0
        self.total_hits  = 0
        self.menu_anim   = 0
        self.level_timer = 0
        self.cursor_visible = False
        self.shake_timer = 0
        self.shake_x = 0
        self.shake_y = 0

    def start_level(self):
        li = min(self.level-1, len(self.LEVEL_DEER)-1)
        self.time_left   = self.LEVEL_TIME[li]
        self.time_frac   = 0.0
        self.deer_goal   = self.LEVEL_DEER[li]
        self.deer_killed = 0
        self.deer_list   = []
        self.ammo        = self.MAX_AMMO
        self.reloading   = False
        self.spawn_rate  = max(40, 90 - self.level * 8)
        self.state       = STATE_PLAY

    def spawn_deer(self):
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate and len(self.deer_list) < 6:
            self.deer_list.append(Deer(self.level))
            self.spawn_timer = 0

    def reload(self):
        if not self.reloading and self.ammo < self.MAX_AMMO:
            self.reloading = True
            self.reload_timer = self.RELOAD_TIME
            play(SND_RELOAD)
            flashes.append(Flash((255,200,0), 10))

    def shoot(self, mx, my):
        if self.ammo <= 0:
            self.reload()
            return
        if self.reloading:
            return

        self.ammo -= 1
        self.total_shots += 1
        play(SND_SHOOT)
        muzzle_flash(mx, my)
        smoke_puff(mx, my)
        self.crosshair.recoil = 8
        self.shake_timer = 12

        hit = False
        for d in self.deer_list:
            if d.alive and not d.dying and d.rect.collidepoint(mx, my):
                d.alive = False
                d.dying = True
                d.hit_flash = 15
                blood_burst(mx, my)
                star_burst(mx, my)
                play(SND_HIT)
                self.total_hits += 1
                self.deer_killed += 1

                self.combo += 1
                self.combo_timer = 120
                bonus = self.combo * 50 if self.combo > 1 else 0
                pts = d.score_val + bonus
                self.score += pts
                label = f"+{pts}"
                if self.combo > 1: label += f" x{self.combo} COMBO!"
                float_texts.append(FloatText(mx, my-20, label, GOLD, "med"))
                flashes.append(Flash((255,100,0), 8))
                hit = True
                break

        if not hit:
            play(SND_MISS)
            float_texts.append(FloatText(mx, my-10, "MISS", PINK, "med"))
            self.combo = 0

        if self.ammo == 0:
            self.reload()

    def update(self):
        global particles, float_texts, flashes
        update_wind()

        if self.state == STATE_MENU:
            self.menu_anim += 1
            return

        if self.state == STATE_LEVEL:
            self.level_timer += 1
            if self.level_timer > 150:
                self.start_level()
            return

        if self.state == STATE_PAUSE:
            return

        if self.state == STATE_OVER:
            return

        # PLAY
        self.shake_timer = max(0, self.shake_timer-1)
        if self.shake_timer > 0:
            self.shake_x = random.randint(-4,4)
            self.shake_y = random.randint(-3,3)
        else:
            self.shake_x = self.shake_y = 0

        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.ammo = self.MAX_AMMO
                self.reloading = False
                float_texts.append(FloatText(W//2, H-80, "RELOADED!", (100,255,100)))

        self.time_frac += 1/FPS
        if self.time_frac >= 1.0:
            self.time_frac -= 1.0
            self.time_left -= 1
            if self.time_left <= 0:
                self.time_left = 0
                self.end_level(False)
                return

        self.spawn_deer()

        dead = []
        for d in self.deer_list:
            if d.update():
                dead.append(d)
        for d in dead:
            if d in self.deer_list:
                self.deer_list.remove(d)

        particles  = [p for p in particles  if not p.dead]
        float_texts= [f for f in float_texts if not f.dead]
        flashes    = [f for f in flashes    if not f.dead]

        for p in particles:  p.update()
        for f in float_texts: f.update()
        for f in flashes:     f.update()

        if self.deer_killed >= self.deer_goal:
            self.end_level(True)

    def end_level(self, success):
        if success:
            play(SND_LEVEL)
            self.level += 1
            self.hi_score = max(self.hi_score, self.score)
            if self.level > len(self.LEVEL_DEER):
                self.state = STATE_OVER
                self.hi_score = max(self.hi_score, self.score)
            else:
                self.state = STATE_LEVEL
                self.level_timer = 0
        else:
            self.state = STATE_OVER
            self.hi_score = max(self.hi_score, self.score)

    def draw_hud(self, surf):
        # top bar background
        draw_rounded_rect(surf,(10,20,10),pygame.Rect(0,0,W,64),0,200)

        # score
        txt(surf,"SCORE", 20, 8, F_SMALL, LGRAY)
        txt(surf,f"{self.score:,}", 20, 26, F_BIG, GOLD)

        # level
        txt(surf,f"LEVEL {self.level}", W//2, 8, F_MED, LGRAY, "center")

        # deer progress
        draw_progress_bar(surf, W//2-100, 30, 200, 20,
                          self.deer_killed, self.deer_goal,
                          (80,200,80),(30,60,30),
                          f"{self.deer_killed}/{self.deer_goal} DEER")

        # time
        tcol = RED if self.time_left < 15 else (ORANGE if self.time_left < 30 else WHITE)
        txt(surf,f"⏱ {self.time_left:02d}s", W-160, 8, F_MED, tcol)
        draw_progress_bar(surf, W-160, 34, 140, 16,
                          self.time_left, self.LEVEL_TIME[min(self.level-1,7)],
                          tcol,(40,20,20))

        # ammo
        txt(surf,"AMMO", 20, H-52, F_SMALL, LGRAY)
        draw_ammo_bar(surf, self.ammo, self.MAX_AMMO, 70, H-55)
        if self.reloading:
            pct = 1.0 - self.reload_timer/self.RELOAD_TIME
            draw_progress_bar(surf, 70, H-28, self.MAX_AMMO*22, 14, pct, 1.0,
                              ORANGE, (40,20,0), "RELOADING...")

        # hi-score
        txt(surf,f"BEST: {self.hi_score:,}", W-10, 70, F_SMALL, LGRAY, "topright")

        # combo
        if self.combo > 1:
            txt(surf,f"COMBO x{self.combo}!", W//2, 75, F_BIG,
                (255, int(255-self.combo*20), 0), "center")

        # accuracy
        if self.total_shots > 0:
            acc = int(self.total_hits/self.total_shots*100)
            txt(surf,f"ACC {acc}%", W-10, 90, F_SMALL, (180,220,180),"topright")

        # wind
        draw_wind(surf, 20, H-100)

        # scope hint
        txt(surf,"[RMB] SCOPE  [R] RELOAD  [ESC] PAUSE",
            W//2, H-18, F_TINY, (130,130,130), "center", False)

    def draw_play(self, surf):
        ox, oy = self.shake_x, self.shake_y
        temp = pygame.Surface((W, H))
        temp.blit(BG, (0,0))
        temp.blit(DECOR, (0,0))

        for d in sorted(self.deer_list, key=lambda d: d.y):
            d.draw(temp)

        for p in particles: p.draw(temp)
        for f in float_texts: f.draw(temp)

        if scope_active and scope_surf:
            temp.blit(scope_surf, (0,0))

        surf.blit(temp, (ox, oy))

        for f in flashes: f.draw(surf)
        self.draw_hud(surf)
        mx, my = pygame.mouse.get_pos()
        self.crosshair.update(mx, my)
        self.crosshair.draw(surf, self.ammo)

    def draw_menu(self, surf):
        surf.blit(BG, (0,0))
        surf.blit(DECOR, (0,0))
        t = self.menu_anim

        # animated title panel
        panel_y = 80 + int(math.sin(t*0.03)*6)
        draw_rounded_rect(surf,(0,0,0),pygame.Rect(W//2-340, panel_y, 680, 160),20,180)
        pygame.draw.rect(surf, GOLD, (W//2-340, panel_y, 680, 160), 3, border_radius=20)

        # title with color cycle
        hue = (t * 2) % 360
        c = pygame.Color(0)
        c.hsva = (hue, 80, 100, 100)
        txt(surf,"DEER HUNTER", W//2, panel_y+25, F_HUGE, (int(c.r),int(c.g),int(c.b)), "midtop")
        txt(surf,"EXTREME EDITION", W//2, panel_y+110, F_MED, ORANGE, "midtop")

        # animated deer on menu
        fake = Deer(1)
        fake.x = W//2 + int(math.sin(t*0.02)*100) + 150
        fake.y = H//2 + 80
        fake.dir = -1 if math.sin(t*0.02) > 0 else 1
        fake.anim = t
        fake.scale = 1.3
        fake.draw(surf)

        # buttons
        buttons = [("PLAY GAME","START",GREEN),
                   ("HIGH SCORE",f"{self.hi_score:,}",GOLD),
                   ("CONTROLS","",LGRAY)]
        for i,(label,val,col) in enumerate(buttons):
            by = 310 + i*90
            hover = pygame.Rect(W//2-150, by-5, 300, 65).collidepoint(pygame.mouse.get_pos())
            bcol = (col[0]//2, col[1]//2, col[2]//2) if not hover else col
            draw_rounded_rect(surf, bcol, pygame.Rect(W//2-150, by-5, 300, 65), 14, 220)
            pygame.draw.rect(surf, col, (W//2-150, by-5, 300, 65), 2, border_radius=14)
            txt(surf, label, W//2, by+10, F_MED, WHITE, "midtop")
            if val:
                txt(surf, val, W//2, by+35, F_MED, col, "midtop")

        # controls panel
        draw_rounded_rect(surf,(0,0,0),pygame.Rect(W//2-220,580,440,110),12,160)
        lines=[
            "LMB = SHOOT    RMB = SCOPE    R = RELOAD",
            "ESC = PAUSE    Space = RELOAD",
        ]
        for i,l in enumerate(lines):
            txt(surf, l, W//2, 595+i*30, F_SMALL, LGRAY, "midtop", False)

        for p in particles: p.draw(surf)
        for f in float_texts: f.draw(surf)

    def draw_level_screen(self, surf):
        surf.blit(BG, (0,0))
        t = self.level_timer
        alpha = min(255, t*5)
        panel = pygame.Surface((600,300), pygame.SRCALPHA)
        panel.fill((0,0,0,int(200*alpha/255)))
        pygame.draw.rect(panel, GOLD, (0,0,600,300), 3, border_radius=20)
        surf.blit(panel, (W//2-300, H//2-150))

        txt(surf,"LEVEL COMPLETE!", W//2, H//2-120, F_BIG, GOLD,"center")
        txt(surf,f"LEVEL {self.level-1} CLEARED", W//2, H//2-70, F_MED, WHITE,"center")
        txt(surf,f"Score: {self.score:,}", W//2, H//2-30, F_MED, YELLOW,"center")
        acc = int(self.total_hits/max(1,self.total_shots)*100)
        txt(surf,f"Accuracy: {acc}%", W//2, H//2+10, F_MED, (150,255,150),"center")
        txt(surf,f"LEVEL {self.level} INCOMING...", W//2, H//2+60, F_MED, ORANGE,"center")
        prog = min(1.0, self.level_timer/150)
        draw_progress_bar(surf, W//2-150, H//2+110, 300, 20, prog, 1.0, GREEN,(30,30,30))
        star_burst(W//2, H//2) if t%8==0 else None
        for p in particles: p.draw(surf)

    def draw_pause(self, surf):
        self.draw_play(surf)
        overlay = pygame.Surface((W,H), pygame.SRCALPHA)
        overlay.fill((0,0,0,150))
        surf.blit(overlay,(0,0))
        draw_rounded_rect(surf,(20,20,20),pygame.Rect(W//2-200,H//2-140,400,280),20,230)
        pygame.draw.rect(surf,GRAY,(W//2-200,H//2-140,400,280),2,border_radius=20)
        txt(surf,"PAUSED",W//2,H//2-120,F_HUGE,WHITE,"center")
        for i,(l,c) in enumerate([("RESUME",GREEN),("MAIN MENU",ORANGE),("QUIT",RED)]):
            by = H//2-30 + i*70
            hover = pygame.Rect(W//2-120,by-5,240,50).collidepoint(pygame.mouse.get_pos())
            draw_rounded_rect(surf,(c[0]//3,c[1]//3,c[2]//3) if not hover else (c[0]//2,c[1]//2,c[2]//2),
                              pygame.Rect(W//2-120,by-5,240,50),12,220)
            pygame.draw.rect(surf,c,(W//2-120,by-5,240,50),2,border_radius=12)
            txt(surf,l,W//2,by+10,F_MED,WHITE,"center")

    def draw_game_over(self, surf):
        surf.blit(BG, (0,0))
        draw_rounded_rect(surf,(0,0,0),pygame.Rect(W//2-300,H//2-200,600,400),20,200)
        pygame.draw.rect(surf,RED,(W//2-300,H//2-200,600,400),3,border_radius=20)
        won = self.level > len(self.LEVEL_DEER)
        col = GOLD if won else RED
        title = "VICTORY!" if won else "GAME OVER"
        txt(surf,title,W//2,H//2-180,F_HUGE,col,"center")
        txt(surf,f"Final Score: {self.score:,}",W//2,H//2-80,F_BIG,WHITE,"center")
        txt(surf,f"Best Score: {self.hi_score:,}",W//2,H//2-30,F_MED,GOLD,"center")
        acc = int(self.total_hits/max(1,self.total_shots)*100)
        txt(surf,f"Accuracy: {acc}%  |  Deer: {self.deer_killed}",W//2,H//2+20,F_MED,LGRAY,"center")
        if won:
            for _ in range(2): star_burst(random.randint(200,W-200), random.randint(100,H-200))
        for i,(l,c) in enumerate([("PLAY AGAIN",GREEN),("MAIN MENU",ORANGE)]):
            by = H//2+90 + i*75
            hover = pygame.Rect(W//2-130,by-5,260,55).collidepoint(pygame.mouse.get_pos())
            draw_rounded_rect(surf,(c[0]//3,c[1]//3,c[2]//3) if not hover else (c[0]//2,c[1]//2,c[2]//2),
                              pygame.Rect(W//2-130,by-5,260,55),12,220)
            pygame.draw.rect(surf,c,(W//2-130,by-5,260,55),2,border_radius=12)
            txt(surf,l,W//2,by+10,F_MED,WHITE,"center")
        for p in particles: p.draw(surf)
        for f in float_texts: f.draw(surf)

    def handle_click(self, pos, button):
        mx, my = pos
        if self.state == STATE_PLAY:
            if button == 1:
                self.shoot(mx, my)
            elif button == 3:
                toggle_scope()
        elif self.state == STATE_MENU:
            if pygame.Rect(W//2-150,305,300,65).collidepoint(pos):
                play(SND_LEVEL)
                self.level = 1
                self.score = 0
                self.total_shots = self.total_hits = 0
                self.combo = 0
                self.state = STATE_LEVEL
                self.level_timer = 0
        elif self.state == STATE_PAUSE:
            if pygame.Rect(W//2-120,H//2-35,240,50).collidepoint(pos):
                self.state = STATE_PLAY
            elif pygame.Rect(W//2-120,H//2+35,240,50).collidepoint(pos):
                self.reset_all()
            elif pygame.Rect(W//2-120,H//2+105,240,50).collidepoint(pos):
                pygame.quit(); sys.exit()
        elif self.state == STATE_OVER:
            if pygame.Rect(W//2-130,H//2+85,260,55).collidepoint(pos):
                hi = self.hi_score
                self.reset_all()
                self.hi_score = hi
                self.level = 1; self.score = 0
                self.total_shots = self.total_hits = 0
                self.state = STATE_LEVEL; self.level_timer = 0
            elif pygame.Rect(W//2-130,H//2+160,260,55).collidepoint(pos):
                hi = self.hi_score
                self.reset_all()
                self.hi_score = hi

# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    global scope_active
    game = Game()
    pygame.mouse.set_visible(False)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.state == STATE_PLAY:
                        game.state = STATE_PAUSE
                    elif game.state == STATE_PAUSE:
                        game.state = STATE_PLAY
                if event.key in (pygame.K_r, pygame.K_SPACE):
                    if game.state == STATE_PLAY:
                        game.reload()
            if event.type == pygame.MOUSEBUTTONDOWN:
                game.handle_click(event.pos, event.button)
                if event.button == 3 and game.state != STATE_PLAY:
                    scope_active = False

        game.update()

        screen.fill(BLACK)
        if game.state == STATE_MENU:
            game.draw_menu(screen)
        elif game.state == STATE_PLAY:
            game.draw_play(screen)
        elif game.state == STATE_PAUSE:
            game.draw_pause(screen)
        elif game.state == STATE_LEVEL:
            game.draw_level_screen(screen)
        elif game.state == STATE_OVER:
            game.draw_game_over(screen)

        # cursor (crosshair replaces it in play mode)
        if game.state != STATE_PLAY:
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(screen, WHITE, (mx,my), 6, 2)
            pygame.draw.line(screen, WHITE,(mx-9,my),(mx+9,my),2)
            pygame.draw.line(screen, WHITE,(mx,my-9),(mx,my+9),2)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
