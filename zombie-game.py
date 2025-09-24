
import pygame
import random
import math
import sys
from collections import deque

pygame.init()
pygame.mixer.init()


SCREEN_W, SCREEN_H = 800, 600
WORLD_W, WORLD_H = 2400, 1800     
FPS = 60

# Colors
WHITE = (255, 255, 255)
GREY = (40, 40, 40)
DARK = (20, 20, 20)
GREEN = (40, 200, 40)
RED = (220, 40, 40)
YELLOW = (220, 220, 30)
BLUE = (30, 130, 220)

PLAYER_IMG_PATH = "C:/Users/HP/Desktop/assets/player.jpg.png"
BULLET_IMG_PATH = "C:/Users/HP/Desktop/assets/bullet.png"
ZOMBIE_IMG_PATHS = [
    r"C:\Users\HP\Desktop\assets\Zombie1Walk12.png",
    r"C:\Users\HP\Desktop\assets\h3.png"
]


screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Zombie Open-World Shooter")
clock = pygame.time.Clock()
font = pygame.font.SysFont("comicsansms", 20)
big_font = pygame.font.SysFont("comicsansms", 48)

def safe_load_image(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception as e:
        # fallback: return a colored surface
        w, h = size if size else (50, 50)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((150, 0, 0, 255))
        pygame.draw.rect(surf, (0,0,0), surf.get_rect(), 2)
        return surf


player_img = safe_load_image(PLAYER_IMG_PATH, (48, 48))
bullet_img = safe_load_image(BULLET_IMG_PATH, (10, 6))
zombie_imgs = [safe_load_image(p, (44, 44)) for p in ZOMBIE_IMG_PATHS]


def safe_load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

shoot_snd = None
reload_snd = None
zombie_hurt_snd = None


class Camera:
    def __init__(self, width, height, screen_w, screen_h):
        self.width, self.height = width, height
        self.screen_w, self.screen_h = screen_w, screen_h
        self.x, self.y = 0, 0

    def update(self, target_rect):
        # Center camera on player but clamp to world bounds
        self.x = int(target_rect.centerx - self.screen_w // 2)
        self.y = int(target_rect.centery - self.screen_h // 2)
        self.x = max(0, min(self.x, self.width - self.screen_w))
        self.y = max(0, min(self.y, self.height - self.screen_h))

    def apply(self, rect):
        return rect.move(-self.x, -self.y)

class Player:
    def __init__(self, x, y):
        self.image = player_img
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.speed = 4.0
        self.sprint_multiplier = 1.5
        self.health = 100
        self.max_health = 100
        self.score = 0

        # Weapons
        self.weapons = [
            {"name": "Pistol", "mag": 12, "reserve": 60, "rpm": 300, "bullet_speed": 14, "damage": 18, "reload_time": 900},
            {"name": "Shotgun", "mag": 6, "reserve": 30, "rpm": 60, "bullet_speed": 13, "damage": 40, "pellets": 6, "spread": 18, "reload_time": 1200},
            {"name": "SMG", "mag": 30, "reserve": 120, "rpm": 900, "bullet_speed": 16, "damage": 10, "reload_time": 1300},
        ]
        self.curr_weapon = 0
        self.mag = self.weapons[self.curr_weapon]["mag"]
        self.last_shot = 0
        self.reloading = False
        self.reload_start = 0

    def switch_weapon(self, idx):
        if 0 <= idx < len(self.weapons):
            self.curr_weapon = idx
            self.mag = min(self.mag, self.weapons[self.curr_weapon]["mag"])

    def start_reload(self, now):
        weapon = self.weapons[self.curr_weapon]
        if self.reloading: return
        if self.mag >= weapon["mag"]: return
        if weapon["reserve"] <= 0: return
        self.reloading = True
        self.reload_start = now
        if reload_snd: reload_snd.play()

    def finish_reload(self):
        weapon = self.weapons[self.curr_weapon]
        needed = weapon["mag"] - self.mag
        taken = min(needed, weapon["reserve"])
        weapon["reserve"] -= taken
        self.mag += taken
        self.reloading = False

    def update(self, dt, keys):
        self.vel = pygame.Vector2(0, 0)
        move_speed = self.speed
        if keys[pygame.K_LSHIFT]:
            move_speed *= self.sprint_multiplier
        if keys[pygame.K_w]:
            self.vel.y = -move_speed
        if keys[pygame.K_s]:
            self.vel.y = move_speed
        if keys[pygame.K_a]:
            self.vel.x = -move_speed
        if keys[pygame.K_d]:
            self.vel.x = move_speed
        self.pos += self.vel * dt
        # clamp to world
        self.pos.x = max(16, min(self.pos.x, WORLD_W - 16))
        self.pos.y = max(16, min(self.pos.y, WORLD_H - 16))
        self.rect.center = (round(self.pos.x), round(self.pos.y))

player = Player(WORLD_W//2, WORLD_H//2)

class Bullet:
    def __init__(self, pos, vel, dmg, lifespan=2000):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.dmg = dmg
        self.lifespan = lifespan
        self.spawn_time = pygame.time.get_ticks()
        self.rect = bullet_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))

    def update(self, dt):
        self.pos += self.vel * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        return pygame.time.get_ticks() - self.spawn_time < self.lifespan

class Zombie:
    def __init__(self, x, y, kind=0):
        self.image = zombie_imgs[kind % len(zombie_imgs)]
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        # type properties
        if kind == 0:
            self.speed = 1.2
            self.hp = 40
            self.max_hp = 40
        elif kind == 1:
            self.speed = 0.9
            self.hp = 100
            self.max_hp = 100
        else:
            self.speed = 1.6
            self.hp = 60
            self.max_hp = 60
        self.kind = kind

    def update(self, dt, target_pos):
        # move towards player (simple homing)
        dirv = (target_pos - self.pos)
        dist = dirv.length()
        if dist > 0.1:
            dirv.scale_to_length(self.speed)
            self.pos += dirv * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))

