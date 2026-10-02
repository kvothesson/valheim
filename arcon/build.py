"""Arma la pagina del inventario a partir de la carpeta de un mundo de Valheim.

Uso: python arcon/build.py <carpeta_del_mundo> <salida.html>
"""
import collections
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from zdo import parse_items, stable_hash, world_objects

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HASHES = {int(k): v for k, v in json.load(open(os.path.join(ROOT, "data", "hashes.json"))).items()}
NAMES = json.load(open(os.path.join(ROOT, "data", "names.json"), encoding="utf-8"))

KIND = {"piece_chest_wood": "Cofre", "piece_chest": "Cofre reforzado", "piece_chest_private": "Cofre personal",
        "piece_chest_blackmetal": "Cofre de metal negro", "Cart": "Carro", "Karve": "Karve",
        "VikingShip": "Drakkar", "Player_tombstone": "Tumba"}
STATIONS = {"fermenter": "Fermentador", "smelter": "Fundición", "charcoal_kiln": "Horno de carbón",
            "blastfurnace": "Alto horno", "piece_spinningwheel": "Rueca", "windmill": "Molino",
            "eitrrefinery": "Refinería de eitr"}
ITEMS, CONTENT, QUEUED, FUEL = (stable_hash(k) for k in ("items", "Content", "queued", "fuel"))
STATION_HASH = {stable_hash(k): v for k, v in STATIONS.items()}
# La base principal: lo que esta a menos de BASE_RADIUS metros cuenta como "base".
BASE = (float(os.environ.get("BASE_X", 1290)), float(os.environ.get("BASE_Z", -195)))
BASE_RADIUS = float(os.environ.get("BASE_RADIUS", 150))
ART = timezone(timedelta(hours=-3))


def name_es(prefab):
    return NAMES.get(prefab, {}).get("es", prefab)


def build(world_dir):
    containers, stations, used = [], [], set()
    for z in world_objects(world_dir):
        pf = HASHES.get(z["prefab"])
        x, _, zz = z["pos"] or (0, 0, 0)
        if pf in KIND and ITEMS in z.get("bytes", {}):
            items = [[HASHES.get(h, hex(h)), s, q] for h, s, q in parse_items(z["bytes"][ITEMS])]
            if not items:
                continue
            used.update(p for p, _, _ in items)
            containers.append({"kind": KIND[pf], "x": round(x), "z": round(zz),
                               "base": (x - BASE[0]) ** 2 + (zz - BASE[1]) ** 2 < BASE_RADIUS ** 2,
                               "items": items})
        elif z["prefab"] in STATION_HASH:
            kind = STATION_HASH[z["prefab"]]
            ints, strs = z.get("ints", {}), z.get("strs", {})
            if kind == "Fermentador":
                c = ints.get(CONTENT)
                detail = f"Fermentando {name_es(HASHES[c])}" if c in HASHES else "Vacío"
            else:
                parts = []
                queued = ints.get(QUEUED, 0)
                if queued:
                    ores = collections.Counter(v for v in strs.values() if v)
                    what = ", ".join(f"{name_es(k)} ×{v}" for k, v in ores.items())
                    parts.append(f"{queued} en cola" + (f" ({what})" if what else ""))
                fuel = z.get("floats", {}).get(FUEL)
                if fuel:
                    parts.append(f"carbón cargado: {fuel:.0f}")
                detail = "; ".join(parts) or "Vacío"
            stations.append({"kind": kind, "x": round(x), "z": round(zz), "detail": detail})

    ok = sorted(glob.glob(os.path.join(world_dir, "_main.*.ok")), key=os.path.getmtime)
    saved = datetime.fromtimestamp(os.path.getmtime(ok[-1]) if ok else 0, ART)
    return {"saved": saved.isoformat(timespec="minutes"),
            "built": datetime.now(ART).isoformat(timespec="minutes"),
            "containers": containers, "stations": stations,
            "names": {p: NAMES.get(p, {"es": p, "cat": "Otros"}) for p in sorted(used)}}


def main(world_dir, out_path):
    if not glob.glob(os.path.join(world_dir, "*.chunk")):
        sys.exit(f"No hay archivos .chunk en {world_dir}: no publico una pagina vacia.")
    data = build(world_dir)
    template = open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(template.replace("__DATA__", payload))
    print(f"{len(data['containers'])} contenedores, {len(data['stations'])} estaciones, "
          f"{len(data['names'])} items distintos; guardado {data['saved']} -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
