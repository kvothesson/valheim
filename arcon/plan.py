"""Plano de la base visto desde arriba, armado con las piezas construidas.

Cada pieza se dibuja como un rectangulo con su posicion y su giro horizontal.
Los tamanos son los del juego (metros); los techos no se dibujan porque desde
arriba tapan todo lo de adentro. Norte arriba: x crece hacia la derecha y z
hacia arriba, asi que en SVG y = -z.
"""
import math

# prefab: (capa, largo, ancho). Las paredes se dibujan con un ancho fijo.
WALL_W = 0.35
SHAPES = {
    "wood_floor": ("floor_wood", 2, 2), "wood_floor_1x1": ("floor_wood", 1, 1),
    "stone_floor_2x2": ("floor_stone", 2, 2), "stone_floor": ("floor_stone", 4, 4),
    "blackmarble_floor": ("floor_stone", 2, 2), "blackmarble_floor_large": ("floor_stone", 4, 4),
    "wood_stair": ("floor_wood", 2, 2), "stone_stair": ("floor_stone", 2, 2),
    "woodwall": ("wall_wood", 2, WALL_W), "wood_wall_half": ("wall_wood", 2, WALL_W),
    "wood_wall_quarter": ("wall_wood", 2, WALL_W), "wood_wall_roof_45": ("wall_wood", 2, WALL_W),
    "wood_wall_roof": ("wall_wood", 2, WALL_W), "wood_gate": ("wall_wood", 2, WALL_W),
    "wood_door": ("wall_wood", 1.2, WALL_W), "wood_fence": ("wall_wood", 2, WALL_W),
    "darkwood_wall": ("wall_wood", 2, WALL_W),
    "stone_wall_1x1": ("wall_stone", 1, 0.5), "stone_wall_2x1": ("wall_stone", 2, 0.5),
    "stone_wall_4x2": ("wall_stone", 4, 0.5), "stone_fence": ("wall_stone", 2, 0.5),
    "stake_wall": ("stake", 2, 0.5),
}
STATION_PREFABS = {"forge", "piece_workbench", "smelter", "charcoal_kiln", "fermenter", "piece_cauldron",
                   "portal_wood", "bed", "piece_bed02", "piece_beehive", "piece_stonecutter", "piece_artisanstation",
                   "piece_spinningwheel", "windmill", "blastfurnace", "eitrrefinery", "fire_pit", "hearth"}


def _rect(x, z, yaw, length, width):
    t = math.radians(yaw or 0)
    ux, uz = math.cos(t), -math.sin(t)   # eje largo de la pieza
    vx, vz = math.sin(t), math.cos(t)
    hl, hw = length / 2, width / 2
    return [(x + a * hl * ux + b * hw * vx, z + a * hl * uz + b * hw * vz)
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


class Plan:
    def __init__(self, cx, cz, radius):
        self.cx, self.cz, self.r2 = cx, cz, radius ** 2
        self.layers = {k: [] for k in ("floor_wood", "floor_stone", "wall_wood", "wall_stone", "stake")}
        self.stations = []
        self.pts = []

    def add(self, prefab, pos, yaw):
        if pos is None or yaw is None:
            return
        x, y, z = pos
        if (x - self.cx) ** 2 + (z - self.cz) ** 2 > self.r2:
            return
        if prefab in SHAPES:
            layer, length, width = SHAPES[prefab]
            poly = _rect(x, z, yaw, length, width)
            self.layers[layer].append((y, poly))
            self.pts.extend(poly)
        elif prefab in STATION_PREFABS:
            self.stations.append([round(x, 1), round(-z, 1)])

    def to_json(self):
        if not self.pts:
            return None
        xs = [p[0] for p in self.pts]; zs = [p[1] for p in self.pts]
        layers = {}
        for name, polys in self.layers.items():
            polys.sort(key=lambda t: t[0])   # lo mas alto se dibuja ultimo
            layers[name] = "".join(
                "M" + "L".join(f"{px:.1f} {-pz:.1f}" for px, pz in poly) + "Z" for _, poly in polys)
        return {"box": [round(min(xs) - 4, 1), round(-max(zs) - 4, 1),
                        round(max(xs) - min(xs) + 8, 1), round(max(zs) - min(zs) + 8, 1)],
                "layers": layers, "stations": self.stations}
