"""Entidades y comportamiento básico del combate."""
from dataclasses import dataclass
import pygame

Vec = pygame.Vector2


@dataclass
class Bullet:
    position: Vec
    velocity: Vec
    damage: float
    ttl: float = 1.5
    hostile: bool = False


class Player:
    def __init__(self):
        self.position = Vec(600, 440)
        self.radius = 15
        self.max_health = 100
        self.health = 100
        self.damage = 20
        self.speed = 250
        self.interval = .28
        self.cooldown = 0

    def apply_skill(self, key):
        if key == "damage":
            self.damage += 8
        elif key == "damage2":
            self.damage += 12
        elif key == "health":
            self.max_health += 40
            self.health = min(self.max_health, self.health + 40)
        elif key in ("speed", "speed2"):
            self.interval *= .75
        elif key == "move":
            self.speed *= 1.25

    def update(self, dt, keys, world=None):
        direction = Vec(int(keys[pygame.K_d]) - int(keys[pygame.K_a]),
                        int(keys[pygame.K_s]) - int(keys[pygame.K_w]))
        if direction.length_squared():
            delta = direction.normalize() * self.speed * dt
            if world:
                world.move(self.position, delta, self.radius)
            else:
                self.position += delta
        self.position.x = max(35, min(1165, self.position.x))
        self.position.y = max(100, min(685, self.position.y))
        self.cooldown = max(0, self.cooldown - dt)


class Enemy:
    def __init__(self, position, difficulty):
        self.position = Vec(position)
        self.max_health = 48 + difficulty * 14
        self.health = self.max_health
        self.speed = 72 + difficulty * 10
        self.radius = 13
        self.damage = 12 + difficulty * 3
        self.cooldown = .65
        self.interval = max(.65, 1.3 - difficulty * .12)
        self.guardian_locked = False
        self.aim = Vec(0, 1)
        self.path = None

    def update(self, dt, player, guardian, world, bullets):
        """Avanza al guardián; al entrar en alcance queda fijado a él."""
        self.cooldown = max(0, self.cooldown - dt)
        if (self.position.distance_to(guardian) <= 115
                and world.visible(self.position, guardian)):
            self.guardian_locked = True
        if self.guardian_locked:
            self.shoot(guardian, bullets)
            return
        if self.path is None:
            self.path = world.path_to_guardian(self.position)
        if world.visible(self.position, guardian, self.radius + 2):
            waypoint = guardian
        else:
            while self.path and self.position.distance_to(self.path[0]) < 4:
                self.path.pop(0)
            waypoint = self.path[0] if self.path else guardian
        delta = waypoint - self.position
        if delta.length_squared():
            self.aim = delta.normalize()
            world.move(self.position, self.aim * min(self.speed * dt, delta.length()), self.radius)
        # El jugador es un blanco de oportunidad: nunca cambia la ruta principal.
        if (self.position.distance_to(player.position) <= 330
                and world.visible(self.position, player.position)):
            self.shoot(player.position, bullets)

    def shoot(self, target, bullets):
        direction = target - self.position
        if direction.length_squared():
            self.aim = direction.normalize()
            if self.cooldown == 0:
                # Nace en el centro para comprobar también paredes junto al cañón.
                bullets.append(Bullet(self.position.copy(), self.aim * 320,
                                      self.damage, ttl=3, hostile=True))
                self.cooldown = self.interval
