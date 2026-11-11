"""Interfaz provisional: combate, habilidades y mapa."""
import math
import os
import random
import sys
import pygame
from .entities import Bullet, Enemy, Player, Vec
from .progression import SkillTree, ZoneGraph
from .world import Arena, circle_hit_time

BG, PANEL = (16, 21, 33), (27, 36, 53)
WHITE, MUTED = (226, 233, 244), (143, 160, 184)
CYAN, GOLD, RED, GREEN = (72, 210, 234), (246, 199, 94), (236, 91, 111), (104, 220, 161)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 720))
        pygame.display.set_caption("Soul Arena | Prototipo Grupo 8")
        self.font = pygame.font.SysFont("Segoe UI", 19)
        self.small = pygame.font.SysFont("Segoe UI", 15)
        self.title = pygame.font.SysFont("Segoe UI", 36, bold=True)
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
        self.guardian, self.guardian_health = Vec(600, 320), 300
        self.world = Arena(self.guardian)
        self.player.position, self.player.health = Vec(600, 440), self.player.max_health
        self.player.cooldown = 0
        self.wave, self.pending, self.spawn_timer = 0, 0, 0
        self.wave_timer, self.cleared = 3, False

    def notify(self, message):
        self.message, self.message_time = message, 3

    def text(self, message, position, color=WHITE, font=None, center=False):
        surface = (font or self.font).render(str(message), True, color)
        rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
        self.screen.blit(surface, rect)

    def button(self, rect, label, action, color=PANEL):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, tuple(min(255, c + 15) for c in color) if hover else color, rect, border_radius=10)
        pygame.draw.rect(self.screen, CYAN if hover else (60, 76, 100), rect, 1, border_radius=10)
        self.text(label, rect.center, center=True)
        self.buttons.append((rect, action))

    def bar(self, x, y, width, ratio, color):
        pygame.draw.rect(self.screen, (48, 56, 72), (x, y, width, 7), border_radius=3)
        pygame.draw.rect(self.screen, color, (x, y, int(width * max(0, min(1, ratio))), 7), border_radius=3)

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
            for rect, action in reversed(self.buttons):
                if rect.collidepoint(event.pos):
                    action()
                    break

    def update(self, dt):
        self.message_time = max(0, self.message_time - dt)
        if self.scene != "arena" or self.cleared:
            return
        self.player.update(dt, pygame.key.get_pressed(), self.world)
        if pygame.mouse.get_pressed()[0] and self.player.cooldown == 0 and pygame.mouse.get_pos()[1] > 80:
            direction = Vec(pygame.mouse.get_pos()) - self.player.position
            if direction.length_squared():
                direction = direction.normalize()
                self.bullets.append(Bullet(self.player.position.copy(), direction * 650, self.player.damage))
                self.player.cooldown = self.player.interval
        difficulty = {"camp": 0, "ruins": 1, "crypt": 2, "core": 3}[self.zone]
        if not self.enemies and self.pending == 0:
            if self.wave >= 3:
                self.cleared = True
                self.graph.completed.add(self.zone)
                self.souls += 15
                if self.zone == "core":
                    self.scene = "win"
                else:
                    self.notify("Zona completada: +15 almas. Abrí el mapa con M.")
                return
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.wave += 1
                self.pending = 7 + self.wave * 2 + difficulty * 2
                self.spawn_timer, self.wave_timer = 0, 3
        if self.pending:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                position = random.choice(self.world.spawn_points)
                self.enemies.append(Enemy(position, difficulty))
                self.pending -= 1
                self.spawn_timer = max(.3, .7 - difficulty * .1)
        self.update_bullets(dt)
        for enemy in self.enemies[:]:
            if enemy.health <= 0:
                self.enemies.remove(enemy)
                self.souls += 5 + difficulty
                self.kills += 1
            else:
                enemy.update(dt, self.player, self.guardian, self.world, self.bullets)
        if self.player.health <= 0 or self.guardian_health <= 0:
            self.scene = "dead"

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
                if target == "guardian":
                    self.guardian_health -= bullet.damage
                elif target is not None:
                    target.health -= bullet.damage
                self.bullets.remove(bullet)
                continue
            bullet.position = end
            bullet.ttl -= dt
            if bullet.ttl <= 0 or not self.world.bounds.collidepoint(end):
                self.bullets.remove(bullet)

    def draw_arena(self):
        for x in range(0, 1200, 40):
            pygame.draw.line(self.screen, (24, 32, 46), (x, 85), (x, 720))
        for y in range(85, 720, 40):
            pygame.draw.line(self.screen, (24, 32, 46), (0, y), (1200, y))
        pygame.draw.rect(self.screen, (72, 87, 110), self.world.bounds, 3)
        for wall in self.world.walls:
            pygame.draw.rect(self.screen, (7, 12, 22), wall.move(5, 5), border_radius=3)
            pygame.draw.rect(self.screen, (65, 79, 101), wall, border_radius=3)
            pygame.draw.rect(self.screen, (108, 128, 151), wall, 2, border_radius=3)
        for point in self.world.spawn_points:
            pygame.draw.circle(self.screen, (102, 47, 63), point, 19, 2)
        pygame.draw.circle(self.screen, (32, 65, 66), self.guardian, 70, 1)
        pygame.draw.rect(self.screen, GREEN, (574, 294, 52, 52), border_radius=9)
        self.text("GUARDIÁN", (600, 260), GREEN, self.small, True)
        self.bar(565, 355, 70, self.guardian_health / 300, GREEN)
        for bullet in self.bullets:
            color = RED if bullet.hostile else GOLD
            if bullet.velocity.length_squared():
                pygame.draw.line(self.screen, color, bullet.position,
                                 bullet.position - bullet.velocity.normalize() * 12, 3)
            pygame.draw.circle(self.screen, color, bullet.position, 4)
        for enemy in self.enemies:
            pygame.draw.circle(self.screen, RED, enemy.position, enemy.radius)
            pygame.draw.line(self.screen, GOLD if enemy.guardian_locked else WHITE,
                             enemy.position, enemy.position + enemy.aim * 20, 3)
            if enemy.guardian_locked:
                pygame.draw.circle(self.screen, GOLD, enemy.position, enemy.radius + 4, 1)
            self.bar(enemy.position.x - 15, enemy.position.y - 22, 30, enemy.health / enemy.max_health, RED)
        p = self.player
        pygame.draw.circle(self.screen, CYAN, p.position, p.radius)
        aim = Vec(pygame.mouse.get_pos()) - p.position
        if aim.length_squared():
            pygame.draw.line(self.screen, WHITE, p.position, p.position + aim.normalize() * 26, 5)
        pygame.draw.rect(self.screen, PANEL, (0, 0, 1200, 80))
        self.text("SOUL ARENA", (20, 12), CYAN)
        self.text(self.graph.names[self.zone] + "  |  Oleada " + str(self.wave) + "/3", (20, 43), MUTED, self.small)
        self.text(f"Vida {max(0, int(p.health))}/{p.max_health}", (230, 15))
        self.bar(230, 49, 140, p.health / p.max_health, CYAN)
        self.text(f"Guardián {max(0, int(self.guardian_health))}/300", (400, 15))
        self.text(f"Almas: {self.souls}", (630, 15), GOLD)
        self.text(f"Bajas: {self.kills}", (630, 44), MUTED, self.small)
        self.button((790, 17, 175, 44), "TAB · Habilidades", lambda: self.set_scene("skills"))
        self.button((980, 17, 125, 44), "M · Mapa", lambda: self.set_scene("map"))
        self.button((1120, 17, 60, 44), "II", lambda: self.set_scene("pause"))
        if self.cleared:
            self.text("ZONA COMPLETADA · Abrí M para viajar o repetir", (600, 570), GREEN, center=True)
        elif self.pending == 0 and not self.enemies:
            self.text(f"Próxima oleada en {max(1, math.ceil(self.wave_timer))}", (600, 140), GOLD, center=True)
        self.text("WASD: mover   |   Mouse: apuntar   |   Clic sostenido: disparar   |   P: pausa", (20, 694), MUTED, self.small)

    def draw_skills(self):
        self.text("ÁRBOL DE HABILIDADES", (60, 35), CYAN, self.title)
        self.text(f"Almas: {self.souls}  ·  Comprá el padre antes que sus hijos. Ambas ramas se pueden desarrollar.", (60, 92), GOLD)
        positions = {"basic": (600, 195), "damage": (335, 340), "speed": (865, 340),
                     "damage2": (180, 500), "health": (440, 500), "speed2": (760, 500), "move": (1020, 500)}
        for node in self.tree.preorder():
            if node.parent:
                pygame.draw.line(self.screen, GREEN if node.unlocked else (65, 80, 103), positions[node.parent.key], positions[node.key], 3)
        for node in self.tree.preorder():
            x, y = positions[node.key]
            label = node.name + (" · OK" if node.unlocked else f" · {node.cost}")
            self.button((x - 115, y - 30, 230, 60), label, lambda key=node.key: self.buy_skill(key), (30, 77, 65) if node.unlocked else PANEL)
            self.text(node.description, (x, y + 45), MUTED, self.small, True)
        self.text("Árbol binario manual · 7 nodos · Un único padre y hasta dos hijos por habilidad.", (60, 625), MUTED, self.small)
        self.button((930, 645, 210, 45), "Volver · TAB / Esc", lambda: self.set_scene("arena"))

    def buy_skill(self, key):
        self.souls, bought, message = self.tree.buy(key, self.souls)
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
            self.button((x - 105, y - 35, 210, 70), self.graph.names[key], lambda k=key: self.travel(k), (30, 77, 65) if opened else PANEL)
            status = "Actual · clic para repetir" if key == self.zone else "Abierta · viajar gratis" if opened else "Bloqueada"
            self.text(status, (x, y + 55), CYAN if key == self.zone else MUTED, self.small, True)
            if key in self.graph.completed:
                self.text("Completada", (x, y + 80), GREEN, self.small, True)
        order = " > ".join(self.graph.names[k] for k in self.graph.bfs("camp"))
        self.text("Recorrido BFS: " + order, (60, 610), MUTED, self.small)
        self.text("Viajar reinicia el combate y restaura la vida. Conservás almas y habilidades.", (60, 640), MUTED, self.small)
        self.button((930, 660, 210, 40), "Volver · M / Esc", lambda: self.set_scene("arena"))

    def draw_card(self, title, subtitle, lines, label, action):
        pygame.draw.rect(self.screen, PANEL, (220, 135, 760, 460), border_radius=20)
        self.text(title, (600, 190), CYAN, self.title, True)
        self.text(subtitle, (600, 245), GOLD, center=True)
        for i, line in enumerate(lines):
            self.text(line, (600, 305 + i * 34), WHITE, center=True)
        self.button((440, 510, 320, 55), label, action)

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
            self.draw_card("SOUL ARENA", "Prototipo funcional · Grupo 8", [
                "Defendé el guardián durante tres oleadas por zona.",
                "WASD para moverte. Apuntá y dispará con el mouse.",
                "Ganás almas con cada baja: TAB abre las habilidades.",
                "Completá zonas y usá M para avanzar hasta el Núcleo."], "Jugar · Enter", lambda: self.set_scene("arena"))
        elif self.scene == "pause":
            self.draw_card("PAUSA", "El combate está detenido", [
                "TAB: habilidades  ·  M: mapa", "El árbol y el mapa también pausan el juego."],
                "Continuar · P / Esc", lambda: self.set_scene("arena"))
        else:
            won = self.scene == "win"
            reason = "El guardián fue destruido." if self.guardian_health <= 0 else "Tu personaje cayó."
            self.draw_card("VICTORIA" if won else "DERROTA", "Completaste el Núcleo." if won else reason,
                           [f"Bajas: {self.kills}  ·  Almas restantes: {self.souls}",
                            "R reinicia la partida, incluyendo habilidades y zonas."],
                           "Nueva partida · R", self.restart)
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
