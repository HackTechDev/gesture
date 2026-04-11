"""Démo D — Dessin dans l'air avec l'index, effacement main ouverte."""
import cv2

DRAW_COLORS = [
    (255, 255, 255),  # blanc
    (100, 255, 100),  # vert
    (100, 100, 255),  # rouge
    (0,   220, 255),  # jaune
    (255, 100, 200),  # violet
    (50,  200, 255),  # orange
]
DRAW_THICKNESS = 3


def is_index_only(lm):
    """Index étendu, majeur/annulaire/auriculaire repliés."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y > lm[10].y and
            lm[16].y > lm[14].y and
            lm[20].y > lm[18].y)


def is_open_hand(lm):
    """Les 4 doigts étendus → effacement."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y < lm[10].y and
            lm[16].y < lm[14].y and
            lm[20].y < lm[18].y)


def draw_palette(frame, color_idx, w):
    """Affiche la barre de couleurs en haut à droite. Retourne (x0, y0, sw, gap)."""
    sw, gap = 28, 4
    total = len(DRAW_COLORS) * (sw + gap) - gap
    x0, y0 = w - total - 10, 40
    for i, color in enumerate(DRAW_COLORS):
        x = x0 + i * (sw + gap)
        cv2.rectangle(frame, (x, y0), (x + sw, y0 + sw), color, -1)
        if i == color_idx:
            cv2.rectangle(frame, (x - 2, y0 - 2), (x + sw + 2, y0 + sw + 2),
                          (255, 255, 255), 2)
    return x0, y0, sw, gap


def process(frame, hand_landmarks, w, h, canvas, prev_draw_pos, draw_color_idx, idx):
    """
    Gère dessin, sélection de couleur et effacement pour une main.
    Retourne (draw_color_idx, erase_triggered).
    """
    ix = int(hand_landmarks[8].x * w)
    iy = int(hand_landmarks[8].y * h)
    px_pinky = int(hand_landmarks[20].x * w)
    py_pinky = int(hand_landmarks[20].y * h)
    color = DRAW_COLORS[draw_color_idx]
    erase_triggered = False

    if is_open_hand(hand_landmarks):
        canvas[:] = 0
        erase_triggered = True
        prev_draw_pos.pop(idx, None)
    else:
        # Sélection couleur via petit doigt
        x0, y0, sw, gap = draw_palette(frame, draw_color_idx, w)
        for i in range(len(DRAW_COLORS)):
            bx = x0 + i * (sw + gap)
            if bx <= px_pinky <= bx + sw and y0 <= py_pinky <= y0 + sw:
                draw_color_idx = i
                color = DRAW_COLORS[i]
                prev_draw_pos.pop(idx, None)
                break

        if is_index_only(hand_landmarks):
            if idx in prev_draw_pos:
                cv2.line(canvas, prev_draw_pos[idx], (ix, iy), color, DRAW_THICKNESS)
            prev_draw_pos[idx] = (ix, iy)
            cv2.circle(frame, (ix, iy), 8, color, -1)
            cv2.circle(frame, (ix, iy), 8, (255, 255, 255), 1)
        else:
            prev_draw_pos.pop(idx, None)

    return draw_color_idx, erase_triggered


def render(frame, canvas, draw_color_idx, erase_flash, w, h):
    """Fusionne le canvas sur la frame et gère le flash d'effacement."""
    frame[:] = cv2.add(frame, canvas)
    draw_palette(frame, draw_color_idx, w)
    if erase_flash > 0:
        flash = frame.copy()
        cv2.rectangle(flash, (0, 0), (w, h), (255, 255, 255), -1)
        cv2.addWeighted(flash, erase_flash / 12 * 0.35, frame,
                        1 - erase_flash / 12 * 0.35, 0, frame)
        cv2.putText(frame, "EFFACE !", (w // 2 - 80, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 200), 3)
    return max(0, erase_flash - 1)
