"""Démo Flame — Flammes jaillissant des bouts de doigts quand la main est ouverte."""
import random
import cv2
import numpy as np

_MAX_PARTICLES = 500
_EMIT_PER_TIP  = 3
_TIPS = [4, 8, 12, 16, 20]   # pouce, index, majeur, annulaire, auriculaire


def new_flame():
    return {"particles": []}


def update(flame, hands_by_side, w, h):
    pts = flame["particles"]

    # Mise à jour physique des particules
    alive = []
    for p in pts:
        p["life"] -= 0.028
        p["x"]   += p["vx"]
        p["y"]   += p["vy"]
        p["vy"]  -= 0.20                          # poussée vers le haut
        p["vx"]  += random.uniform(-0.15, 0.15)   # turbulence latérale
        p["size"] *= 0.976
        if p["life"] > 0 and -40 < p["y"] < h + 20:
            alive.append(p)
    flame["particles"] = alive

    # Émission depuis les mains ouvertes
    for lm in hands_by_side.values():
        if not _is_open(lm):
            continue
        for tip in _TIPS:
            for _ in range(_EMIT_PER_TIP):
                if len(flame["particles"]) >= _MAX_PARTICLES:
                    return
                tx = lm[tip].x * w
                ty = lm[tip].y * h
                flame["particles"].append({
                    "x":    tx + random.uniform(-5, 5),
                    "y":    ty + random.uniform(-2, 3),
                    "vx":   random.uniform(-1.4, 1.4),
                    "vy":   random.uniform(-6.0, -2.5),
                    "life": random.uniform(0.75, 1.0),
                    "size": random.uniform(5.0, 13.0),
                })


def render(frame, flame, w, h):
    if not flame["particles"]:
        return

    ov = np.zeros(frame.shape, dtype=np.float32)

    for p in flame["particles"]:
        x, y = int(p["x"]), int(p["y"])
        if not (0 <= x < w and 0 <= y < h):
            continue
        life = max(0.0, p["life"])
        size = max(1, int(p["size"]))
        color = _flame_color(life)
        cv2.circle(ov, (x, y), size, color, -1)

    # Halo lumineux par flou additif
    glow = cv2.GaussianBlur(ov, (15, 15), 0)
    np.add(ov, glow * 0.6, out=ov)
    np.clip(ov, 0, 255, out=ov)

    # Fusion additive sur la frame
    frame[:] = np.clip(frame.astype(np.float32) + ov, 0, 255).astype(np.uint8)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _flame_color(life):
    """BGR : blanc → jaune → orange → rouge, estompé vers 0."""
    alpha = min(1.0, life * 1.6)
    if life > 0.65:
        t = (life - 0.65) / 0.35   # 0→1 quand life va de 0.65 à 1.0
        b = int(255 * t * alpha)
        g = int(255 * alpha)
        r = int(255 * alpha)
    elif life > 0.35:
        t = (life - 0.35) / 0.30   # 0→1 quand life va de 0.35 à 0.65
        b = 0
        g = int((80 + 175 * t) * alpha)
        r = int(255 * alpha)
    else:
        t = life / 0.35             # 0→1 quand life va de 0 à 0.35
        b = 0
        g = int(80 * t * alpha)
        r = int(255 * alpha)
    return b, g, r


def _is_open(lm):
    """Quatre doigts étendus."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y < lm[10].y and
            lm[16].y < lm[14].y and
            lm[20].y < lm[18].y)
