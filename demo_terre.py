"""Démo Terre — Globe terrestre 3D texturé, manipulable avec les deux mains.

Contrôles :
  Position          → point milieu entre les deux paumes
  Taille            → distance entre les mains
  Rotation yaw      → déplacer les mains vers la gauche / droite
  Rotation pitch    → déplacer les mains vers le haut / bas (rotation vers l'avant)
"""
import math
import cv2
import numpy as np

IMAGE_PATH = "2k_earth_daymap.jpg"

# ── Physique ───────────────────────────────────────────────────────────────
_POS_K = 0.14;  _POS_D = 0.82
_ROT_K = 0.010;  _ROT_D = 0.85   # inertie de rotation (yaw + pitch)
_FADE  = 0.07

# ── Lumière (direction normalisée, soleil en haut à gauche devant) ────────
_LX, _LY, _LZ = -0.35, -0.50, 0.79
_NL = math.sqrt(_LX**2 + _LY**2 + _LZ**2)
_LX /= _NL;  _LY /= _NL;  _LZ /= _NL


# ── API publique ───────────────────────────────────────────────────────────

def new_terre():
    """Charge la texture et initialise l'état du globe."""
    tex = cv2.imread(IMAGE_PATH)
    if tex is None:
        return None
    return {
        "texture": tex,
        "cx": 0.0,  "cy": 0.0,
        "vx": 0.0,  "vy": 0.0,
        "pitch":  0.0,
        "vpitch": 0.0,
        "yaw":    0.0,
        "vyaw":   0.0,
        "pitch":  0.0,
        "vpitch": 0.0,
        "scale":  130.0,   # rayon en px
        "alpha":  0.0,
        "prev_tcx": None,  # position précédente du midpoint (pour deltas)
        "prev_tcy": None,
    }


def update(terre, hands_by_side, w, h):
    """Met à jour position, inclinaison, taille et fondu."""
    if terre is None:
        return

    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        lx, ly = _palm(left,  w, h)
        rx, ry = _palm(right, w, h)
        tcx  = (lx + rx) * 0.5
        tcy  = (ly + ry) * 0.5
        dist = math.hypot(lx - rx, ly - ry)

        if terre["alpha"] == 0.0:
            terre["cx"], terre["cy"] = tcx, tcy
            terre["prev_tcx"] = tcx
            terre["prev_tcy"] = tcy

        terre["vx"] = terre["vx"] * _POS_D + (tcx - terre["cx"]) * _POS_K
        terre["vy"] = terre["vy"] * _POS_D + (tcy - terre["cy"]) * _POS_K

        # Yaw   : mouvement horizontal → rotation gauche/droite
        # Pitch : mouvement vertical   → rotation vers l'avant/arrière
        if terre["prev_tcx"] is not None:
            dx_mid = tcx - terre["prev_tcx"]
            dy_mid = tcy - terre["prev_tcy"]
            terre["vyaw"]   = terre["vyaw"]   * _ROT_D + dx_mid * _ROT_K
            # dy > 0 = mains descendent → sommet s'éloigne (pitch négatif)
            terre["vpitch"] = terre["vpitch"] * _ROT_D - dy_mid * _ROT_K
        terre["prev_tcx"] = tcx
        terre["prev_tcy"] = tcy

        terre["scale"] = max(60.0, min(250.0, dist * 0.45))
        terre["alpha"] = min(1.0, terre["alpha"] + _FADE)
    else:
        terre["vx"]     *= _POS_D
        terre["vy"]     *= _POS_D
        terre["vyaw"]   *= _ROT_D
        terre["vpitch"] *= _ROT_D
        terre["alpha"]   = max(0.0, terre["alpha"] - _FADE)
        terre["prev_tcx"] = None
        terre["prev_tcy"] = None

    terre["cx"]    += terre["vx"]
    terre["cy"]    += terre["vy"]
    terre["yaw"]   += terre["vyaw"]
    terre["pitch"] += terre["vpitch"]


