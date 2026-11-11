"""Paredes, colisiones y rutas BFS hacia el guardián."""
from collections import deque
import math
import pygame

Vec = pygame.Vector2


def circle_hit_time(start, end, center, radius):
    """Primer impacto del segmento contra un círculo, entre 0 y 1."""
    delta, offset = end - start, start - center
    c = offset.length_squared() - radius * radius
    if c <= 0:
        return 0.0
    a = delta.length_squared()
    if a == 0:
        return None
    b = 2 * offset.dot(delta)
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None
    t = (-b - math.sqrt(discriminant)) / (2 * a)
    return t if 0 <= t <= 1 else None


class Arena:
    def __init__(self, guardian):
        self.bounds = pygame.Rect(20, 100, 1160, 580)
        self.walls = [pygame.Rect(*rect) for rect in (
            (260, 100, 24, 180), (260, 360, 24, 200),
            (900, 100, 24, 180), (900, 360, 24, 200),
            (360, 230, 160, 24), (680, 230, 160, 24),
            (400, 460, 160, 24), (680, 460, 160, 24),
            (120, 580, 200, 24), (880, 580, 200, 24),
        )]
        self.guardian = Vec(guardian)
        self.cells = {}
        for x in range(29):
            for y in range(14):
                point = Vec(40 + x * 40, 120 + y * 40)
                if self.is_free(point, 16):
                    self.cells[(x, y)] = point
        goal = self.nearest_cell(self.guardian)
        self.parents, self.distance = {goal: None}, {goal: 0}
        pending = deque([goal])
        while pending:
            current = pending.popleft()
            x, y = current
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in self.cells and neighbor not in self.parents:
                    self.parents[neighbor] = current
                    self.distance[neighbor] = self.distance[current] + 1
                    pending.append(neighbor)
        self.spawn_points = [Vec(p) for p in ((80, 160), (1120, 160), (80, 520),
                                              (1120, 520), (600, 120), (600, 640))]

    def is_free(self, point, radius):
        return (self.bounds.left + radius <= point.x <= self.bounds.right - radius
                and self.bounds.top + radius <= point.y <= self.bounds.bottom - radius
                and not any(w.inflate(radius * 2, radius * 2).collidepoint(point) for w in self.walls))

    def nearest_cell(self, position):
        return min(self.cells, key=lambda key: self.cells[key].distance_squared_to(position))

    def path_to_guardian(self, position):
        cell = self.nearest_cell(position)
        if cell not in self.parents:
            return []
        path = [self.cells[cell].copy()]
        while self.parents[cell] is not None:
            cell = self.parents[cell]
            path.append(self.cells[cell].copy())
        path.append(self.guardian.copy())
        return path

    def wall_hit_time(self, start, end, radius=0):
        length = (end - start).length()
        result = None
        for wall in self.walls:
            expanded = wall.inflate(radius * 2, radius * 2)
            if expanded.collidepoint(start):
                return 0.0
            clipped = expanded.clipline(start, end)
            if clipped:
                t = Vec(clipped[0]).distance_to(start) / length if length else 0
                result = t if result is None else min(result, t)
        return result

    def visible(self, start, end, radius=0):
        return self.wall_hit_time(start, end, radius) is None

    def move(self, position, delta, radius):
        """Movimiento por ejes con deslizamiento y pasos cortos antitúnel."""
        steps = max(1, math.ceil(delta.length() / 6))
        step = delta / steps
        for _ in range(steps):
            for axis in ("x", "y"):
                old = getattr(position, axis)
                setattr(position, axis, old + getattr(step, axis))
                if not self.is_free(position, radius):
                    setattr(position, axis, old)
        return position
