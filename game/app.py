"""Combate, habilidades y mapa de Soul Arena."""
import math
import os
import random
import sys
import pygame
from .art import Art, CHARACTER_SCALE, Effect, facing_for
from .entities import Bullet, Enemy, HealthPickup, Player, Vec
from .progression import SkillTree, ZoneGraph
from .world import Arena, circle_hit_time

BG, PANEL = (8, 16, 28), (12, 23, 38)
WHITE, MUTED = (226, 233, 244), (143, 160, 184)
CYAN, GOLD, RED, GREEN = (72, 210, 234), (246, 199, 94), (236, 91, 111), (104, 220, 161)


PINK = (245, 49, 131)
CRITICAL_RED = (255, 67, 82)
GUARDIAN_MAX_HEALTH = 300
ZONE_TIERS = {"camp": 0, "ruins": 1, "crypt": 2, "core": 3}


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 720))
        pygame.display.set_caption("Soul Arena | Grupo 8")
        self.art = Art()
        self.font, self.small, self.title = self.art.font, self.art.small, self.art.title
        self.critical_glow = pygame.Surface((112, 112), pygame.SRCALPHA)
        for radius in range(55, 0, -1):
            alpha = round(115 * (1 - radius / 56) ** 2)
            pygame.draw.circle(self.critical_glow, (*CRITICAL_RED, alpha), (56, 56), radius)
        self.health_cross = pygame.Surface((52, 52), pygame.SRCALPHA)
        for radius in range(25, 0, -1):
            alpha = round(175 * (1 - radius / 26) ** 2)
            pygame.draw.circle(self.health_cross, (53, 255, 106, alpha), (26, 26), radius)
        pygame.draw.rect(self.health_cross, (12, 74, 38), (21, 15, 10, 22))
        pygame.draw.rect(self.health_cross, (12, 74, 38), (15, 21, 22, 10))
        pygame.draw.rect(self.health_cross, (166, 255, 160), (23, 17, 6, 18))
        pygame.draw.rect(self.health_cross, (166, 255, 160), (17, 23, 18, 6))
        self.clock = pygame.time.Clock()
        self.running, self.buttons = True, []
        self.reset()

    def reset(self):
        self.player, self.tree, self.graph = Player(), SkillTree(), ZoneGraph()
        self.souls, self.kills = 0, 0
        self.zone, self.scene = "camp", "intro"
        self.message, self.message_time = "", 0
        self.load_zone()

    def load_zone(self):
        self.enemies, self.bullets = [], []
        self.guardian = Arena.art_point((835, 427))
        self.guardian_health = GUARDIAN_MAX_HEALTH
        self.effects, self.fallen = [], []
        self.health_pickups = []
        self.hurt = self.shot = 0
        self.fire_pressed = False
        self.aim, self.moving = Vec(0, -1), False
        self.facing, self.walk_distance, self.idle_time = 0, 0.0, 0.0
        self.world = Arena(self.guardian)
        self.player.position, self.player.health = Arena.art_point((835, 828)), self.player.max_health
        self.player.cooldown = 0
        self.wave, self.pending, self.spawn_timer = 0, 0, 0
        self.wave_timer, self.cleared = 3, False
        self.healing_slots = set()

    @property
    def level(self):
        return 1 + len(self.graph.completed)

    def start_wave(self, tier):
        self.wave += 1
        self.pending = 7 + self.wave * 2 + tier * (self.wave + 1)
        # Cada posición seleccionada reemplaza a un minion normal.
        count = random.choices((0, 1, 2), weights=(20, 65, 15))[0]
        self.healing_slots = set(random.sample(range(self.pending - 1), count))
        self.spawn_timer, self.wave_timer = 0, 3

    def notify(self, message):
        self.message, self.message_time = message, 3

    def text(self, message, position, color=WHITE, font=None, center=False):
        surface = (font or self.font).render(str(message), False, color)
        rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
        self.screen.blit(surface, rect)

    def button(self, rect, label, action, *, icon=None, enabled=True, selected=False):
        rect = pygame.Rect(rect)
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if not enabled:
            state = 3
        elif hovered and pygame.mouse.get_pressed()[0]:
            state = 2
        else:
            state = 1 if hovered or selected else 0
        self.art.ui_image(self.screen, 0, state, rect)
        if icon:
            x = rect.centerx - 10 if not label else rect.left + 13
            self.art.ui_image(self.screen, *icon, (x, rect.centery - 10, 20, 20))
        if label:
            x = rect.centerx + (12 if icon else 0)
            self.text(label, (x, rect.centery + (2 if state == 2 else 0)),
                      WHITE if enabled else MUTED, center=True)
        if enabled:
            self.buttons.append((rect, action))

    def bar(self, x, y, width, ratio, color):
        pygame.draw.rect(self.screen, (48, 56, 72), (x, y, width, 6))
        pygame.draw.rect(self.screen, color, (x, y, int(width * max(0, min(1, ratio))), 6))

    def draw_actor_health(self, position, offset, width, ratio, color):
        x, y = round(position.x), round(position.y + offset)
        pygame.draw.rect(self.screen, BG, (x - width // 2 - 1, y - 1, width + 2, 8))
        critical = 0 < ratio < .2
        self.bar(x - width // 2, y, width, ratio, CRITICAL_RED if critical else color)
        if critical:
            label = (x, y + 15)
            self.text("CRITICO", (x, label[1] + 1), BG, self.small, center=True)
            self.text("CRITICO", label, CRITICAL_RED, self.small, center=True)

    def set_scene(self, scene):
        self.scene = scene

    def handle(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            key = event.key
            active = self.scene in ("arena", "skills", "map", "pause")
            if key == pygame.K_ESCAPE and active:
                self.scene = "pause" if self.scene == "arena" else "arena"
            elif key == pygame.K_TAB and active:
                self.scene = "arena" if self.scene == "skills" else "skills"
            elif key == pygame.K_m and active:
                self.scene = "arena" if self.scene == "map" else "map"
            elif key == pygame.K_p and self.scene in ("arena", "pause"):
                self.scene = "arena" if self.scene == "pause" else "pause"
            elif key == pygame.K_RETURN and self.scene == "intro":
                self.scene = "arena"
            elif key == pygame.K_r and self.scene in ("dead", "win"):
                self.restart()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.scene == "arena" and event.pos[1] >= 80:
                self.fire_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for rect, action in reversed(self.buttons):
                if rect.collidepoint(event.pos):
                    action()
                    break

    def update(self, dt):
        self.message_time = max(0, self.message_time - dt)
        if self.scene != "arena":
            self.fire_pressed = False
            return
        self.hurt = max(0, self.hurt - dt)
        self.shot = max(0, self.shot - dt)
        for effects in (self.effects, self.fallen):
            for effect in effects:
                effect.age += dt
            effects[:] = [effect for effect in effects if not effect.finished]
        previous = self.player.position.copy()
        self.player.update(dt, pygame.key.get_pressed(), self.world)
        distance = self.player.position.distance_to(previous)
        self.moving = distance > .01
        if self.moving:
            self.walk_distance += distance
            self.idle_time = 0
        else:
            self.walk_distance = 0
            self.idle_time += dt
        mouse = Vec(pygame.mouse.get_pos())
        aim = mouse - self.player.position
        if mouse.y >= 80 and aim.length_squared() >= 8 ** 2:
            self.aim = aim.normalize()
            self.facing = facing_for(self.aim, self.facing)
        self.update_health_pickups(dt)
        if self.cleared:
            self.fire_pressed = False
            return
        firing = self.fire_pressed or pygame.mouse.get_pressed()[0]
        self.fire_pressed = False
        if firing and self.player.cooldown == 0 and mouse.y >= 80:
            origin = self.shot_origin(self.player.position, self.facing, mouse, False)
            direction = mouse - origin
            direction = direction.normalize() if aim.length_squared() >= 8 ** 2 else self.aim
            self.bullets.append(Bullet(origin, direction * self.player.projectile_speed, self.player.damage))
            self.player.cooldown = self.player.interval
            self.shot = .065
            self.muzzle(origin, direction, False)
        tier = ZONE_TIERS[self.zone]
        if not self.enemies and self.pending == 0:
            if self.wave >= 3:
                self.cleared = True
                first_clear = self.zone not in self.graph.completed
                self.graph.completed.add(self.zone)
                self.souls += 15
                if self.zone == "core":
                    self.scene = "win"
                else:
                    message = f"Nivel {self.level} · " if first_clear else ""
                    self.notify(message + "Zona completada: +15 almas. Abrí el mapa con M.")
                return
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.start_wave(tier)
        if self.pending:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                position = random.choice(self.world.spawn_points)
                difficulty = tier * (1 + .25 * (self.wave - 1))
                self.pending -= 1
                self.enemies.append(Enemy(position, difficulty, healing=self.pending in self.healing_slots))
                self.spawn_timer = max(.25, .7 - .1 * difficulty)
        self.update_bullets(dt)
        for enemy in self.enemies[:]:
            if enemy.health <= 0:
                self.enemies.remove(enemy)
                self.souls += 5 + tier
                self.kills += 1
                self.effects.append(Effect((16, 17), enemy.position.copy(), .14))
                self.fallen.append(Effect((21 if enemy.healing else 20,), enemy.position.copy(), .8))
                if enemy.healing:
                    self.health_pickups.append(HealthPickup(enemy.position.copy()))
            else:
                count = len(self.bullets)
                enemy.update(dt, self.player, self.guardian, self.world, self.bullets)
                enemy.facing = facing_for(enemy.aim, enemy.facing)
                if len(self.bullets) > count:
                    bullet = self.bullets[-1]
                    target = self.guardian if enemy.guardian_locked else self.player.position
                    origin = self.shot_origin(enemy.position, enemy.facing, target, True)
                    direction = (target - origin).normalize()
                    bullet.position, bullet.velocity = origin, direction * bullet.velocity.length()
                    self.muzzle(origin, direction, True)
        if self.player.health <= 0 or self.guardian_health <= 0:
            self.scene = "dead"

    def update_health_pickups(self, dt):
        player = self.player
        for pickup in self.health_pickups[:]:
            pickup.remaining -= dt
            if pickup.remaining <= 0:
                self.health_pickups.remove(pickup)
            elif (0 < player.health < player.max_health
                  and player.position.distance_squared_to(pickup.position) <= (player.radius + pickup.radius) ** 2):
                restored = min(player.max_health - player.health, player.max_health * .2)
                player.health += restored
                self.health_pickups.remove(pickup)
                self.notify(f"Cruz verde · +{restored:.0f} de vida")

    def draw_health_pickups(self):
        for pickup in self.health_pickups:
            alpha = 255
            if pickup.remaining <= 4:
                elapsed = 4 - pickup.remaining
                cycles = elapsed * 2 if elapsed < 2 else 4 + (elapsed - 2) * 4
                alpha = round(40 + 215 * (1 + math.cos(math.tau * cycles)) / 2)
            self.health_cross.set_alpha(alpha)
            self.art.sprite(self.screen, self.health_cross, pickup.position)

    def shot_origin(self, position, facing, target, hostile):
        offset = self.art.muzzle_offset(facing, hostile)
        origin = position + offset
        if ((target - position).length_squared() <= offset.length_squared()
                or not self.world.visible(position, origin, 4)):
            return position.copy()
        return origin

    def muzzle(self, position, aim, hostile):
        frames = (5, 6, 7) if hostile else (1, 2, 3)
        self.effects.append(Effect(frames, position.copy(), .03, aim.angle_to(Vec(1, 0))))

    def update_bullets(self, dt):
        for bullet in self.bullets[:]:
            start = bullet.position.copy()
            end = start + bullet.velocity * min(dt, bullet.ttl)
            wall_t = self.world.wall_hit_time(start, end, 4)
            hit_t, target = wall_t, None
            if bullet.hostile:
                candidates = [(self.player, self.player.position, self.player.radius),
                              ("guardian", self.guardian, 28)]
            else:
                candidates = [(enemy, enemy.position, enemy.radius)
                              for enemy in self.enemies if enemy.health > 0]
            for candidate, position, radius in candidates:
                t = circle_hit_time(start, end, position, radius + 4)
                if t is not None and (hit_t is None or t < hit_t):
                    hit_t, target = t, candidate
            if hit_t is not None:
                impact = start.lerp(end, hit_t)
                if target == "guardian":
                    self.guardian_health -= bullet.damage
                    self.effects.append(Effect((18, 19), impact, .075))
                elif target is not None:
                    if target is self.player:
                        target.health -= bullet.damage * (1 - target.armor)
                        self.hurt = .11
                    else:
                        target.health -= bullet.damage
                        target.hurt = .11
                    self.effects.append(Effect((12, 13, 14, 15), impact, .04))
                else:
                    self.effects.append(Effect((8, 9, 10, 11), impact, .045))
                self.bullets.remove(bullet)
                continue
            bullet.position = end
            bullet.ttl -= dt
            if bullet.ttl <= 0 or not self.world.bounds.collidepoint(end):
                self.bullets.remove(bullet)

    def draw_arena(self):
        self.screen.blit(self.art.arena, (0, 80))
        p = self.player
        player_health = p.health / p.max_health
        guardian_health = self.guardian_health / GUARDIAN_MAX_HEALTH
        pulse = (1 + math.cos(pygame.time.get_ticks() * math.tau / 800)) / 2
        self.critical_glow.set_alpha(round(45 + 210 * pulse))
        for position, ratio in ((p.position, player_health), (self.guardian, guardian_health)):
            if 0 < ratio < .2:
                self.art.sprite(self.screen, self.critical_glow, position)

        for fallen in self.fallen:
            self.art.draw_effect(self.screen, fallen)
        self.draw_health_pickups()
        for enemy in self.enemies:
            if enemy.guardian_locked:
                pygame.draw.circle(self.screen, GOLD, enemy.position, enemy.radius + 3, 1)
            self.art.enemy_sprite(self.screen, enemy)
            if enemy.health < enemy.max_health:
                self.bar(enemy.position.x - 14, enemy.position.y - 26 * CHARACTER_SCALE, 28,
                         enemy.health / enemy.max_health, GREEN if enemy.healing else PINK)
        if p.health > 0:
            self.art.player_sprite(self.screen, p.position, self.facing, self.walk_distance,
                                   self.idle_time, self.moving, self.hurt, self.shot)
        else:
            self.art.sprite(self.screen, self.art.player_fallen, p.position)
        for bullet in self.bullets:
            frame = self.art.effects[4 if bullet.hostile else 0]
            self.art.sprite(self.screen, frame, bullet.position, bullet.velocity.angle_to(Vec(1, 0)))
        for effect in self.effects:
            self.art.draw_effect(self.screen, effect)

        self.draw_actor_health(p.position, 30, 44, player_health, CYAN)
        self.draw_actor_health(self.guardian, 48, 74, guardian_health, GOLD)

        pygame.draw.rect(self.screen, PANEL, (0, 0, 1200, 80))
        pygame.draw.line(self.screen, (26, 111, 124), (0, 79), (1200, 79), 2)
        self.text("SOUL ARENA", (20, 9), CYAN)
        self.art.ui_image(self.screen, 2, 3, (20, 43, 21, 18))
        self.text(f"{self.graph.names[self.zone]}  {self.wave}/3", (50, 42), MUTED, self.small)
        self.art.ui_image(self.screen, 2, 0, (220, 19, 24, 22))
        self.text(f"{max(0, int(p.health))}/{p.max_health}", (254, 17))
        self.bar(220, 51, 140, player_health, CYAN)
        self.art.ui_image(self.screen, 2, 1, (405, 15, 18, 26))
        self.text(f"{max(0, int(self.guardian_health))}/{GUARDIAN_MAX_HEALTH}", (435, 17))
        self.bar(405, 51, 140, guardian_health, GOLD)
        self.art.ui_image(self.screen, 2, 2, (595, 13, 17, 26))
        self.text(f"Almas {self.souls}", (624, 17), CYAN)
        self.text(f"Nivel {self.level} · Bajas {self.kills}", (624, 43), MUTED, self.small)
        self.button((768, 16, 192, 46), "TAB Habilidades", lambda: self.set_scene("skills"), icon=(1, 5))
        self.button((971, 16, 133, 46), "M Mapa", lambda: self.set_scene("map"), icon=(1, 4))
        self.button((1115, 16, 65, 46), "", lambda: self.set_scene("pause"), icon=(1, 1))
        if self.cleared:
            self.text("ZONA COMPLETADA · Abrí M para viajar", (600, 570), GREEN, center=True)
        elif self.pending == 0 and not self.enemies and self.scene == "arena":
            self.text(f"Próxima oleada en {max(1, math.ceil(self.wave_timer))}", (600, 145), GOLD, center=True)
        self.text("WASD mover   ·   Mouse apuntar y disparar   ·   P pausa", (20, 691), MUTED, self.small)

    def draw_skills(self):
        self.text("ÁRBOL DE HABILIDADES", (60, 35), CYAN, self.title)
        self.text(f"Nivel {self.level} · Almas: {self.souls} · Completá zonas para abrir más habilidades.", (60, 92), GOLD)
        positions = {"basic": (600, 169), "damage": (335, 283), "speed": (865, 283),
                     "damage2": (165, 398), "health": (435, 398), "speed2": (765, 398), "move": (1035, 398),
                     "armor": (435, 523), "velocity": (765, 523)}
        for node in self.tree.preorder():
            if node.parent:
                pygame.draw.line(self.screen, GREEN if node.unlocked else (65, 80, 103), positions[node.parent.key], positions[node.key], 3)
        icons = {"basic": (3, 0), "damage": (3, 0), "damage2": (3, 0),
                 "speed": (3, 1), "speed2": (3, 1), "health": (2, 0), "move": (3, 2),
                 "armor": (2, 1), "velocity": (3, 0)}
        for node in self.tree.preorder():
            x, y = positions[node.key]
            label = node.name + (" · OK" if node.unlocked else f" · {node.cost}")
            self.button((x - 115, y - 30, 230, 60), label, lambda key=node.key: self.buy_skill(key), icon=icons[node.key], selected=node.unlocked,
                        enabled=node.unlocked or (self.level >= node.min_level and node.parent.unlocked))
            detail = f"Requiere nivel {node.min_level}" if self.level < node.min_level else node.description
            self.text(detail, (x, y + 45), MUTED, self.small, True)
        self.button((930, 645, 210, 45), "Volver · TAB", lambda: self.set_scene("arena"), icon=(1, 3))

    def buy_skill(self, key):
        self.souls, bought, message = self.tree.buy(key, self.souls, level=self.level)
        if bought:
            self.player.apply_skill(key)
        self.notify(message)

    def travel(self, key):
        self.souls, allowed, message = self.graph.access(self.zone, key, self.souls)
        self.notify(message)
        if allowed:
            self.zone = key
            self.load_zone()
            self.scene = "arena"

    def draw_map(self):
        self.text("MAPA DE ZONAS", (60, 35), CYAN, self.title)
        self.text(f"Almas: {self.souls}  ·  Completá una zona para comprar sus rutas. Repetir zonas abiertas es gratis.", (60, 92), GOLD)
        positions = {"camp": (200, 355), "ruins": (600, 230), "crypt": (600, 480), "core": (1000, 355)}
        for source, edges in self.graph.adjacency.items():
            for target, cost in edges:
                a, b = Vec(positions[source]), Vec(positions[target])
                direction = (b - a).normalize()
                start, end = a + direction * 110, b - direction * 110
                pygame.draw.line(self.screen, (78, 98, 124), start, end, 3)
                normal = Vec(-direction.y, direction.x)
                pygame.draw.polygon(self.screen, GOLD, [end, end - direction * 13 + normal * 7, end - direction * 13 - normal * 7])
                self.text(str(cost) + " almas", (a + b) / 2 + Vec(0, -20), GOLD, self.small, True)
        for key, (x, y) in positions.items():
            opened = key in self.graph.unlocked
            self.button((x - 105, y - 35, 210, 70), self.graph.names[key], lambda k=key: self.travel(k), icon=(3, 3) if key == "core" else (1, 4), selected=opened)
            status = "Actual · clic para repetir" if key == self.zone else "Abierta · viajar gratis" if opened else "Bloqueada"
            self.text(status, (x, y + 55), CYAN if key == self.zone else MUTED, self.small, True)
            if key in self.graph.completed:
                self.text("Completada", (x, y + 80), GREEN, self.small, True)
        self.text("Viajar reinicia el combate y restaura la vida. Conservás almas y habilidades.", (60, 640), MUTED, self.small)
        self.button((930, 660, 210, 40), "Volver · M", lambda: self.set_scene("arena"), icon=(1, 3))

    def draw_card(self, title, subtitle, lines, label, action, icon=(1, 0)):
        self.screen.blit(self.art.arena, (0, 80))
        if self.scene == "dead":
            self.draw_arena()
            self.buttons.clear()
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill((4, 8, 19, 190))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, PANEL, (220, 135, 760, 460))
        pygame.draw.rect(self.screen, (32, 125, 146), (220, 135, 760, 460), 2)
        self.text(title, (600, 190), CYAN, self.title, True)
        self.text(subtitle, (600, 245), GOLD, center=True)
        for i, line in enumerate(lines):
            self.text(line, (600, 305 + i * 34), WHITE, center=True)
        self.button((440, 510, 320, 55), label, action, icon=icon)

    def draw(self):
        self.screen.fill(BG)
        self.buttons = []
        if self.scene == "arena":
            self.draw_arena()
        elif self.scene == "skills":
            self.draw_skills()
        elif self.scene == "map":
            self.draw_map()
        elif self.scene == "intro":
            self.draw_card("SOUL ARENA", "Grupo 8", [
                "Defendé el guardián durante tres oleadas por zona.",
                "WASD para moverte. Apuntá y dispará con el mouse.",
                "Recogé la cruz del minion verde: cura hasta 20% de vida.",
                "Completá zonas y usá M para avanzar hasta el Núcleo."], "Jugar · Enter", lambda: self.set_scene("arena"))
        elif self.scene == "pause":
            self.draw_card("PAUSA", "Soul Arena", [
                "TAB: habilidades  ·  M: mapa", "El árbol y el mapa también pausan el juego."],
                "Continuar · P / Esc", lambda: self.set_scene("arena"))
        else:
            won = self.scene == "win"
            reason = "El guardián fue destruido." if self.guardian_health <= 0 else "Tu personaje cayó."
            self.draw_card("VICTORIA" if won else "DERROTA", "Completaste el Núcleo." if won else reason,
                           [f"Bajas: {self.kills}  ·  Almas restantes: {self.souls}",
                            "R reinicia la partida, incluyendo habilidades y zonas."],
                           "Nueva partida · R", self.restart, icon=(1, 2))
        if self.message_time > 0:
            pygame.draw.rect(self.screen, (42, 50, 68), (210, 563, 780, 42), border_radius=10)
            self.text(self.message, (600, 584), GOLD, self.small, True)
        pygame.display.flip()

    def restart(self):
        self.reset()
        self.scene = "arena"


def run():
    smoke = "--smoke-test" in sys.argv
    if smoke:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    game = Game()
    frames = 0
    while game.running:
        dt = min(game.clock.tick(60) / 1000, .05)
        for event in pygame.event.get():
            game.handle(event)
        game.update(dt)
        game.draw()
        frames += 1
        if smoke and frames >= 10:
            game.running = False
    pygame.quit()


if __name__ == "__main__":
    run()
