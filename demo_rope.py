"""Démo Corde — Boule soumise à la gravité, retenue par la corde entre les deux index."""
import cv2

_GRAVITY  = 0.38   # px/frame²
_BALL_R   = 22     # rayon de la boule en px
_FRICTION = 0.991  # frottement tangentiel sur la corde
_BOUNCE   = 0.20   # restitution sur les bords de l'écran


def new_rope(w, h):
    return {
        "bx": float(w // 2),
        "by": 60.0,
        "vx": 0.0,
        "vy": 0.0,
    }


def update(state, hands_by_side, w, h):
    # Gravité + déplacement
    state["vy"] += _GRAVITY
    state["bx"] += state["vx"]
    state["by"] += state["vy"]

    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")
    if left is not None and right is not None:
        px = int(left[8].x  * w)
        py = int(left[8].y  * h)
        qx = int(right[8].x * w)
        qy = int(right[8].y * h)
        _collide(state, px, py, qx, qy)

    # Bords de l'écran
    if state["bx"] < _BALL_R:
        state["bx"] = _BALL_R
        state["vx"] = abs(state["vx"]) * _BOUNCE
    elif state["bx"] > w - _BALL_R:
        state["bx"] = w - _BALL_R
        state["vx"] = -abs(state["vx"]) * _BOUNCE
    if state["by"] < _BALL_R:
        state["by"] = _BALL_R
        state["vy"] = abs(state["vy"]) * _BOUNCE
    elif state["by"] > h - _BALL_R:
        # Respawn en haut quand la boule touche le bas
        state["bx"] = float(w // 2)
        state["by"] = 60.0
        state["vx"] = 0.0
        state["vy"] = 0.0


def render(frame, state, hands_by_side, w, h):
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        px = int(left[8].x  * w)
        py = int(left[8].y  * h)
        qx = int(right[8].x * w)
        qy = int(right[8].y * h)

        # Corde : ombre + corps brun + reflet clair
        cv2.line(frame, (px + 2, py + 2), (qx + 2, qy + 2), (25, 15, 5),    5)
        cv2.line(frame, (px, py),         (qx, qy),          (80, 55, 20),   5)
        cv2.line(frame, (px, py),         (qx, qy),          (200, 150, 65), 2)

        # Points d'attache aux index
        for pt in [(px, py), (qx, qy)]:
            cv2.circle(frame, pt, 9, (170, 120, 45), -1)
            cv2.circle(frame, pt, 9, (230, 185, 95), 2)

    # Boule (ombre + corps + dégradé + reflet)
    bx, by = int(state["bx"]), int(state["by"])
    r = _BALL_R
    cv2.circle(frame, (bx + 4, by + 5), r,        (12, 8, 8),         -1)
    cv2.circle(frame, (bx, by),         r,        (40, 80, 195),       -1)
    cv2.circle(frame, (bx - 3, by - 3), r * 2//3, (65, 115, 225),     -1)
    cv2.circle(frame, (bx - r//3, by - r//3), r//4, (205, 230, 255),  -1)
    cv2.circle(frame, (bx, by),         r,        (85, 135, 255),       2)


# ── Physique interne ──────────────────────────────────────────────────────────

def _collide(state, px, py, qx, qy):
    """Détecte et résout la collision boule↔corde."""
    dx, dy = qx - px, qy - py
    len_sq = dx*dx + dy*dy
    if len_sq < 16:
        return

    rope_len = len_sq ** 0.5

    # Paramètre de projection sur la droite portant la corde (0 = P1, 1 = P2)
    t = ((state["bx"] - px)*dx + (state["by"] - py)*dy) / len_sq

    # Point le plus proche sur le segment [P1, P2]
    tc = max(0.0, min(1.0, t))
    cx = px + tc * dx
    cy = py + tc * dy

    # Vecteur (point proche → boule)
    rx = state["bx"] - cx
    ry = state["by"] - cy
    dist = (rx*rx + ry*ry) ** 0.5

    # Normale perpendiculaire à la corde, orientée "vers le haut" (y décroissant)
    nx, ny = -dy / rope_len, dx / rope_len
    if ny > 0:          # ny > 0 → pointe vers le bas en coords écran → inverser
        nx, ny = -nx, -ny

    # Distance signée : positive = boule au-dessus de la corde
    signed = (rx * nx + ry * ny) if dist > 0.001 else 0.0

    # Collision seulement si la boule est dans l'étendue du segment ET sous la surface
    if 0.0 <= t <= 1.0 and signed < _BALL_R:
        # Replacer la boule à la surface supérieure de la corde
        state["bx"] = cx + nx * _BALL_R
        state["by"] = cy + ny * _BALL_R

        # Annuler la composante de vitesse dirigée vers la corde
        v_n = state["vx"] * nx + state["vy"] * ny
        if v_n < 0:
            state["vx"] -= v_n * nx
            state["vy"] -= v_n * ny

        # Frottement sur la composante tangentielle (glissement)
        state["vx"] *= _FRICTION
        state["vy"] *= _FRICTION
