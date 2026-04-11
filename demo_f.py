"""Démo F — Reconnaissance de gestes (pouce levé, victoire, poing, metal…)."""
from collections import deque, Counter
import math
import time
import cv2
import numpy as np

GESTURE_SMOOTH = 10  # frames pour confirmer un geste (anti-scintillement)

# Cercle magique Dr Strange
_CIRCLE_R    = 90   # rayon principal en pixels
_RUNE_COUNT  = 16   # nombre de marques runiques sur le cercle extérieur
_SPARK_COUNT = 8    # étincelles orbitant autour du cercle


def _extended(lm, tip, pip):
    return lm[tip].y < lm[pip].y


def _tips_distance(lm, tip_a, tip_b):
    """Distance euclidienne normalisée entre deux bouts de doigts."""
    dx = lm[tip_a].x - lm[tip_b].x
    dy = lm[tip_a].y - lm[tip_b].y
    return (dx * dx + dy * dy) ** 0.5


def detect_gesture(lm):
    """Retourne (nom, couleur_BGR) du geste détecté, ou (None, None)."""
    index_ext  = _extended(lm,  8,  6)
    middle_ext = _extended(lm, 12, 10)
    ring_ext   = _extended(lm, 16, 14)
    pinky_ext  = _extended(lm, 20, 18)
    # Pouce levé : tip au-dessus de ses articulations ET au-dessus du MCP de l'index
    thumb_up = lm[4].y < lm[3].y and lm[4].y < lm[2].y and lm[4].y < lm[5].y

    if thumb_up and not index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "Pouce leve !", (0, 200, 255)
    # Pouce écarté : tip (4) loin du MCP de l'index (5), quelle que soit l'orientation
    thumb_spread    = _tips_distance(lm, 4, 5) > 0.13
    fingers_together = _tips_distance(lm, 8, 12) < 0.07
    if thumb_spread and index_ext and middle_ext and not ring_ext and not pinky_ext and fingers_together:
        return "Dr Strange !", (0, 140, 255)
    if index_ext and middle_ext and not ring_ext and not pinky_ext and not thumb_up:
        return "Victoire !", (100, 255, 100)
    if not index_ext and not middle_ext and not ring_ext and not pinky_ext and not thumb_up:
        return "Poing !", (80, 80, 255)
    if index_ext and middle_ext and ring_ext and pinky_ext:
        return "Main ouverte", (255, 200, 50)
    if index_ext and not middle_ext and not ring_ext and pinky_ext:
        return "Metal !", (0, 80, 255)
    if index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "Index pointe", (200, 100, 255)
    return None, None


