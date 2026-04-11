"""Démo H — Bulle d'eau 3D en apesanteur, modelable avec les deux mains.

Maillage déformable : N points de contrôle avec physique ressort-masse
et propagation d'onde. Chaque doigt (5 tips + paume) déforme la surface
indépendamment dans n'importe quelle direction.
"""
import math
import time
import cv2
import numpy as np
from config import BUBBLE_H_MIN_R, BUBBLE_H_MAX_R, FINGERTIPS

# ── Maillage ───────────────────────────────────────────────────────────────
N_SEG   = 48
_ANGLES = np.linspace(0, 2 * math.pi, N_SEG, endpoint=False, dtype=np.float32)
_COS_A  = np.cos(_ANGLES)
_SIN_A  = np.sin(_ANGLES)

# ── Physique des points de surface ────────────────────────────────────────
_SPRING_K   = 0.038   # rappel vers la sphère de repos
_COUPLING   = 0.22    # couplage voisins → propagation d'onde
_DAMPING    = 0.90    # amortissement par frame
_PUSH       = 0.32    # intensité de la poussée des doigts
_SIGMA      = 0.65    # largeur angulaire de l'influence (radians)
_TOUCH_ZONE = 48      # pixels au-delà de la surface pour déclencher le contact

# ── Physique du centre ─────────────────────────────────────────────────────
_CK   = 0.12
_CD   = 0.78
_FADE = 0.07

# Landmarks d'interaction : 5 bouts de doigts + paume
_INTERACT_LM = FINGERTIPS + [9]

# ── Couleurs eau (BGR) ────────────────────────────────────────────────────
_C_DEEP  = ( 80,  45,  10)
_C_MID   = (160, 105,  40)
_C_LIGHT = (210, 168,  90)
_C_RIM   = (250, 225, 155)
_C_WHITE = (255, 255, 248)


# ── API publique ───────────────────────────────────────────────────────────

def new_bubble_h():
    return {
        "cx": 0.0, "cy": 0.0, "r": float(BUBBLE_H_MIN_R),
        "vx": 0.0, "vy": 0.0, "vr": 0.0,
        "disp": np.zeros(N_SEG, dtype=np.float32),
        "vel":  np.zeros(N_SEG, dtype=np.float32),
        "alpha": 0.0,
    }


def update(bubble, hands_by_side, w, h):
    """Met à jour centre, rayon et déformations de la bulle."""
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    # ── Centre et rayon ──────────────────────────────────────────────────
    if left is not None and right is not None:
        lx, ly = _palm(left,  w, h)
        rx, ry = _palm(right, w, h)
        tcx = (lx + rx) * 0.5
        tcy = (ly + ry) * 0.5

        # Rayon cible = distance moyenne du centre aux 5 bouts de doigts de chaque main
        tip_dists = []
        for lm in (left, right):
            for lm_idx in FINGERTIPS:
                tx = lm[lm_idx].x * w
                ty = lm[lm_idx].y * h
                tip_dists.append(math.hypot(tx - tcx, ty - tcy))
        tr = max(BUBBLE_H_MIN_R, min(BUBBLE_H_MAX_R,
                                     sum(tip_dists) / len(tip_dists)))

        if bubble["alpha"] == 0.0:
            bubble["cx"], bubble["cy"], bubble["r"] = tcx, tcy, tr

        bubble["vx"] = bubble["vx"] * _CD + (tcx - bubble["cx"]) * _CK
        bubble["vy"] = bubble["vy"] * _CD + (tcy - bubble["cy"]) * _CK
        bubble["vr"] = bubble["vr"] * _CD + (tr   - bubble["r"])  * _CK
        bubble["alpha"] = min(1.0, bubble["alpha"] + _FADE)
    else:
        bubble["vx"] *= _CD
        bubble["vy"] *= _CD
        bubble["vr"] *= _CD
        bubble["alpha"] = max(0.0, bubble["alpha"] - _FADE)

    bubble["cx"] += bubble["vx"]
    bubble["cy"] += bubble["vy"]
    bubble["r"]   = max(BUBBLE_H_MIN_R, bubble["r"] + bubble["vr"])

    # ── Forces des doigts sur la surface ─────────────────────────────────
    cx, cy, r    = bubble["cx"], bubble["cy"], bubble["r"]
    disp         = bubble["disp"]
    vel          = bubble["vel"]
    hand_force   = np.zeros(N_SEG, dtype=np.float32)
    n_interact   = float(len(_INTERACT_LM))

    for side in ("Left", "Right"):
        lm = hands_by_side.get(side)
        if lm is None:
            continue
        for lm_idx in _INTERACT_LM:
            px = lm[lm_idx].x * w
            py = lm[lm_idx].y * h
            dx   = px - cx
            dy   = py - cy
            dist_p = math.hypot(dx, dy)
            pen    = (r + _TOUCH_ZONE) - dist_p
            if pen <= 0:
                continue
            ang_diff = _ANGLES - math.atan2(dy, dx)
            ang_diff = (ang_diff + math.pi) % (2 * math.pi) - math.pi
            weight   = np.exp(-ang_diff * ang_diff / (2 * _SIGMA * _SIGMA))
            # Négatif = enfonce depuis l'extérieur ; positif = pousse de l'intérieur
            sign = -1.0 if dist_p >= r else 1.0
            hand_force += sign * weight * (pen * _PUSH / n_interact)

    # ── Intégration ressort-masse + couplage voisins ──────────────────────
    acc   = -_SPRING_K * disp
    acc  += _COUPLING * (np.roll(disp, 1) + np.roll(disp, -1) - 2.0 * disp)
    acc  += hand_force
    vel  += acc
    vel  *= _DAMPING
    disp += vel
    np.clip(disp, -r * 0.55, r * 0.70, out=disp)


