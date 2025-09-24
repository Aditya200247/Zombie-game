import pygame
import random
import sys

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zombie Shooting Game")

font = pygame.font.SysFont("comicsansms", 24)

def safe_load_image(path, size=None):
    try:
        img = pygame.image.load(path)
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except pygame.error:
        print(f"Error loading image: {path}")
        surf = pygame.Surface(size if size else (50, 50))
        surf.fill((200, 0, 0))
        return surf

player_img = safe_load_image("C:/Users/HP/Desktop/assets/player.jpg.png", (60, 60))
player_rect = player_img.get_rect(center=(WIDTH//2, HEIGHT-60))
bullet_img = safe_load_image(r"C:/Users/HP/Desktop/assets/bullet.png", (15, 25))

zombie_imgs = [
    safe_load_image(r"C:\\Users\\HP\\Desktop\\assets\\Zombie1Walk12.png", (50, 50)),
    safe_load_image(r"C:\\Users\\HP\\Desktop\\assets\\h3.png", (60, 60)),
    safe_load_image(r"C:\\Users\\HP\\Desktop\\assets\\Zombie1Walk12.png", (55, 55)),
]

guns = {
    "Pistol": {"speed": 7, "damage": 1},
    "Shotgun": {"speed": 6, "damage": 2},
    "Machine Gun": {"speed": 10, "damage": 1},
}
gun_names = list(guns.keys())
current_gun = 0

bullets = []

zombie_types = [
    {"img": zombie_imgs[0], "speed": 2, "hp": 1},
    {"img": zombie_imgs[1], "speed": 1, "hp": 3},
    {"img": zombie_imgs[2], "speed": 3, "hp": 2},
]
zombies = []

score = 0
clock = pygame.time.Clock()

def spawn_zombie():
    z_type = random.choice(zombie_types)
    zombie_rect = z_type["img"].get_rect()
    zombie_rect.topleft = (random.randint(0, WIDTH-60), -60)
    zombies.append({"rect": zombie_rect, "type": z_type, "hp": z_type["hp"]})

def draw():
    screen.fill((30, 30, 30))
    screen.blit(player_img, player_rect)
    for b in bullets:
        screen.blit(bullet_img, b["rect"])
    for z in zombies:
        screen.blit(z["type"]["img"], z["rect"])
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    gun_text = font.render(f"Gun: {gun_names[current_gun]}", True, (255, 255, 255))
    screen.blit(score_text, (10, 10))
    screen.blit(gun_text, (10, 40))
    pygame.display.flip()

def game_over_screen(score):
    screen.fill((10, 10, 10))
    over_text = font.render("GAME OVER!", True, (255, 0, 0))
    score_text = font.render(f"Final Score: {score}", True, (255, 255, 255))
    info_text = font.render("Press R to Restart or Q to Quit", True, (200, 200, 200))
    screen.blit(over_text, (WIDTH//2 - over_text.get_width()//2, HEIGHT//2 - 80))
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2 - 30))
    screen.blit(info_text, (WIDTH//2 - info_text.get_width()//2, HEIGHT//2 + 20))
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_r:
                    waiting = False

def reset_game():
    global bullets, zombies, score, player_rect, current_gun
    bullets = []
    zombies = []
    score = 0
    player_rect = player_img.get_rect(center=(WIDTH//2, HEIGHT-60))
    current_gun = 0

while True:
    reset_game()
    zombie_timer = 0
    running = True
    while running:
        clock.tick(60)
        zombie_timer += 1
        if zombie_timer > 50:
            spawn_zombie()
            zombie_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    gun = guns[gun_names[current_gun]]
                    bullet = bullet_img.get_rect(center=(player_rect.centerx, player_rect.top))
                    bullets.append({"rect": bullet, "speed": gun["speed"], "damage": gun["damage"]})
                if event.key == pygame.K_TAB:
                    current_gun = (current_gun + 1) % len(gun_names)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player_rect.left > 0:
            player_rect.x -= 5
        if keys[pygame.K_RIGHT] and player_rect.right < WIDTH:
            player_rect.x += 5

        for b in bullets[:]:
            b["rect"].y -= b["speed"]
            if b["rect"].bottom < 0:
                bullets.remove(b)

        for z in zombies[:]:
            z["rect"].y += z["type"]["speed"]
            if z["rect"].top > HEIGHT:
                zombies.remove(z)
            if z["rect"].colliderect(player_rect):
                running = False

        for b in bullets[:]:
            for z in zombies[:]:
                if b["rect"].colliderect(z["rect"]):
                    z["hp"] -= b["damage"]
                    if b in bullets:
                        bullets.remove(b)
                    if z["hp"] <= 0:
                        zombies.remove(z)
                        score += 10
                    break

        draw()
    game_over_screen(score)