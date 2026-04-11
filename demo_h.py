"""Démo H — Bulle d'eau en apesanteur, modelable avec les deux mains."""
import math
import time
import cv2
import numpy as np
from config import BUBBLE_H_MIN_R, BUBBLE_H_MAX_R

_SPRING_K  = 0.12   # raideur du ressort (position et rayon)
_SPRING_D  = 0.78   # amortissement
_FADE_STEP = 0.07   # vitesse de fondu (apparition / disparition)
_TOUCH_MARGIN = 38  # pixels — zone de contact autour de la surface

# Couleurs eau (BGR)
_C_DEEP  = ( 90,  50,  15)   # bleu profond
_C_MID   = (175, 110,  45)   # bleu moyen
_C_LIGHT = (220, 175, 100)   # bleu clair
_C_RIM   = (255, 230, 160)   # reflet de bord (rim Fresnel)
_C_WHITE = (255, 255, 245)   # surbrillance spéculaire


def new_bubble_h():
    return {
        "cx": 0.0, "cy": 0.0, "r": float(BUBBLE_H_MIN_R),
        "vx": 0.0, "vy": 0.0, "vr": 0.0,
        "alpha": 0.0,
    }


def _palm(lm, w, h):
    """Coordonnées pixel du centre de la paume (landmark 9)."""
    return int(lm[9].x * w), int(lm[9].y * h)


def update(bubble, hands_by_side, w, h):
    """Met à jour position, rayon et opacité de la bulle (ressort + fondu)."""
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        lx, ly = _palm(left,  w, h)
        rx, ry = _palm(right, w, h)

        target_cx = (lx + rx) / 2
        target_cy = (ly + ry) / 2
        dist      = ((lx - rx) ** 2 + (ly - ry) ** 2) ** 0.5
        target_r  = max(BUBBLE_H_MIN_R, min(BUBBLE_H_MAX_R, dist / 2.2))

        # Téléporte au centre si première apparition
        if bubble["alpha"] == 0.0:
            bubble["cx"], bubble["cy"], bubble["r"] = target_cx, target_cy, target_r

        bubble["vx"] = bubble["vx"] * _SPRING_D + (target_cx - bubble["cx"]) * _SPRING_K
        bubble["vy"] = bubble["vy"] * _SPRING_D + (target_cy - bubble["cy"]) * _SPRING_K
        bubble["vr"] = bubble["vr"] * _SPRING_D + (target_r  - bubble["r"])  * _SPRING_K
        bubble["alpha"] = min(1.0, bubble["alpha"] + _FADE_STEP)
    else:
        # Fondu sortant
        bubble["vx"] *= _SPRING_D
        bubble["vy"] *= _SPRING_D
        bubble["vr"] *= _SPRING_D
        bubble["alpha"] = max(0.0, bubble["alpha"] - _FADE_STEP)

    bubble["cx"] += bubble["vx"]
    bubble["cy"] += bubble["vy"]
    bubble["r"]   = max(BUBBLE_H_MIN_R, bubble["r"] + bubble["vr"])


def _contacts(bubble, hands_by_side, w, h):
    """Retourne [(contact_px, contact_py, depth, nx, ny), ...] pour chaque main proche."""
    result = []
    cx, cy, r = bubble["cx"], bubble["cy"], bubble["r"]
    for side in ("Left", "Right"):
        lm = hands_by_side.get(side)
        if lm is None:
            continue
        hx, hy = _palm(lm, w, h)
        dx, dy = hx - cx, hy - cy
        dist   = (dx * dx + dy * dy) ** 0.5
        if dist < r + _TOUCH_MARGIN:
            depth = max(0.0, r + _TOUCH_MARGIN - dist)
            nx, ny = (dx / dist, dy / dist) if dist > 1 else (0.0, -1.0)
            # Point de contact : sur la surface dans la direction de la main
            contact_d = min(dist, r)
            cpx = int(cx + nx * contact_d)
            cpy = int(cy + ny * contact_d)
            result.append((cpx, cpy, depth, nx, ny))
    return result