def render(frame, terre, w, h):
    """Dessine le globe texturé avec éclairage et atmosphère."""
    if terre is None:
        cv2.putText(frame, f"Image '{IMAGE_PATH}' introuvable",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 60, 255), 2)
        return

    alpha = terre["alpha"]
    if alpha <= 0.01:
        return

    cx = int(terre["cx"])
    cy = int(terre["cy"])
    r  = int(terre["scale"])

    R  = _rot(terre["pitch"], terre["yaw"])
    Rt = R.T   # rotation inverse : surface → coords texture

    tex    = terre["texture"]
    th, tw = tex.shape[:2]

    # ── Bounding box clampée au cadre ─────────────────────────────────────
    bx0 = max(0, cx - r - 1);  bx1 = min(w, cx + r + 2)
    by0 = max(0, cy - r - 1);  by1 = min(h, cy + r + 2)
    if bx1 <= bx0 or by1 <= by0:
        return

    # ── Grille de pixels normalisés ───────────────────────────────────────
    gx, gy = np.meshgrid(np.arange(bx0, bx1, dtype=np.float32),
                         np.arange(by0, by1, dtype=np.float32))
    dx = (gx - cx) / r
    dy = (gy - cy) / r
    d2 = dx * dx + dy * dy
    mask = d2 <= 1.0
    if not np.any(mask):
        return

    dz = np.sqrt(np.maximum(0.0, 1.0 - d2))

    # ── Rotation inverse → direction monde ────────────────────────────────
    nx = Rt[0, 0]*dx + Rt[0, 1]*dy + Rt[0, 2]*dz
    ny = Rt[1, 0]*dx + Rt[1, 1]*dy + Rt[1, 2]*dz
    nz = Rt[2, 0]*dx + Rt[2, 1]*dy + Rt[2, 2]*dz

    # ── Coords sphériques → coords texture ────────────────────────────────
    lon = np.arctan2(nx, nz)                          # [−π, π]
    lat = np.arcsin(np.clip(ny, -1.0, 1.0))           # [−π/2, π/2]
    mx  = np.clip(((lon / (2*math.pi) + 0.5) * tw).astype(np.int32), 0, tw - 1)
    my  = np.clip(((0.5 - lat / math.pi)      * th).astype(np.int32), 0, th - 1)

    # ── Échantillonnage texture ────────────────────────────────────────────
    colors = tex[my[mask], mx[mask]]   # (N, 3) BGR

    # ── Éclairage Lambertien (face éclairée / côté nuit) ──────────────────
    shade = np.clip(
        dx[mask] * _LX + dy[mask] * _LY + dz[mask] * _LZ,
        0.04, 1.0,
    )[:, np.newaxis]

    lit = (colors.astype(np.float32) * shade * alpha).clip(0, 255).astype(np.uint8)

    # ── Placement des pixels sur la frame ─────────────────────────────────
    frame[gy[mask].astype(np.int32), gx[mask].astype(np.int32)] = lit

    # ── Atmosphère (halo bleuté gaussien) ─────────────────────────────────
    atmo = np.zeros_like(frame, dtype=np.uint8)
    ar   = r + max(6, r // 6)
    at   = max(5, r // 9)
    cv2.circle(atmo, (cx, cy), ar, (255, 160, 80), at)
    frame[:] = cv2.addWeighted(frame, 1.0,
                                cv2.GaussianBlur(atmo, (35, 35), 0),
                                alpha * 0.90, 0)

    # ── Surbrillance spéculaire ────────────────────────────────────────────
    hl_x = cx - r // 3;  hl_y = cy - r // 3
    spec = np.zeros_like(frame, dtype=np.uint8)
    cv2.ellipse(spec, (hl_x, hl_y),
                (max(3, r // 5), max(2, r // 8)), -30, 0, 360,
                (255, 255, 255), -1)
    frame[:] = cv2.addWeighted(frame, 1.0,
                                cv2.GaussianBlur(spec, (17, 17), 0),
                                alpha * 0.38, 0)


# ── Utilitaires ───────────────────────────────────────────────────────────

def _palm(lm, w, h):
    return int(lm[9].x * w), int(lm[9].y * h)


def _rot(pitch, yaw):
    """Matrice de rotation Ry(yaw) @ Rx(pitch)."""
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw),   math.sin(yaw)
    Rx = np.array([[1,  0,   0 ],
                   [0,  cp, -sp],
                   [0,  sp,  cp]], dtype=np.float32)
    Ry = np.array([[ cy, 0, sy],
                   [  0, 1,  0],
                   [-sy, 0, cy]], dtype=np.float32)
    return Ry @ Rx