def _draw_dr_strange_circle(frame, cx, cy, r):
    """Cercle magique avec pentagramme tournant et étincelles, style Dr Strange."""
    t       = time.time()
    angle   = math.degrees(t * 1.8) % 360   # pentagramme : ~1 tour / 3,5 s
    angle2  = -math.degrees(t * 1.1) % 360  # runes : sens inverse, plus lent

    orange      = (  0, 120, 255)  # orange vif (BGR)
    orange_dark = (  0,  55, 180)  # orange sombre pour le halo
    white_warm  = (180, 200, 255)  # blanc chaud pour les tracés nets
    glow = np.zeros_like(frame, dtype=np.uint8)

    # ── Cercles concentriques ──────────────────────────────────────────────
    cv2.circle(glow, (cx, cy), r + 12, orange_dark, 5)
    cv2.circle(glow, (cx, cy), r,      orange_dark, 3)
    cv2.circle(glow, (cx, cy), r - 18, orange_dark, 2)

    # ── Marques runiques sur le cercle extérieur (tournent en sens inverse) ─
    for i in range(_RUNE_COUNT):
        a    = math.radians(angle2 + i * (360 / _RUNE_COUNT))
        long = 12 if i % 4 == 0 else 6          # grandes et petites marques
        r1   = r + 6
        r2   = r + 6 + long
        x1   = cx + int(r1 * math.cos(a))
        y1   = cy + int(r1 * math.sin(a))
        x2   = cx + int(r2 * math.cos(a))
        y2   = cy + int(r2 * math.sin(a))
        cv2.line(glow, (x1, y1), (x2, y2), orange_dark, 3)

    # ── Pentagramme (5 pointes, connexion en étoile 0→2→4→1→3→0) ─────────
    pts = []
    for i in range(5):
        a  = math.radians(angle + i * 72 - 90)
        px = cx + int((r - 16) * math.cos(a))
        py = cy + int((r - 16) * math.sin(a))
        pts.append((px, py))
    star = [0, 2, 4, 1, 3, 0]
    for k in range(len(star) - 1):
        cv2.line(glow, pts[star[k]], pts[star[k + 1]], orange, 4)

    # ── Halo par flou additif ──────────────────────────────────────────────
    frame[:] = cv2.add(frame, cv2.GaussianBlur(glow, (33, 33), 0))

    # ── Tracés nets par-dessus ─────────────────────────────────────────────
    cv2.circle(frame, (cx, cy), r + 12, orange, 1)
    cv2.circle(frame, (cx, cy), r,      orange, 1)
    cv2.circle(frame, (cx, cy), r - 18, orange, 1)
    for i in range(_RUNE_COUNT):
        a    = math.radians(angle2 + i * (360 / _RUNE_COUNT))
        long = 12 if i % 4 == 0 else 6
        r1, r2 = r + 6, r + 6 + long
        cv2.line(frame,
                 (cx + int(r1 * math.cos(a)), cy + int(r1 * math.sin(a))),
                 (cx + int(r2 * math.cos(a)), cy + int(r2 * math.sin(a))),
                 orange, 1)
    for k in range(len(star) - 1):
        cv2.line(frame, pts[star[k]], pts[star[k + 1]], white_warm, 1)

    # ── Étincelles orbitant autour du cercle ──────────────────────────────
    for i in range(_SPARK_COUNT):
        a   = math.radians(angle + i * (360 / _SPARK_COUNT))
        sx  = cx + int((r + 18) * math.cos(a))
        sy  = cy + int((r + 18) * math.sin(a))
        cv2.circle(frame, (sx, sy), 3, white_warm, -1)
        cv2.circle(frame, (sx, sy), 5, orange,     1)


def draw_gesture_label(frame, name, color, cx, cy, w, h):
    """Affiche le nom du geste dans un bandeau semi-transparent sous la main."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 1.1, 3
    (tw, th), _ = cv2.getTextSize(name, font, scale, thickness)
    pad = 14
    bx  = max(pad, min(cx - tw // 2, w - tw - pad))
    by  = min(cy + 60, h - 60)
    rx1, ry1 = bx - pad, by - th - pad
    rx2, ry2 = bx + tw + pad, by + pad
    overlay = frame.copy()
    cv2.rectangle(overlay, (rx1, ry1), (rx2, ry2), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, 2)
    cv2.putText(frame, name, (bx, by), font, scale, color, thickness)


def update_history(gesture_history, idx, hand_landmarks):
    """Met à jour l'historique de détection pour une main."""
    name, gcolor = detect_gesture(hand_landmarks)
    if idx not in gesture_history:
        gesture_history[idx] = deque(maxlen=GESTURE_SMOOTH)
    gesture_history[idx].append((name, gcolor))


def render(frame, gesture_history, active_ids, current_positions, hand_sizes, w, h):
    """Affiche les étiquettes de gestes lissés, purge les mains disparues."""
    for idx in list(gesture_history.keys()):
        if idx not in active_ids:
            del gesture_history[idx]
            continue
        history = gesture_history[idx]
        counts  = Counter(name for name, _ in history if name is not None)
        if not counts:
            continue
        best, freq = counts.most_common(1)[0]
        if freq >= GESTURE_SMOOTH // 2:
            gcolor = next(
                (c for n, c in history if n == best and c is not None),
                (200, 200, 200),
            )
            pcx, pcy = current_positions.get(idx, (w // 2, h // 2))
            if best == "Dr Strange !":
                r = max(_CIRCLE_R, hand_sizes.get(idx, _CIRCLE_R))
                _draw_dr_strange_circle(frame, pcx, pcy, r)
            else:
                draw_gesture_label(frame, best, gcolor, pcx, pcy, w, h)
