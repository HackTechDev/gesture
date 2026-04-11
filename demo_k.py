"""Démo K — Galaxie spirale 3D tournante entre les mains.

Contrôle :
  Position   → point milieu entre les deux paumes
  Inclinaison → angle de la ligne main-gauche → main-droite
  Taille     → distance entre les mains
  Rotation   → spin automatique (yaw) ; pitch piloté par l'inclinaison des mains
"""
import math
import time
import random
import cv2
import numpy as np

# ── Paramètres de génération ───────────────────────────────────────────────
N_STARS   = 1500
N_ARMS    = 2
N_NEBULAE = 20
R_UNIT    = 1.0        # rayon de référence (unités arbitraires)

# ── Physique ───────────────────────────────────────────────────────────────
_SPIN     = 0.45       # rad/s — vitesse de rotation automatique
_POS_K    = 0.14;  _POS_D    = 0.82
_PITCH_K  = 0.12;  _PITCH_D  = 0.86
_FADE     = 0.07

# ── Couleurs étoiles (BGR) ────────────────────────────────────────────────
_C_HOT   = (255, 238, 215)   # OB — bleues-blanches
_C_WARM  = (215, 200, 165)   # jaune-blanc
_C_DISK  = (165, 158, 128)   # disque diffus
_C_BULGE = (155, 192, 255)   # bulbe (jaunâtre)
_C_GIANT = ( 70, 125, 255)   # géantes oranges-rouges

# ── Couleurs nébuleuses (BGR) ─────────────────────────────────────────────
_NEBULA_PALETTE = [
    (255, 100,  80),   # bleue
    (200,  65, 255),   # rose
    (255,  75, 168),   # violette
    ( 55, 175, 255),   # orange-jaune (région HII)
    (255, 200,  70),   # cyan
    ( 90, 255, 120),   # verte
]


# ── Génération (effectuée une seule fois à l'activation) ──────────────────

def _generate_stars():
    pos, colors, sizes = [], [], []

    # Bras spiraux (55 %)
    n_arm = int(N_STARS * 0.55)
    for i in range(n_arm):
        arm = i % N_ARMS
        t   = random.random() ** 0.60
        a   = t * 4 * math.pi + arm * math.pi + random.gauss(0, 0.30)
        r   = max(0.05, t * R_UNIT + random.gauss(0, 0.04 * R_UNIT))
        pos.append([r * math.cos(a),
                    random.gauss(0, R_UNIT * 0.018 * (1 - t * 0.5)),
                    r * math.sin(a)])
        colors.append(_C_HOT if t < 0.40 else _C_WARM)
        sizes.append(2 if t < 0.25 else 1)

    # Disque diffus (20 %)
    n_disk = int(N_STARS * 0.20)
    for _ in range(n_disk):
        r = abs(random.gauss(0, R_UNIT * 0.38))
        a = random.uniform(0, 2 * math.pi)
        pos.append([r * math.cos(a),
                    random.gauss(0, R_UNIT * 0.025),
                    r * math.sin(a)])
        colors.append(_C_DISK)
        sizes.append(1)

    # Bulbe central (20 %)
    n_bulge = int(N_STARS * 0.20)
    for _ in range(n_bulge):
        r   = abs(random.gauss(0, R_UNIT * 0.13))
        th  = random.uniform(0, 2 * math.pi)
        phi = math.acos(2 * random.random() - 1)
        pos.append([r * math.sin(phi) * math.cos(th),
                    r * math.cos(phi) * 0.60,
                    r * math.sin(phi) * math.sin(th)])
        colors.append(_C_BULGE)
        sizes.append(2 if r < R_UNIT * 0.05 else 1)

    # Géantes rouges (5 %)
    n_giant = N_STARS - n_arm - n_disk - n_bulge
    for i in range(n_giant):
        arm = i % N_ARMS
        t   = 0.30 + random.random() * 0.60
        a   = t * 4 * math.pi + arm * math.pi + random.gauss(0, 0.40)
        r   = max(0.05, t * R_UNIT + random.gauss(0, 0.05))
        pos.append([r * math.cos(a),
                    random.gauss(0, R_UNIT * 0.020),
                    r * math.sin(a)])
        colors.append(_C_GIANT)
        sizes.append(2)

    return (np.array(pos,    dtype=np.float32),
            np.array(colors, dtype=np.uint8),
            np.array(sizes,  dtype=np.int32))