# Obstacles (rects)
obstacles = []
def generate_obstacles(n=40):
    obstacles.clear()
    for _ in range(n):
        w = random.randint(80, 240)
        h = random.randint(40, 180)
        x = random.randint(0, WORLD_W - w)
        y = random.randint(0, WORLD_H - h)
        r = pygame.Rect(x, y, w, h)
        # don't overlap player spawn too close
        if r.collidepoint(player.pos.x, player.pos.y):
            continue
        obstacles.append(r)
generate_obstacles()


bullets = []
zombies = []
pickups = [] 
spawn_cooldown = 0
wave = 1
wave_timer = 0
last_wave_clear = True

# ---------- Utility functions ----------
def world_to_screen(vec, cam):
    return pygame.Vector2(vec.x - cam.x, vec.y - cam.y)

def spawn_zombie_offscreen(player_pos, min_dist=800):
    # spawn at random edge, but far from player
    while True:
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            x = random.randint(0, WORLD_W)
            y = -random.randint(80, 300)
        elif side == "bottom":
            x = random.randint(0, WORLD_W)
            y = WORLD_H + random.randint(80, 300)
        elif side == "left":
            x = -random.randint(80, 300)
            y = random.randint(0, WORLD_H)
        else:
            x = WORLD_W + random.randint(80, 300)
            y = random.randint(0, WORLD_H)
        if pygame.Vector2(x, y).distance_to(player_pos) > min_dist:
            break
    kind = random.choices([0,1,2], weights=[60,20,20])[0]
    zombies.append(Zombie(x, y, kind))

def spawn_pickup(x, y):
    t = random.choice(["ammo", "health"])
    if t == "ammo":
        val = 30
    else:
        val = 30
    r = pygame.Rect(x - 12, y - 12, 24, 24)
    pickups.append((t, r, val))

