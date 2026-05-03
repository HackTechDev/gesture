"""Démo Corde — Boule soumise à la gravité, retenue par la corde entre les deux index.

Physique de glissement explicite :
  a_t = g · ty  (composante de la gravité le long de la pente)
  ty > 0 → corde descend vers la droite → boule glisse à droite
  ty < 0 → corde monte vers la droite  → boule glisse à gauche
  Vitesse d'équilibre ∝ sin(inclinaison) / (1 - FRICTION)
"""
import cv2
from config import ROPE_GRAVITY, ROPE_FRICTION

_BALL_R  = 22    # rayon de la boule en px
_BOUNCE  = 0.20  # restitution sur les bords de l'écran


def new_rope(w, h):
    return {
        "bx": float(w // 2),
        "by": 60.0,
        "vx": 0.0,
        "vy": 0.0,
    }


def update(state, hands_by_side, w, h):
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        px = int(left[8].x  * w);  py = int(left[8].y  * h)
        qx = int(right[8].x * w);  qy = int(right[8].y * h)
        _step_with_rope(state, px, py, qx, qy)
    else:
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
        # Respawn en haut
        state["bx"] = float(w) / 2
        state["by"] = 60.0
        state["vx"] = 0.0
        state["vy"] = 0.0


def render(frame, state, hands_by_side, w, h):
    left  = hands_by_side.get("Left")
    right = hands_by_side.get("Right")

    if left is not None and right is not None:
        px = int(left[8].x  * w);  py = int(left[8].y  * h)
        qx = int(right[8].x * w);  qy = int(right[8].y * h)

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
    cv2.circle(frame, (bx + 4, by + 5), r,          (12, 8, 8),         -1)
    cv2.circle(frame, (bx, by),         r,          (40, 80, 195),       -1)
    cv2.circle(frame, (bx - 3, by - 3), r * 2 // 3, (65, 115, 225),    -1)
    cv2.circle(frame, (bx - r//3, by - r//3), r//4, (205, 230, 255),   -1)
    cv2.circle(frame, (bx, by),         r,          (85, 135, 255),       2)


# ── Physique interne ──────────────────────────────────────────────────────────

def _step_free(state):
    """Chute libre : gravité pleine, pas de contrainte."""
    state["vy"] += ROPE_GRAVITY
    state["bx"] += state["vx"]
    state["by"] += state["vy"]


def _step_with_rope(state, px, py, qx, qy):
    """Un pas de simulation avec corde présente.

    Si la boule est sur le segment : physique de glissement (a_t = g·ty).
    Si la boule est hors du segment : chute libre.
    """
    dx, dy = qx - px, qy - py
    len_sq = dx*dx + dy*dy
    if len_sq < 16:
        _step_free(state)
        return

    rope_len = len_sq ** 0.5
    tx, ty   = dx / rope_len, dy / rope_len   # tangente normalisée

    # Normale perpendiculaire à la corde, orientée vers le haut (ny < 0 en screen)
    nx, ny = -ty, tx
    if ny > 0:          # pointe vers le bas → inverser
        nx, ny = -nx, -ny

    # Projection du centre de la boule sur la droite portant la corde (en px depuis P1)
    rel_x = state["bx"] - px
    rel_y = state["by"] - py
    t_px  = rel_x * tx + rel_y * ty
    tc    = max(0.0, min(rope_len, t_px))
    cx    = px + tc * tx
    cy    = py + tc * ty

    # Distance signée (positive = au-dessus de la corde)
    ox     = state["bx"] - cx
    oy     = state["by"] - cy
    dist   = (ox*ox + oy*oy) ** 0.5
    signed = (ox * nx + oy * ny) if dist > 0.001 else 0.0

    if 0.0 <= t_px <= rope_len and signed < _BALL_R:
        # ── Boule sur la corde ──────────────────────────────────────────────
        # Coller à la surface supérieure
        state["bx"] = cx + nx * _BALL_R
        state["by"] = cy + ny * _BALL_R

        # Vitesse tangentielle actuelle (les composantes normales sont ignorées)
        v_t = state["vx"] * tx + state["vy"] * ty

        # Accélération tangentielle = projection de la gravité sur la pente :
        #   a_t = (0, g) · (tx, ty) = g * ty
        # Plus l'inclinaison est grande, plus |ty| est grand, plus la boule accélère.
        v_t = (v_t + ROPE_GRAVITY * ty) * ROPE_FRICTION

        state["vx"] = v_t * tx
        state["vy"] = v_t * ty
        state["bx"] += state["vx"]
        state["by"] += state["vy"]
    else:
        # ── Hors corde : chute libre ────────────────────────────────────────
        _step_free(state)