def render(frame, bubble, hands_by_side, w, h):
    """Dessine la bulle d'eau avec ses effets visuels."""
    alpha = bubble["alpha"]
    if alpha <= 0.01:
        return

    cx = int(bubble["cx"])
    cy = int(bubble["cy"])
    r  = int(bubble["r"])
    t  = time.time()

    contacts = _contacts(bubble, hands_by_side, w, h)

    # ── 1. Halo extérieur (glow additif) ─────────────────────────────────
    glow = np.zeros_like(frame, dtype=np.uint8)
    cv2.circle(glow, (cx, cy), r + 28, _C_MID, 12)
    glow_b = cv2.GaussianBlur(glow, (39, 39), 0)
    frame[:] = cv2.addWeighted(frame, 1.0, glow_b, alpha * 0.55, 0)

    # ── 2. Corps translucide ──────────────────────────────────────────────
    ov = frame.copy()
    cv2.circle(ov, (cx, cy), r, _C_DEEP, -1)
    cv2.addWeighted(ov, alpha * 0.30, frame, 1 - alpha * 0.30, 0, frame)

    # ── 3. Volume intérieur (dégradé simulé) ─────────────────────────────
    ov2 = frame.copy()
    cv2.circle(ov2, (cx - r // 7, cy - r // 8), int(r * 0.68), _C_MID, -1)
    cv2.addWeighted(ov2, alpha * 0.14, frame, 1 - alpha * 0.14, 0, frame)

    # ── 4. Caustiques animées (reflets internes mobiles) ─────────────────
    for i in range(5):
        a   = t * 0.38 + i * math.pi * 2 / 5
        ex  = cx + int(r * 0.30 * math.cos(a))
        ey  = cy + int(r * 0.25 * math.sin(a * 1.45))
        erx = max(3, int(r * (0.11 + 0.04 * math.sin(t * 1.1 + i))))
        ery = max(2, int(r * (0.055 + 0.03 * math.cos(t * 0.85 + i))))
        ang = int((t * 18 + i * 36) % 180)
        ov3 = frame.copy()
        cv2.ellipse(ov3, (ex, ey), (erx, ery), ang, 0, 360, _C_LIGHT, -1)
        cv2.addWeighted(ov3, alpha * 0.09, frame, 1 - alpha * 0.09, 0, frame)

    # ── 5. Indentations des mains ─────────────────────────────────────────
    for cpx, cpy, depth, nx, ny in contacts:
        indent_r = max(10, int(depth * 0.75))

        # Cuvette sombre
        ind = frame.copy()
        cv2.circle(ind, (cpx, cpy), indent_r, _C_DEEP, -1)
        blend = min(0.60, depth / (r + 1))
        cv2.addWeighted(ind, blend * alpha, frame, 1 - blend * alpha, 0, frame)

        # Bord lumineux de l'indent (tension de surface)
        cv2.circle(frame, (cpx, cpy), indent_r, _C_RIM, 2)

        # Mini-bulle d'air au fond si indent profond
        if indent_r > 16:
            air_r = max(3, indent_r // 4)
            air_x = cpx - int(nx * air_r)
            air_y = cpy - int(ny * air_r)
            ov4 = frame.copy()
            cv2.circle(ov4, (air_x, air_y), air_r, _C_LIGHT, -1)
            cv2.addWeighted(ov4, alpha * 0.65, frame, 1 - alpha * 0.65, 0, frame)

    # ── 6. Rim Fresnel (bord lumineux) ───────────────────────────────────
    rim = frame.copy()
    cv2.circle(rim, (cx, cy), r, _C_RIM, 6)
    cv2.addWeighted(rim, alpha * 0.60, frame, 1 - alpha * 0.60, 0, frame)

    # ── 7. Surbrillance spéculaire principale ─────────────────────────────
    hl_x = cx - r // 3
    hl_y = cy - r // 3
    hl_a = max(5, r // 4)
    hl_b = max(3, r // 7)
    hl = frame.copy()
    cv2.ellipse(hl, (hl_x, hl_y), (hl_a, hl_b), -30, 0, 360, _C_WHITE, -1)
    cv2.addWeighted(hl, alpha * 0.82, frame, 1 - alpha * 0.82, 0, frame)

    # ── 8. Surbrillance secondaire ────────────────────────────────────────
    cv2.circle(frame, (cx + r // 3, cy + r // 4), max(2, r // 11), _C_WHITE, -1)

    # ── 9. Contour final ──────────────────────────────────────────────────
    cv2.circle(frame, (cx, cy), r, _C_RIM, 1)
