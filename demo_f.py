"""Démo F — Reconnaissance de gestes (pouce levé, victoire, poing, metal…)."""
from collections import deque, Counter
import cv2

GESTURE_SMOOTH = 10  # frames pour confirmer un geste (anti-scintillement)


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
    fingers_together = _tips_distance(lm, 8, 12) < 0.07
    if thumb_up and index_ext and middle_ext and not ring_ext and not pinky_ext and fingers_together:
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


def render(frame, gesture_history, active_ids, current_positions, w, h):
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
            draw_gesture_label(frame, best, gcolor, pcx, pcy, w, h)