def _generate_nebulae():
    pos, colors, radii = [], [], []
    per_arm = N_NEBULAE // N_ARMS
    for arm in range(N_ARMS):
        for j in range(per_arm):
            t = 0.12 + j / per_arm * 0.82
            a = t * 4 * math.pi + arm * math.pi + random.gauss(0, 0.20)
            r = max(0.05, t * R_UNIT * 0.90 + random.gauss(0, 0.06))
            pos.append([r * math.cos(a),
                        random.gauss(0, R_UNIT * 0.015),
                        r * math.sin(a)])
            colors.append(random.choice(_NEBULA_PALETTE))
            radii.append(random.uniform(0.08, 0.20) * R_UNIT)
    return (np.array(pos,    dtype=np.float32),
            np.array(colors, dtype=np.uint8),
            np.array(radii,  dtype=np.float32))


# ── API publique ───────────────────────────────────────────────────────────

def new_galaxy():
    sp, sc, ss = _generate_stars()
    np_, nc, nr = _generate_nebulae()
    return {
        "star_pos":    sp,
        "star_colors": sc,
        "star_sizes":  ss,
        "neb_pos":     np_,
        "neb_colors":  nc,
        "neb_radii":   nr,
        "cx": 0.0,  "cy": 0.0,
        "vx": 0.0,  "vy": 0.0,
        "pitch":  0.0,
        "vpitch": 0.0,
        "scale":  160.0,
        "alpha":  0.0,
    }


def update(galaxy, hands_by_side, w, h):
    """Met à jour position, inclinaison, taille et fondu."""
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        lx, ly = _palm(left,  w, h)
        rx, ry = _palm(right, w, h)
        tcx  = (lx + rx) * 0.5
        tcy  = (ly + ry) * 0.5
        dist = math.hypot(lx - rx, ly - ry)

        if galaxy["alpha"] == 0.0:
            galaxy["cx"], galaxy["cy"] = tcx, tcy

        galaxy["vx"] = galaxy["vx"] * _POS_D + (tcx - galaxy["cx"]) * _POS_K
        galaxy["vy"] = galaxy["vy"] * _POS_D + (tcy - galaxy["cy"]) * _POS_K

        # Inclinaison = angle de la ligne gauche→droite par rapport à l'horizontale
        target_pitch = math.atan2(ly - ry, lx - rx) * 0.90
        galaxy["vpitch"] = (galaxy["vpitch"] * _PITCH_D
                            + (target_pitch - galaxy["pitch"]) * _PITCH_K)

        galaxy["scale"] = max(80.0, min(340.0, dist * 0.92))
        galaxy["alpha"] = min(1.0, galaxy["alpha"] + _FADE)
    else:
        galaxy["vx"]     *= _POS_D
        galaxy["vy"]     *= _POS_D
        galaxy["vpitch"] *= _PITCH_D
        galaxy["alpha"]   = max(0.0, galaxy["alpha"] - _FADE)

    galaxy["cx"]    += galaxy["vx"]
    galaxy["cy"]    += galaxy["vy"]
    galaxy["pitch"] += galaxy["vpitch"]


