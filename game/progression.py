"""Estructuras manuales, independientes de Pygame y de la interfaz."""
from collections import deque
from dataclasses import dataclass


@dataclass
class SkillNode:
    key: str
    name: str
    cost: int
    description: str
    parent: object = None
    left: object = None
    right: object = None
    unlocked: bool = False
    min_level: int = 1


class SkillTree:
    def __init__(self):
        self.root = SkillNode("basic", "Disparo básico", 0, "Tu arma inicial", unlocked=True)
        damage = self.insert(self.root, "left", "damage", "Daño I", 20, "+8 de daño")
        speed = self.insert(self.root, "right", "speed", "Cadencia I", 20, "Dispara más rápido")
        self.insert(damage, "left", "damage2", "Daño II", 35, "+12 de daño", min_level=2)
        health = self.insert(damage, "right", "health", "Vitalidad", 30, "+40 de vida máxima", min_level=2)
        cadence = self.insert(speed, "left", "speed2", "Cadencia II", 35, "Aún más disparos", min_level=2)
        self.insert(speed, "right", "move", "Agilidad", 30, "+25% de movimiento", min_level=2)
        self.insert(health, "left", "armor", "Blindaje", 40, "Recibís 20% menos daño", min_level=3)
        self.insert(cadence, "right", "velocity", "Proyectiles", 40, "+25% velocidad de bala", min_level=3)

    def insert(self, parent, side, key, name, cost, description, *, min_level=1):
        if side not in ("left", "right") or getattr(parent, side) is not None:
            raise ValueError("Hijo inválido u ocupado")
        node = SkillNode(key, name, cost, description, parent=parent, min_level=min_level)
        setattr(parent, side, node)
        return node

    def preorder(self, node=None):
        node = self.root if node is None else node
        yield node
        if node.left:
            yield from self.preorder(node.left)
        if node.right:
            yield from self.preorder(node.right)

    def buy(self, key, souls, *, level=1):
        node = next((n for n in self.preorder() if n.key == key), None)
        if node is None or node.unlocked:
            return souls, False, "Habilidad ya adquirida o inexistente."
        if level < node.min_level:
            return souls, False, f"Requiere nivel {node.min_level}."
        if node.parent and not node.parent.unlocked:
            return souls, False, "Primero comprá la habilidad anterior."
        if souls < node.cost:
            return souls, False, "No tenés suficientes almas."
        node.unlocked = True
        return souls - node.cost, True, "Adquirida: " + node.name


class ZoneGraph:
    def __init__(self):
        self.names = {"camp": "Campamento", "ruins": "Ruinas", "crypt": "Cripta", "core": "Núcleo"}
        self.adjacency = {key: [] for key in self.names}
        self.add_edge("camp", "ruins", 25)
        self.add_edge("camp", "crypt", 35)
        self.add_edge("ruins", "core", 50)
        self.add_edge("crypt", "core", 40)
        self.unlocked = {"camp"}
        self.completed = set()

    def add_edge(self, source, target, cost):
        if source not in self.adjacency or target not in self.adjacency or cost < 0:
            raise ValueError("Ruta inválida")
        self.adjacency[source].append((target, cost))

    def bfs(self, start):
        pending, visited, order = deque([start]), {start}, []
        while pending:
            current = pending.popleft()
            order.append(current)
            for neighbor, _ in self.adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        return order

    def access(self, source, target, souls):
        if target in self.unlocked:
            return souls, True, "Zona disponible."
        if source not in self.completed:
            return souls, False, "Completá la zona actual para abrir sus rutas."
        cost = next((cost for key, cost in self.adjacency[source] if key == target), None)
        if cost is None:
            return souls, False, "No hay una ruta dirigida desde esta zona."
        if souls < cost:
            return souls, False, "No tenés suficientes almas."
        self.unlocked.add(target)
        return souls - cost, True, "Zona desbloqueada."
