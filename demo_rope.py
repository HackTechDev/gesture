"""Démo Corde — Boule soumise à la gravité, retenue par la corde entre les deux index.

Physique de glissement explicite :
  a_t = g · ty  (composante de la gravité le long de la pente)

Rebond par le bas :
  prev_signed − signed  mesure la vitesse d'approche de la corde.
  Si la corde monte vers la balle (v_n >= 0 et rope_approach > seuil) → rebond.
"""
import cv2
from config import ROPE_GRAVITY, ROPE_FRICTION

_BALL_R      = 22    # rayon de la boule en px
_BOUNCE      = 0.20  # restitution sur les bords de l'écran
_RESTITUTION = 0.80  # énergie conservée lors d'un rebond corde→balle
_MAX_BOUNCE  = 22.0  # vitesse de rebond maximale en px/frame


def new_rope(w, h):
    return {
        "bx":          float(w // 2),
        "by":          60.0,
        "vx":          0.0,
        "vy":          0.0,
        "prev_signed": 9999.0,   # distance signée au frame précédent
    }


def update(state, hands_by_side, w, h):
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        px = int(left[8].x  * w);  py = int(left[8].y  * h)
        qx = int(right[8].x * w);  qy = int(right[8].y * h)
        _step_with_rope(state, px, py, qx, qy)
    else:
        state["prev_signed"] = 9999.0
        _step_free(state)

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
        state["bx"] = float(w) / 2
        state["by"] = 60.0
        state["vx"] = 0.0
        state["vy"] = 0.0
        state["prev_signed"] = 9999.0


def render(frame, state, hands_by_side, w, h):
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        px = int(left[8].x  * w);  py = int(left[8].y  * h)
        qx = int(right[8].x * w);  qy = int(right[8].y * h)

        cv2.line(frame, (px + 2, py + 2), (qx + 2, qy + 2), (25, 15, 5),    5)
        cv2.line(frame, (px, py),         (qx, qy),          (80, 55, 20),   5)
        cv2.line(frame, (px, py),         (qx, qy),          (200, 150, 65), 2)

        for pt in [(px, py), (qx, qy)]:
            cv2.circle(frame, pt, 9, (170, 120, 45), -1)
            cv2.circle(frame, pt, 9, (230, 185, 95), 2)

    bx, by = int(state["bx"]), int(state["by"])
    r = _BALL_R
    cv2.circle(frame, (bx + 4, by + 5), r,          (12, 8, 8),         -1)
    cv2.circle(frame, (bx, by),         r,          (40, 80, 195),       -1)
    cv2.circle(frame, (bx - 3, by - 3), r * 2 // 3, (65, 115, 225),    -1)
    cv2.circle(frame, (bx - r//3, by - r//3), r//4, (205, 230, 255),   -1)
    cv2.circle(frame, (bx, by),         r,          (85, 135, 255),       2)


# ── Physique interne ──────────────────────────────────────────────────────────

def _step_free(state):
    """Chute libre : gravité pleine, aucune contrainte."""
    state["vy"] += ROPE_GRAVITY
    state["bx"] += state["vx"]
    state["by"] += state["vy"]


def _step_with_rope(state, px, py, qx, qy):
    """Un pas de simulation.

    Trois cas possibles :
      1. signed < BALL_R et v_n < 0  → balle tombe sur la corde  → glissement
      2. signed < BALL_R et rope_approach > seuil → corde frappe par le bas → rebond
      3. sinon                                    → chute libre
    """
    dx, dy = qx - px, qy - py
    len_sq = dx*dx + dy*dy
    if len_sq < 16:
        _step_free(state)
        return

    rope_len = len_sq ** 0.5
    tx, ty   = dx / rope_len, dy / rope_len

    # Normale perpendiculaire, orientée vers le haut (ny < 0 en screen coords)
    nx, ny = -ty, tx
    if ny > 0:
        nx, ny = -nx, -ny

    # Projection du centre de la boule sur le segment
    rel_x = state["bx"] - px
    rel_y = state["by"] - py
    t_px  = rel_x * tx + rel_y * ty
    tc    = max(0.0, min(rope_len, t_px))
    cx    = px + tc * tx
    cy    = py + tc * ty

    ox    = state["bx"] - cx
    oy    = state["by"] - cy
    dist  = (ox*ox + oy*oy) ** 0.5
    # Distance signée : positive = balle au-dessus de la corde
    signed = (ox * nx + oy * ny) if dist > 0.001 else 0.0

    prev_signed   = state["prev_signed"]
    # Vitesse d'approche de la corde vers la balle (positive si la corde monte)
    rope_approach = max(0.0, prev_signed - signed)

    if 0.0 <= t_px <= rope_len and signed < _BALL_R:
        # Vitesse normale de la balle (positive = s'éloigne de la corde vers le haut)
        v_n = state["vx"] * nx + state["vy"] * ny

        if v_n < 0:
            # ── Cas 1 : balle tombe sur la corde ────────────────────────────
            state["bx"] = cx + nx * _BALL_R
            state["by"] = cy + ny * _BALL_R
            v_t = state["vx"] * tx + state["vy"] * ty
            v_t = (v_t + ROPE_GRAVITY * ty) * ROPE_FRICTION
            state["vx"] = v_t * tx
            state["vy"] = v_t * ty
            state["bx"] += state["vx"]
            state["by"] += state["vy"]
            state["prev_signed"] = signed

        elif rope_approach > 1.0:
            # ── Cas 2 : corde frappe par le bas → rebond ─────────────────────
            state["bx"] = cx + nx * _BALL_R
            state["by"] = cy + ny * _BALL_R
            bounce = min(rope_approach * _RESTITUTION, _MAX_BOUNCE)
            # Conserver la vitesse tangentielle, ajouter le rebond en normale
            v_t = state["vx"] * tx + state["vy"] * ty
            state["vx"] = v_t * tx + nx * (v_n + bounce)
            state["vy"] = v_t * ty + ny * (v_n + bounce)
            state["bx"] += state["vx"]
            state["by"] += state["vy"]
            state["prev_signed"] = signed

        else:
            # ── Cas 3 : balle s'éloigne naturellement → chute libre ──────────
            state["prev_signed"] = 9999.0
            _step_free(state)

    else:
        state["prev_signed"] = 9999.0
        _step_free(state)