def render(frame, galaxy, w, h):
    """Dessine la galaxie 3D sur la frame."""
    alpha = galaxy["alpha"]
    if alpha <= 0.01:
        return

    cx    = int(galaxy["cx"])
    cy    = int(galaxy["cy"])
    scale = galaxy["scale"]
    R     = _rot(galaxy["pitch"], time.time() * _SPIN)

    rot_s = (R @ galaxy["star_pos"].T).T   # (N_STARS, 3)
    rot_n = (R @ galaxy["neb_pos"].T).T    # (N_NEBULAE, 3)

    # ── 1. Nébuleuses (calque gaussien additif) ───────────────────────────
    neb_layer = np.zeros_like(frame, dtype=np.uint8)
    for i in np.argsort(rot_n[:, 2]):          # arrière → avant
        nx = int(cx + rot_n[i, 0] * scale)
        ny = int(cy + rot_n[i, 1] * scale)
        if not (0 <= nx < w and 0 <= ny < h):
            continue
        nr  = max(5, int(galaxy["neb_radii"][i] * scale))
        df  = max(0.15, min(1.0, 0.55 + rot_n[i, 2] / R_UNIT * 0.50))
        nc  = tuple(int(c * df) for c in galaxy["neb_colors"][i])
        cv2.circle(neb_layer, (nx, ny), nr, nc, -1)
    frame[:] = cv2.addWeighted(
        frame, 1.0,
        cv2.GaussianBlur(neb_layer, (61, 61), 0),
        alpha * 0.50, 0,
    )

    # ── 2. Halo du noyau galactique ───────────────────────────────────────
    core_layer = np.zeros_like(frame, dtype=np.uint8)
    cr = max(6, int(scale * 0.13))
    cv2.circle(core_layer, (cx, cy), cr,      (255, 238, 210), -1)
    cv2.circle(core_layer, (cx, cy), cr * 2,  (180, 165, 130), -1)
    cv2.circle(core_layer, (cx, cy), cr * 4,  ( 80,  70,  50), -1)
    frame[:] = cv2.addWeighted(
        frame, 1.0,
        cv2.GaussianBlur(core_layer, (45, 45), 0),
        alpha * 0.75, 0,
    )

    # ── 3. Étoiles ────────────────────────────────────────────────────────
    sx_all = (cx + rot_s[:, 0] * scale).astype(np.int32)
    sy_all = (cy + rot_s[:, 1] * scale).astype(np.int32)
    dz     = rot_s[:, 2]
    vis    = (sx_all >= 0) & (sx_all < w) & (sy_all >= 0) & (sy_all < h)
    order  = np.argsort(dz)                    # arrière → avant
    sizes  = galaxy["star_sizes"]
    colors = galaxy["star_colors"]

    # Calque glow étoiles
    star_layer = np.zeros_like(frame, dtype=np.uint8)

    # Petites étoiles (taille 1) : batch numpy
    m1 = vis & (sizes == 1)
    idx1 = order[m1[order]]
    if len(idx1):
        df1 = np.clip(0.20 + dz[idx1] / R_UNIT * 0.55, 0.20, 1.0)
        c1  = (colors[idx1].astype(np.float32)
               * df1[:, np.newaxis] * alpha).clip(0, 255).astype(np.uint8)
        star_layer[sy_all[idx1], sx_all[idx1]] = c1
        # Écriture directe sur la frame (back→front = overwrite ok)
        frame[sy_all[idx1], sx_all[idx1]] = np.maximum(
            frame[sy_all[idx1], sx_all[idx1]], c1
        )

    # Grandes étoiles (taille ≥ 2) : cv2.circle
    for i in order:
        if not vis[i] or sizes[i] < 2:
            continue
        df = max(0.20, min(1.0, 0.55 + dz[i] / R_UNIT * 0.55))
        c  = tuple(int(ch * df * alpha) for ch in colors[i])
        sz = sizes[i]
        cv2.circle(star_layer, (sx_all[i], sy_all[i]), sz + 1, c, -1)
        cv2.circle(frame,      (sx_all[i], sy_all[i]), sz,     c, -1)

    frame[:] = cv2.addWeighted(
        frame, 1.0,
        cv2.GaussianBlur(star_layer, (5, 5), 0),
        alpha * 0.50, 0,
    )


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
