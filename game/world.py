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


def rect_hit_time(start, delta, rect):
    """Primer contacto del segmento con el rectángulo, en coordenadas continuas."""
    entry, exit = 0.0, 1.0
    for origin, step, lower, upper in (
        (start.x, delta.x, rect.left, rect.right),
        (start.y, delta.y, rect.top, rect.bottom),
    ):
        if step == 0:
            if not lower <= origin <= upper:
                return None
            continue
        near = (lower - origin) / step
        far = (upper - origin) / step
        if near > far:
            near, far = far, near
        entry = max(entry, near)
        exit = min(exit, far)
        if entry > exit:
            return None
    return entry


class Arena:
    def __init__(self, guardian):
        self.bounds = pygame.Rect(12, 99, 1176, 587)
        self.walls = [self.art_rect(rect) for rect in (
            (15,30,20,851), (1634,30,20,851),
            (35,28,259,35), (374,28,132,35), (506,8,657,48),
            (1164,28,135,35), (1373,28,260,35),
            (541,56,590,134),
            (35,210,314,19), (328,228,22,116), (328,444,22,119),
            (35,565,365,20), (380,585,22,63), (380,706,22,143),
            (1324,211,309,22), (1324,233,24,123), (1324,434,24,99),
            (1324,532,309,22), (1274,566,72,22), (1274,588,23,60),
            (1274,706,23,143),
            (522,225,26,121), (548,295,94,51),
            (1124,225,25,121), (1030,295,94,51),
            (531,564,26,114), (557,628,108,50),
            (1114,564,26,114), (1007,628,107,50),
            (493,419,75,66), (1100,420,104,75),
            (36,321,238,90), (241,269,42,80),
            (48,660,179,41), (48,701,43,120), (88,792,104,30),
            (1370,577,176,104), (1528,747,103,92),
            (35,849,454,30), (1181,849,453,30),
            (487,751,19,133), (1165,751,19,133),
            (505,736,268,48), (902,736,263,48),
            (505,884,272,40), (895,884,270,40),
        )]
        self.guardian = Vec(guardian)
        # Los puntos libres del escenario son los nodos del grafo de movimiento.
        self.cells = {}
        for x in range(48):
            for y in range(24):
                point = Vec(12 + x * 25, 100 + y * 25)
                if self.is_free(point, 16):
                    self.cells[(x, y)] = point
        # Recorremos la cuadrícula desde el guardián una vez al cargar la arena.
        goal = self.nearest_cell(self.guardian)
        self.parents, self.distance = {goal: None}, {goal: 0}
        pending = deque([goal])
        while pending:
            current = pending.popleft()
            x, y = current
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (neighbor in self.cells and neighbor not in self.parents
                        and self.visible(self.cells[current], self.cells[neighbor], 15)):
                    # Desde este vecino se vuelve hacia el guardián por la celda actual.
                    self.parents[neighbor] = current
                    self.distance[neighbor] = self.distance[current] + 1
                    pending.append(neighbor)
        self.spawn_points = [self.art_point(point) for point in
                             ((330, 60), (1340, 60), (436, 823), (1223, 823), (835, 911))]

    @staticmethod
    def art_point(point):
        x, y = point
        return Vec(x * 1200 / 1672, 80 + y * 608 / 941)

    @classmethod
    def art_rect(cls, rect):
        x, y, w, h = rect
        start = cls.art_point((x, y))
        end = cls.art_point((x+w, y+h))
        return pygame.Rect(round(start.x), round(start.y),
                           round(end.x-start.x), round(end.y-start.y))

    def is_free(self, point, radius):
        return (self.bounds.left + radius <= point.x <= self.bounds.right - radius
                and self.bounds.top + radius <= point.y <= self.bounds.bottom - radius
                and not any(w.inflate(radius * 2, radius * 2).collidepoint(point) for w in self.walls))

    def nearest_cell(self, position):
        return min(self.cells, key=lambda key: self.cells[key].distance_squared_to(position))

    def path_to_guardian(self, position):
        reachable = [key for key in self.parents
                     if self.visible(position, self.cells[key], 13)]
        if not reachable:
            return []
        cell = min(reachable, key=lambda key: self.cells[key].distance_squared_to(position))
        path = [self.cells[cell].copy()]
        # El minion sigue los padres desde su punto de entrada hasta el guardián.
        while self.parents[cell] is not None:
            cell = self.parents[cell]
            path.append(self.cells[cell].copy())
        path.append(self.guardian.copy())
        return path

    def wall_hit_time(self, start, end, radius=0):
        delta = end - start
        result = None
        for wall in self.walls:
            hit = rect_hit_time(start, delta, wall.inflate(radius * 2, radius * 2))
            if hit == 0:
                return 0.0
            if hit is not None and (result is None or hit < result):
                result = hit
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