def shoot_bullet(origin, target, weapon):
    
    direction = pygame.Vector2(target) - pygame.Vector2(origin)
    if direction.length() == 0:
        direction = pygame.Vector2(1, 0)
    direction = direction.normalize()
    bullets_created = []
    now = pygame.time.get_ticks()
    if weapon["name"] == "Shotgun":
        pellets = weapon.get("pellets", 6)
        spread = math.radians(weapon.get("spread", 12))
        base_angle = math.atan2(direction.y, direction.x)
        for i in range(pellets):
            angle = base_angle + random.uniform(-spread/2, spread/2)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * weapon["bullet_speed"]
            bullets_created.append(Bullet(origin, vel, weapon["damage"]))
    else:
        vel = direction * weapon["bullet_speed"]
        bullets_created.append(Bullet(origin, vel, weapon["damage"]))
    if shoot_snd: shoot_snd.play()
    return bullets_created

def rect_collides_with_obstacles(rect):
    for o in obstacles:
        if rect.colliderect(o):
            return True
    return False


cam = Camera(WORLD_W, WORLD_H, SCREEN_W, SCREEN_H)

# ---------- Draw functions ----------
def draw_world(surface, camera):
    # background grid
    tile = 80
    start_x = (camera.x // tile) * tile
    start_y = (camera.y // tile) * tile
    for x in range(start_x, camera.x + SCREEN_W + tile, tile):
        pygame.draw.line(surface, (28,28,28), (x - camera.x, 0), (x - camera.x, SCREEN_H))
    for y in range(start_y, camera.y + SCREEN_H + tile, tile):
        pygame.draw.line(surface, (28,28,28), (0, y - camera.y), (SCREEN_W, y - camera.y))

    # obstacles
    for o in obstacles:
        r = camera.apply(o)
        pygame.draw.rect(surface, (60,60,60), r)
        pygame.draw.rect(surface, (40,40,40), r, 2)

def draw_hud(surface, player, cam):
    # Health bar
    hp_w = 220
    hp_h = 18
    x = 10; y = 10
    pygame.draw.rect(surface, (70,70,70), (x-4, y-4, hp_w+8, hp_h+8))
    pygame.draw.rect(surface, (40,40,40), (x, y, hp_w, hp_h))
    frac = max(0, player.health / player.max_health)
    pygame.draw.rect(surface, (200,40,40), (x, y, int(hp_w * frac), hp_h))
    hp_text = font.render(f"HP: {player.health}/{player.max_health}", True, WHITE)
    surface.blit(hp_text, (x + 6, y - 22))

    # Score & wave
    score_text = font.render(f"Score: {player.score}", True, WHITE)
    wave_text = font.render(f"Wave: {wave}", True, WHITE)
    surface.blit(score_text, (SCREEN_W - 150, 10))
    surface.blit(wave_text, (SCREEN_W - 150, 32))

    # Weapon info
    w = player.weapons[player.curr_weapon]
    wname = w["name"]
    mag = player.mag
    reserve = w["reserve"]
    weap_text = font.render(f"{wname}  [{mag}/{reserve}]", True, WHITE)
    surface.blit(weap_text, (10, SCREEN_H - 34))

    # Minimap (small)
    map_w, map_h = 180, 135
    mx, my = SCREEN_W - map_w - 10, SCREEN_H - map_h - 10
    pygame.draw.rect(surface, (18,18,18), (mx-2, my-2, map_w+4, map_h+4))
    pygame.draw.rect(surface, (40,40,40), (mx, my, map_w, map_h))
    # draw player as dot
    def world_to_map(wx, wy):
        return mx + (wx / WORLD_W) * map_w, my + (wy / WORLD_H) * map_h
    px, py = world_to_map(player.pos.x, player.pos.y)
    pygame.draw.circle(surface, GREEN, (int(px), int(py)), 4)
    # draw nearby zombies
    for z in zombies:
        zx, zy = world_to_map(z.pos.x, z.pos.y)
        if 0 <= zx - mx <= map_w and 0 <= zy - my <= map_h:
            pygame.draw.circle(surface, RED, (int(zx), int(zy)), 3)


def game_over_screen(final_score):
    screen.fill(DARK)
    t1 = big_font.render("GAME OVER", True, RED)
    t2 = font.render(f"Final Score: {final_score}", True, WHITE)
    t3 = font.render("Press R to restart or Q to quit", True, WHITE)
    screen.blit(t1, (SCREEN_W//2 - t1.get_width()//2, SCREEN_H//2 - 80))
    screen.blit(t2, (SCREEN_W//2 - t2.get_width()//2, SCREEN_H//2 - 10))
    screen.blit(t3, (SCREEN_W//2 - t3.get_width()//2, SCREEN_H//2 + 30))
    pygame.display.flip()
    waiting = True
    while waiting:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_q:
                    pygame.quit(); sys.exit()
                if ev.key == pygame.K_r:
                    waiting = False

def reset_world():
    global zombies, bullets, pickups, player, wave, wave_timer, spawn_cooldown, last_wave_clear
    zombies = []
    bullets = []
    pickups = []
    player.pos = pygame.Vector2(WORLD_W//2, WORLD_H//2)
    player.rect.center = player.pos
    player.health = player.max_health
    # reset weapon ammo fairly
    for w in player.weapons:
        w["reserve"] = w.get("reserve", 60)
    player.mag = player.weapons[player.curr_weapon]["mag"]
    player.score = 0
    wave = 1
    wave_timer = 0
    spawn_cooldown = 0
    last_wave_clear = True
    generate_obstacles()

reset_world()

running = True
while running:
    dt = clock.tick(FPS) / (1000.0)  
    now = pygame.time.get_ticks()
    keys = pygame.key.get_pressed()

    # spawn logic: new wave spawns more zombies
    if len(zombies) == 0 and last_wave_clear:
        # small pause then spawn new wave
        wave_timer += dt
        if wave_timer > 1.0:
            for _ in range(5 + wave * 2):
                spawn_zombie_offscreen(player.pos, min_dist=500)
            wave += 1
            wave_timer = 0
            last_wave_clear = False

    # spawn occasional pickups
    if random.random() < 0.001:
        x = random.randint(0, WORLD_W)
        y = random.randint(0, WORLD_H)
        spawn_pickup(x, y)

    # Input & events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False; break
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                player.switch_weapon(0)
            if event.key == pygame.K_2:
                player.switch_weapon(1)
            if event.key == pygame.K_3:
                player.switch_weapon(2)
            if event.key == pygame.K_r:
                player.start_reload(now)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  
                # handle shooting with RPM
                weapon = player.weapons[player.curr_weapon]
                delay = 60000 / weapon["rpm"] if weapon.get("rpm") else 100
                if not player.reloading and now - player.last_shot >= delay and player.mag > 0:
                    mouse_screen = pygame.mouse.get_pos()
                    
                    world_mouse = pygame.Vector2(mouse_screen[0] + cam.x, mouse_screen[1] + cam.y)
                    # shoot from player.pos
                    new_bs = shoot_bullet(player.pos, world_mouse, weapon)
                    bullets.extend(new_bs)
                    player.last_shot = now
                    player.mag -= 1
            if event.button == 3:  # right click starts reload
                player.start_reload(now)

    
    player.update(1.0, keys)

    # handle reload completion
    if player.reloading:
        weapon = player.weapons[player.curr_weapon]
        if now - player.reload_start >= weapon["reload_time"]:
            player.finish_reload()

    # Update bullets
    for b in bullets[:]:
        alive = b.update(1.0)
        # if hit world bounds remove
        if not (0 <= b.pos.x <= WORLD_W and 0 <= b.pos.y <= WORLD_H):
            alive = False
        # collide with obstacles
        if alive:
            for o in obstacles:
                if o.collidepoint(b.pos.x, b.pos.y):
                    alive = False
                    break
        if not alive:
            try:
                bullets.remove(b)
            except ValueError:
                pass

    # Update zombies
    for z in zombies[:]:
        z.update(1.0, player.pos)
        # collision with player
        if z.rect.colliderect(player.rect):
            player.health -= 20 * dt  
            
            push = (z.pos - player.pos)
            if push.length() > 0:
                push.scale_to_length(6)
                player.pos -= push * dt
        # zombies collide with obstacles by simple check
        for o in obstacles:
            if z.rect.colliderect(o):
                # tiny random step to move around obstacle
                z.pos += pygame.Vector2(random.uniform(-1,1), random.uniform(-1,1))

    # Bullet-zombie collisions
    for b in bullets[:]:
        for z in zombies[:]:
            if z.rect.collidepoint(b.pos.x, b.pos.y):
                z.hp -= b.dmg
                try:
                    bullets.remove(b)
                except ValueError:
                    pass
                if z.hp <= 0:
                    player.score += 10 + (z.kind * 5)
                    # chance to spawn pickup
                    if random.random() < 0.2:
                        spawn_pickup(z.pos.x, z.pos.y)
                    try:
                        zombies.remove(z)
                    except ValueError:
                        pass
                break

    # Pickup collisions
    for pu in pickups[:]:
        t, r, val = pu
        if r.collidepoint(player.pos.x, player.pos.y):
            if t == "ammo":
                player.weapons[player.curr_weapon]["reserve"] += val
            else:
                player.health = min(player.max_health, player.health + val)
            pickups.remove(pu)

    # Check if wave cleared
    if len(zombies) == 0:
        last_wave_clear = True

    # spawn passive zombies periodically (if under limit)
    if len(zombies) < 25 and random.random() < 0.02:
        spawn_zombie_offscreen(player.pos, min_dist=300)

    # camera update
    cam.update(player.rect)

    # Draw world to screen
    screen.fill((18, 18, 18))
    draw_world(screen, cam)

    # Draw bullets (world space)
    for b in bullets:
        br = b.rect.copy()
        br = cam.apply(br)
        # rotate bullet to velocity direction
        angle = math.degrees(math.atan2(-b.vel.y, b.vel.x))
        surf = pygame.transform.rotate(bullet_img, angle)
        rect = surf.get_rect(center=(br.centerx, br.centery))
        screen.blit(surf, rect)

    # Draw zombies
    for z in zombies:
        zr = cam.apply(z.rect)
        screen.blit(z.image, zr)
        # hp bar over zombie
        hp_frac = max(0, z.hp / z.max_hp)
        bw = z.rect.width
        hh = 5
        hx = zr.x; hy = zr.y - 8
        pygame.draw.rect(screen, (40,40,40), (hx, hy, bw, hh))
        pygame.draw.rect(screen, (200, 40, 40), (hx, hy, int(bw * hp_frac), hh))

    # Draw obstacles 
    for o in obstacles:
        ro = cam.apply(o)
        # screen.blit placeholder or darker outline already done

    # Draw player (rotated to face mouse)
    mouse_world = pygame.Vector2(pygame.mouse.get_pos()[0] + cam.x, pygame.mouse.get_pos()[1] + cam.y)
    angle = math.degrees(math.atan2(player.pos.y - mouse_world.y, mouse_world.x - player.pos.x))
    player_rot = pygame.transform.rotate(player.image, angle)
    prow = player_rot.get_rect(center=(player.pos.x - cam.x, player.pos.y - cam.y))
    screen.blit(player_rot, prow)

    # Draw pickups
    for t, r, val in pickups:
        pr = cam.apply(r)
        if t == "ammo":
            pygame.draw.rect(screen, BLUE, pr)
            pygame.draw.rect(screen, WHITE, pr, 1)
        else:
            pygame.draw.rect(screen, GREEN, pr)
            pygame.draw.rect(screen, WHITE, pr, 1)

    # HUD
    draw_hud(screen, player, cam)

    pygame.display.flip()

    # Check death
    if player.health <= 0:
        game_over_screen(player.score)
        reset_world()

pygame.quit()