def render(frame, bubble, w, h):
    """Dessine la bulle d'eau 3D déformée en 9 couches."""
    alpha = bubble["alpha"]
    if alpha <= 0.01:
        return

    pts = _pts(bubble)
    cx  = int(bubble["cx"])
    cy  = int(bubble["cy"])
    r   = int(bubble["r"])
    t   = time.time()

    # ── 1. Halo gaussien additif ─────────────────────────────────────────
    glow = np.zeros_like(frame, dtype=np.uint8)
    cv2.polylines(glow, [pts], True, _C_MID, 18)
    frame[:] = cv2.addWeighted(frame, 1.0,
                                cv2.GaussianBlur(glow, (45, 45), 0),
                                alpha * 0.55, 0)

    # ── 2. Corps translucide (profondeur de l'eau) ───────────────────────
    ov = frame.copy()
    cv2.fillPoly(ov, [pts], _C_DEEP)
    cv2.addWeighted(ov, alpha * 0.30, frame, 1.0 - alpha * 0.30, 0, frame)

    # ── 3. Volume 3D : face illuminée (80 % de la taille, décalée) ───────
    inner80 = _scaled_pts(pts, cx, cy, 0.80, -r // 10, -r // 12)
    ov2 = frame.copy()
    cv2.fillPoly(ov2, [inner80], _C_MID)
    cv2.addWeighted(ov2, alpha * 0.16, frame, 1.0 - alpha * 0.16, 0, frame)

    # ── 4. Volume 3D : cœur lumineux (50 %, décalé haut-gauche) ─────────
    inner50 = _scaled_pts(pts, cx, cy, 0.52, -r // 8, -r // 10)
    ov3 = frame.copy()
    cv2.fillPoly(ov3, [inner50], _C_LIGHT)
    cv2.addWeighted(ov3, alpha * 0.10, frame, 1.0 - alpha * 0.10, 0, frame)

    # ── 5. Limb darkening : assombrissement des bords ────────────────────
    ov4 = frame.copy()
    cv2.polylines(ov4, [pts], True, (12, 8, 2), 16)
    cv2.addWeighted(ov4, alpha * 0.40, frame, 1.0 - alpha * 0.40, 0, frame)

    # ── 6. Caustiques internes animées ───────────────────────────────────
    for i in range(5):
        a   = t * 0.38 + i * math.pi * 0.4
        ex  = cx + int(r * 0.28 * math.cos(a))
        ey  = cy + int(r * 0.22 * math.sin(a * 1.45))
        erx = max(3, int(r * (0.10 + 0.04 * math.sin(t * 1.1 + i))))
        ery = max(2, int(r * (0.055 + 0.03 * math.cos(t * 0.85 + i))))
        ov5 = frame.copy()
        cv2.ellipse(ov5, (ex, ey), (erx, ery),
                    int((t * 18 + i * 36) % 180), 0, 360, _C_LIGHT, -1)
        cv2.addWeighted(ov5, alpha * 0.09, frame, 1.0 - alpha * 0.09, 0, frame)

    # ── 7. Rim Fresnel ────────────────────────────────────────────────────
    ov6 = frame.copy()
    cv2.polylines(ov6, [pts], True, _C_RIM, 4)
    cv2.addWeighted(ov6, alpha * 0.65, frame, 1.0 - alpha * 0.65, 0, frame)

    # ── 8. Surbrillance spéculaire principale ─────────────────────────────
    hl_x, hl_y = cx - r // 3, cy - r // 3
    ov7 = frame.copy()
    cv2.ellipse(ov7, (hl_x, hl_y),
                (max(5, r // 4), max(3, r // 7)), -30, 0, 360, _C_WHITE, -1)
    cv2.addWeighted(ov7, alpha * 0.85, frame, 1.0 - alpha * 0.85, 0, frame)

    # ── 9. Surbrillance secondaire + contour final ────────────────────────
    cv2.circle(frame, (cx + r // 3, cy + r // 4), max(2, r // 11), _C_WHITE, -1)
    cv2.polylines(frame, [pts], True, _C_RIM, 1)


# ── Utilitaires internes ───────────────────────────────────────────────────

def _palm(lm, w, h):
    return int(lm[9].x * w), int(lm[9].y * h)


def _pts(bubble):
    """N points de la surface déformée en int32."""
    radii = bubble["r"] + bubble["disp"]
    return np.column_stack([
        bubble["cx"] + radii * _COS_A,
        bubble["cy"] + radii * _SIN_A,
    ]).astype(np.int32)


def _scaled_pts(pts, cx, cy, scale, off_x=0, off_y=0):
    """Homothétie du polygone autour d'un centre décalé."""
    p = pts.astype(np.float32)
    ox, oy = cx + off_x, cy + off_y
    p[:, 0] = ox + (p[:, 0] - cx) * scale
    p[:, 1] = oy + (p[:, 1] - cy) * scale
    return p.astype(np.int32)
