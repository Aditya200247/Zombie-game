

    
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
