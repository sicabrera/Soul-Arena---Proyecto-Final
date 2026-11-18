"""Sprites direccionales, interfaz y efectos."""
from dataclasses import dataclass
from pathlib import Path
import pygame

ASSETS = Path(__file__).resolve().parents[1] / "assets"
Vec = pygame.Vector2

PLAYER_MUZZLE = [(0, -25), (12, -21), (14, -11), (12, -1), (0, 3), (-12, -2), (-15, -12), (-13, -19)]
MINION_MUZZLE = [(0, -26), (14, -20), (16, -9), (12, 5), (0, 4), (-16, 4), (-17, -10), (-11, -19)]

# Sentido horario desde el norte. El margen evita el parpadeo entre dos poses.
def facing_for(aim, previous):
    angle = Vec(0, -1).angle_to(aim) % 360
    difference = (angle - previous * 45 + 180) % 360 - 180
    if abs(difference) <= 26:
        return previous
    return int((angle + 22.5) // 45) % 8


@dataclass
class Effect:
    frames: tuple
    position: Vec
    frame_time: float
    angle: float = 0
    age: float = 0

    @property
    def finished(self):
        return self.age >= len(self.frames) * self.frame_time


CHARACTER_SCALE = 1.25


def scale_character(image):
    size = (round(image.width * CHARACTER_SCALE), round(image.height * CHARACTER_SCALE))
    return pygame.transform.scale(image, size)


class CharacterArt:
    def __init__(self, atlas, muzzle, hit_color=(255, 145, 163, 255)):
        self.frames = tuple(
            tuple(scale_character(atlas.subsurface((facing * 64, row * 64, 64, 64)))
                  for facing in range(8))
            for row in range(4)
        )
        self.hurt = tuple(tuple(self.hit_tint(frame, hit_color) for frame in row)
                          for row in self.frames)
        self.muzzle = tuple(Vec(point) * CHARACTER_SCALE for point in muzzle)

    @staticmethod
    def hit_tint(frame, color):
        tinted = frame.copy()
        tinted.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
        return tinted

    def draw(self, screen, position, facing, distance, idle_time, moving, hurt, shot):
        if moving:
            row = (1, 0, 2, 0)[int(distance / 8) % 4]
        else:
            row = 3 if int(idle_time * 4) % 4 in (1, 2) else 0
        image = (self.hurt if hurt else self.frames)[row][facing]
        recoil = Vec(0, -2).rotate(facing * 45) * -1 if shot else Vec()
        screen.blit(image, image.get_rect(center=position + recoil))


class Art:
    def __init__(self):
        self.arena = self.image("nightclub").convert()
        self.player = CharacterArt(self.image("player-directions"), PLAYER_MUZZLE)
        self.minion = CharacterArt(self.image("minion-directions"), MINION_MUZZLE)
        self.healing_minion = CharacterArt(self.image("minion-green-directions"), MINION_MUZZLE,
                                           hit_color=(150, 255, 174, 255))
        self.player_fallen = scale_character(self.image("player-fallen"))
        self.effects = self.strip("effects") + (
            scale_character(self.image("minion-fallen")),
            scale_character(self.image("minion-green-fallen")),
        )
        self.ui = [[self.image(f"ui_{row}_{i}") for i in range(count)]
                   for row, count in enumerate((4, 6, 4, 4))]
        self.font = pygame.font.Font(ASSETS / "VT323-Regular.ttf", 25)
        self.small = pygame.font.Font(ASSETS / "VT323-Regular.ttf", 20)
        self.title = pygame.font.Font(ASSETS / "VT323-Regular.ttf", 62)
        self.scaled = {}

    @staticmethod
    def image(name):
        return pygame.image.load(ASSETS / (name + ".png")).convert_alpha()

    def strip(self, name):
        image = self.image(name)
        return tuple(image.subsurface((x, 0, 64, 64)) for x in range(0, image.width, 64))

    def ui_image(self, screen, row, column, rect):
        rect = pygame.Rect(rect)
        key = (row, column, rect.size)
        if key not in self.scaled:
            self.scaled[key] = pygame.transform.scale(self.ui[row][column], rect.size)
        screen.blit(self.scaled[key], rect)

    @staticmethod
    def sprite(screen, image, position, angle=0):
        if angle:
            image = pygame.transform.rotate(image, angle)
        screen.blit(image, image.get_rect(center=position))

    def muzzle_offset(self, facing, hostile):
        character = self.minion if hostile else self.player
        return character.muzzle[facing]

    def player_sprite(self, screen, position, facing, distance, idle_time, moving, hurt, shot):
        self.player.draw(screen, position, facing, distance, idle_time, moving, hurt, shot)

    def enemy_sprite(self, screen, enemy):
        character = self.healing_minion if enemy.healing else self.minion
        character.draw(screen, enemy.position, enemy.facing, enemy.walk_distance,
                       0, enemy.moving, enemy.hurt, enemy.shot)

    def draw_effect(self, screen, effect):
        frame = min(int(effect.age / effect.frame_time), len(effect.frames) - 1)
        self.sprite(screen, self.effects[effect.frames[frame]], effect.position, effect.angle)
