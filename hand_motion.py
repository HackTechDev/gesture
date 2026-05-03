import urllib.request
import os
import time
from collections import deque
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import demo_a
import demo_b
import demo_c
import demo_d
import demo_f
import demo_g
import demo_h
import demo_k
import demo_l
import demo_terre
import demo_tetris
import demo_flame
import demo_pixel
from config import (
    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS,
    MOVEMENT_THRESHOLD, FPS_SMOOTHING,
    NUM_HANDS,
    MIN_DETECTION_CONFIDENCE, MIN_PRESENCE_CONFIDENCE, MIN_TRACKING_CONFIDENCE,
    BUBBLE_COUNT,
)

BaseOptions = mp_python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

# --- Fenêtre ---
WINDOW_NAME = "Detection de mouvement de la main"

# --- Modèle ---
MODEL_PATH = "hand_landmarker_full.task"
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


# ---------------------------------------------------------------------------
# Système d'intro (mode d'emploi avant chaque démo)
# ---------------------------------------------------------------------------

_CONFIRM_FRAMES = 20   # frames de main ouverte pour valider (~0.7 s à 30 fps)

_INTROS = {
    "a": {
        "title": "Filaments néon",
        "lines": [
            "Nécessite les deux mains simultanément",
            "Des filaments colorés relient vos doigts",
        ],
    },
    "b": {
        "title": "Bulles à éclater",
        "lines": [
            "Pincez pouce + index sur une bulle pour l'éclater",
            "Éclater un maximum de bulles en 30 secondes",
        ],
    },
    "c": {
        "title": "Bulle physique",
        "lines": [
            "Approchez l'index de la bulle pour la pousser",
            "Elle rebondit sur les bords de l'écran",
        ],
    },
    "d": {
        "title": "Dessin dans l'air",
        "lines": [
            "Index seul étendu  →  dessiner un trait",
            "Main ouverte (4 doigts)  →  effacer le canvas",
            "Auriculaire sur la palette (haut droite)  →  changer la couleur",
        ],
    },
    "f": {
        "title": "Reconnaissance de gestes",
        "lines": [
            "7 gestes reconnus :",
            "Pouce levé · Victoire · Poing · Main ouverte",
            "Index pointé · Metal · Dr Strange",
        ],
    },
    "g": {
        "title": "Traînées de mouvement",
        "lines": [
            "Bougez vos mains librement",
            "Chaque bout de doigt laisse une traînée lumineuse colorée",
        ],
    },
    "h": {
        "title": "Bulle d'eau 3D",
        "lines": [
            "Nécessite les deux mains simultanément",
            "La bulle apparaît entre vos paumes",
            "Approchez les doigts pour déformer sa surface",
        ],
    },
    "k": {
        "title": "Galaxie spirale 3D",
        "lines": [
            "Nécessite les deux mains simultanément",
            "Mains à la même hauteur  →  vue de tranche (bord)",
            "Mains décalées verticalement  →  vue de face (bras spiraux)",
        ],
    },
    "l": {
        "title": "Puzzle 3×3",
        "lines": [
            "Index pointé sur une pièce  →  attraper",
            "Poing  →  déposer (magnétisme automatique à < 100 px)",
            "Reconstituez l'image complète en 3 minutes",
        ],
    },
    "t": {
        "title": "Globe terrestre 3D",
        "lines": [
            "Nécessite les deux mains simultanément",
            "Mouvement horizontal  →  rotation gauche / droite",
            "Mouvement vertical  →  rotation avant / arrière",
        ],
    },
    "v": {
        "title": "Tetris",
        "lines": [
            "Index pointé + déplacement horizontal  →  déplacer la pièce",
            "Poing  →  chute rapide",
            "Main ouverte  →  rotation de la pièce",
        ],
    },
    "p": {
        "title": "Pixelisation",
        "lines": [
            "Nécessite les deux mains simultanément",
            "Pouce + index de chaque main délimitent la zone",
            "La vidéo est pixelisée à l'intérieur du polygone",
        ],
    },
    "e": {
        "title": "Flammes",
        "lines": [
            "Ouvrez la main  →  flammes sur les bouts des doigts",
            "Fermez la main  →  les flammes s'éteignent",
        ],
    },
}


def _make_intro(key):
    d = _INTROS[key]
    return {"key": key, "title": d["title"], "lines": d["lines"], "confirm": 0}


def _is_open_hand(lm):
    """Quatre doigts étendus (validation de l'intro)."""
    return (lm[8].y  < lm[6].y  and
            lm[12].y < lm[10].y and
            lm[16].y < lm[14].y and
            lm[20].y < lm[18].y)


def _draw_intro(frame, intro, w, h, pct):
    """Affiche la carte d'instructions en incrustation semi-transparente."""
    # Fond sombre
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, h), (8, 8, 20), -1)
    cv2.addWeighted(ov, 0.78, frame, 0.22, 0, frame)

    n_lines = len(intro["lines"])
    card_w  = min(640, w - 80)
    card_h  = 185 + n_lines * 38
    cx      = (w - card_w) // 2
    cy      = (h - card_h) // 2

    # Fond de la carte
    card_ov = frame.copy()
    cv2.rectangle(card_ov, (cx, cy), (cx + card_w, cy + card_h), (28, 28, 48), -1)
    cv2.addWeighted(card_ov, 0.88, frame, 0.12, 0, frame)
    cv2.rectangle(frame, (cx, cy), (cx + card_w, cy + card_h), (90, 90, 130), 1)

    # Titre
    (tw, _), _ = cv2.getTextSize(intro["title"], cv2.FONT_HERSHEY_SIMPLEX, 0.95, 2)
    cv2.putText(frame, intro["title"], ((w - tw) // 2, cy + 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 220, 255), 2)

    # Séparateur haut
    cv2.line(frame, (cx + 18, cy + 64), (cx + card_w - 18, cy + 64), (70, 70, 110), 1)

    # Lignes d'instructions
    for i, line in enumerate(intro["lines"]):
        (lw, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.62, 1)
        cv2.putText(frame, line, ((w - lw) // 2, cy + 100 + i * 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (210, 210, 210), 1)

    # Séparateur bas
    sep_y = cy + 112 + n_lines * 38
    cv2.line(frame, (cx + 18, sep_y), (cx + card_w - 18, sep_y), (70, 70, 110), 1)

    # Texte de validation
    msg = "Ouvrez la main pour commencer"
    (mw, _), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.68, 1)
    cv2.putText(frame, msg, ((w - mw) // 2, sep_y + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.68, (160, 255, 160), 1)

    # Barre de progression
    bar_y  = sep_y + 48
    bar_x0 = cx + 18
    bar_x1 = cx + card_w - 18
    bar_len = bar_x1 - bar_x0
    cv2.rectangle(frame, (bar_x0, bar_y), (bar_x1, bar_y + 10), (40, 40, 40), -1)
    fill = int(bar_len * pct)
    if fill > 0:
        cv2.rectangle(frame, (bar_x0, bar_y), (bar_x0 + fill, bar_y + 10), (0, 200, 80), -1)
    cv2.rectangle(frame, (bar_x0, bar_y), (bar_x1, bar_y + 10), (90, 90, 90), 1)


# ---------------------------------------------------------------------------
# Utilitaires communs
# ---------------------------------------------------------------------------

def download_model():
    if not os.path.exists(MODEL_PATH):
        print(f"Téléchargement du modèle vers {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Modèle téléchargé.")


def enhance_frame(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def draw_hand(frame, hand_landmarks, w, h):
    for start, end in HAND_CONNECTIONS:
        x1, y1 = int(hand_landmarks[start].x * w), int(hand_landmarks[start].y * h)
        x2, y2 = int(hand_landmarks[end].x * w),   int(hand_landmarks[end].y * h)
        cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
    for lm in hand_landmarks:
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (255, 255, 255), -1)


def palm_center(hand_landmarks, w, h):
    lm = hand_landmarks[9]
    return int(lm.x * w), int(lm.y * h)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    download_model()

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.VIDEO,
        num_hands=NUM_HANDS,
        min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
        min_hand_presence_confidence=MIN_PRESENCE_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
    )

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Erreur : impossible d'ouvrir la webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          CAMERA_FPS)

    w_cam = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_cam = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # --- FPS ---
    fps_times = deque(maxlen=FPS_SMOOTHING)

    # --- État général ---
    prev_positions = {}

    # --- Démo A ---
    show_a = False

    # --- Démo B ---
    show_b     = False
    bubbles    = []
    pops       = []
    score      = 0
    game_start = None

    # --- Démo C ---
    show_c       = False
    bubble_c     = None
    prev_index_c = {}

    # --- Démo D ---
    show_d         = False
    canvas         = None
    prev_draw_pos  = {}
    draw_color_idx = 0
    erase_flash    = 0

    # --- Démo F ---
    show_f          = False
    gesture_history = {}
    hand_sizes      = {}

    # --- Démo G ---
    show_g        = False
    trail_history = {}

    # --- Démo H ---
    show_h   = False
    bubble_h = None

    # --- Démo K ---
    show_k = False
    galaxy  = None

    # --- Démo L ---
    show_l = False
    puzzle  = None

    # --- Démo Terre ---
    show_terre = False
    terre      = None

    # --- Démo Tetris ---
    show_tetris = False
    tetris      = None

    # --- Démo Pixel ---
    show_pixel = False

    # --- Démo Flame ---
    show_flame = False
    flame      = None

    # --- Intro ---
    pending_intro = None

    # --- Landmarks ---
    show_landmarks = True

    # --- Fenêtre ---
    fullscreen = False
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            fps_times.append(time.time())
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            enhanced = enhance_frame(frame)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB),
            )
            results = landmarker.detect_for_video(mp_image, timestamp_ms)

            status_text  = "Aucune main detectee"
            status_color = (200, 200, 200)
            current_positions = {}
            hands_by_side     = {}

            for idx, hand_landmarks in enumerate(results.hand_landmarks or []):
                if show_landmarks:
                    draw_hand(frame, hand_landmarks, w, h)

                cx, cy = palm_center(hand_landmarks, w, h)
                current_positions[idx] = (cx, cy)
                if show_landmarks:
                    cv2.circle(frame, (cx, cy), 7, (255, 0, 0), -1)

                if idx in prev_positions:
                    px, py = prev_positions[idx]
                    dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                    if dist > MOVEMENT_THRESHOLD:
                        status_text  = f"Mouvement detecte !  ({dist:.0f} px)"
                        status_color = (0, 80, 255)
                        if show_landmarks:
                            cv2.arrowedLine(frame, (px, py), (cx, cy), (0, 0, 255), 2, tipLength=0.4)
                    else:
                        status_text  = "Main immobile"
                        status_color = (0, 220, 0)
                else:
                    status_text = "Main detectee"

                if results.handedness and idx < len(results.handedness):
                    side = results.handedness[idx][0].display_name
                    hands_by_side[side] = hand_landmarks

                # --- Traitements par main (seulement hors intro) ---
                if pending_intro is None:
                    if show_d and canvas is not None:
                        draw_color_idx, erased = demo_d.process(
                            frame, hand_landmarks, w, h, canvas,
                            prev_draw_pos, draw_color_idx, idx,
                        )
                        if erased:
                            erase_flash = 12

                    if show_f:
                        demo_f.update_history(gesture_history, idx, hand_landmarks)
                        wx = int(hand_landmarks[0].x * w)
                        wy = int(hand_landmarks[0].y * h)
                        hand_sizes[idx] = int(((cx - wx) ** 2 + (cy - wy) ** 2) ** 0.5)

                    if show_g:
                        demo_g.update_trails(trail_history, idx, hand_landmarks, w, h)

                    if show_c and bubble_c is not None:
                        ix = int(hand_landmarks[8].x * w)
                        iy = int(hand_landmarks[8].y * h)
                        if idx in prev_index_c:
                            demo_c.push_bubble_c(bubble_c, ix, iy, *prev_index_c[idx])
                        prev_index_c[idx] = (ix, iy)

                    if show_b and bubbles:
                        score = demo_b.process(frame, hand_landmarks, w, h, bubbles, pops, score)

            prev_positions = current_positions
            if not show_c:
                prev_index_c.clear()

            # --- Rendu démos (seulement hors intro) ---
            if pending_intro is None:
                if show_a and "Left" in hands_by_side and "Right" in hands_by_side:
                    demo_a.draw_filaments(frame, hands_by_side["Left"],
                                          hands_by_side["Right"], w, h)

                if show_b:
                    demo_b.render(frame, bubbles, pops, score, game_start, w, h)

                if show_d and canvas is not None:
                    erase_flash = demo_d.render(frame, canvas, draw_color_idx, erase_flash, w, h)

                if show_c and bubble_c is not None:
                    demo_c.update_bubble_c(bubble_c, w, h)
                    demo_c.draw_bubble_c(frame, bubble_c)

                active_ids = set(range(len(results.hand_landmarks or [])))

                if show_f:
                    demo_f.render(frame, gesture_history, active_ids, current_positions, hand_sizes, w, h)

                if show_g:
                    demo_g.render(frame, trail_history, active_ids, w, h)

                if show_h and bubble_h is not None:
                    demo_h.update(bubble_h, hands_by_side, w, h)
                    demo_h.render(frame, bubble_h, w, h)

                if show_k and galaxy is not None:
                    demo_k.update(galaxy, hands_by_side, w, h)
                    demo_k.render(frame, galaxy, w, h)

                if show_l:
                    if puzzle is None:
                        puzzle = demo_l.new_puzzle(w, h)
                    demo_l.update(puzzle, hands_by_side, w, h)
                    demo_l.render(frame, puzzle, w, h)

                if show_terre:
                    if terre is None:
                        terre = demo_terre.new_terre()
                    demo_terre.update(terre, hands_by_side, w, h)
                    demo_terre.render(frame, terre, w, h)

                if show_tetris:
                    if tetris is None:
                        tetris = demo_tetris.new_tetris(w, h)
                    demo_tetris.update(tetris, hands_by_side, w, h)
                    demo_tetris.render(frame, tetris, w, h)

                if show_pixel:
                    demo_pixel.render(frame, hands_by_side, w, h)

                if show_flame:
                    demo_flame.update(flame, hands_by_side, w, h)
                    demo_flame.render(frame, flame, w, h)

            # --- Intro : détection main ouverte + affichage ---
            if pending_intro is not None:
                any_open = any(_is_open_hand(lm)
                               for lm in (results.hand_landmarks or []))
                if any_open:
                    pending_intro["confirm"] += 1
                else:
                    pending_intro["confirm"] = 0
                pct = min(1.0, pending_intro["confirm"] / _CONFIRM_FRAMES)
                _draw_intro(frame, pending_intro, w, h, pct)
                if pending_intro["confirm"] >= _CONFIRM_FRAMES:
                    pending_intro = None

            # --- UI ---
            cv2.rectangle(frame, (0, h - 42), (w, h), (30, 30, 30), -1)
            cv2.putText(frame, status_text, (10, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)

            for row, (label, active) in enumerate([
                ("Filaments",  show_a),
                ("Bulles",     show_b),
                ("Physique",   show_c),
                ("Dessin",     show_d),
                ("Gestes",     show_f),
                ("Trainées",   show_g),
                ("Bulle eau",  show_h),
                ("Galaxie",    show_k),
                ("Puzzle",     show_l),
                ("Terre",      show_terre),
                ("Tetris",     show_tetris),
                ("Pixel",      show_pixel),
                ("Flammes",    show_flame),
            ]):
                color = (0, 220, 255) if active else (120, 120, 120)
                state = "ON" if active else "OFF"
                cv2.putText(frame, f"{label} : {state}", (10, 28 + row * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            cv2.putText(frame, "a:filaments b:bulles c:physique d:dessin e:flammes f:gestes g:trainées h:bulle k:galaxie l:puzzle p:pixel t:terre v:tetris i:landmarks j:fullscreen q:quitter",
                        (w - 1210, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

            # --- FPS ---
            if len(fps_times) >= 2:
                fps = (len(fps_times) - 1) / (fps_times[-1] - fps_times[0])
                fps_color = (0, 220, 0) if fps >= 25 else (0, 140, 255) if fps >= 15 else (0, 50, 255)
                cv2.putText(frame, f"FPS: {fps:.0f}", (w - 100, h - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, fps_color, 2)

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("a"):
                if show_a:
                    show_a = False
                    if pending_intro and pending_intro["key"] == "a":
                        pending_intro = None
                else:
                    show_a = True
                    pending_intro = _make_intro("a")
            elif key == ord("b"):
                if show_b:
                    show_b = False
                    bubbles, pops, score, game_start = [], [], 0, None
                    if pending_intro and pending_intro["key"] == "b":
                        pending_intro = None
                else:
                    show_b = True
                    bubbles    = [demo_b.new_bubble(w, h, [])]
                    for _ in range(BUBBLE_COUNT - 1):
                        bubbles.append(demo_b.new_bubble(w, h, bubbles))
                    pops, score, game_start = [], 0, time.time()
                    pending_intro = _make_intro("b")
            elif key == ord("c"):
                if show_c:
                    show_c = False
                    bubble_c = None
                    prev_index_c.clear()
                    if pending_intro and pending_intro["key"] == "c":
                        pending_intro = None
                else:
                    show_c = True
                    bubble_c = demo_c.new_bubble_c(w, h)
                    pending_intro = _make_intro("c")
            elif key == ord("d"):
                if show_d:
                    show_d = False
                    canvas = None
                    prev_draw_pos.clear()
                    if pending_intro and pending_intro["key"] == "d":
                        pending_intro = None
                else:
                    show_d = True
                    canvas = np.zeros((h, w, 3), dtype=np.uint8)
                    prev_draw_pos.clear()
                    erase_flash = 0
                    pending_intro = _make_intro("d")
            elif key == ord("p"):
                if show_pixel:
                    show_pixel = False
                    if pending_intro and pending_intro["key"] == "p":
                        pending_intro = None
                else:
                    show_pixel = True
                    pending_intro = _make_intro("p")
            elif key == ord("e"):
                if show_flame:
                    show_flame = False
                    flame = None
                    if pending_intro and pending_intro["key"] == "e":
                        pending_intro = None
                else:
                    show_flame = True
                    flame = demo_flame.new_flame()
                    pending_intro = _make_intro("e")
            elif key == ord("f"):
                if show_f:
                    show_f = False
                    gesture_history.clear()
                    if pending_intro and pending_intro["key"] == "f":
                        pending_intro = None
                else:
                    show_f = True
                    pending_intro = _make_intro("f")
            elif key == ord("g"):
                if show_g:
                    show_g = False
                    trail_history.clear()
                    if pending_intro and pending_intro["key"] == "g":
                        pending_intro = None
                else:
                    show_g = True
                    pending_intro = _make_intro("g")
            elif key == ord("h"):
                if show_h:
                    show_h = False
                    bubble_h = None
                    if pending_intro and pending_intro["key"] == "h":
                        pending_intro = None
                else:
                    show_h = True
                    bubble_h = demo_h.new_bubble_h()
                    pending_intro = _make_intro("h")
            elif key == ord("k"):
                if show_k:
                    show_k = False
                    galaxy = None
                    if pending_intro and pending_intro["key"] == "k":
                        pending_intro = None
                else:
                    show_k = True
                    galaxy = demo_k.new_galaxy()
                    pending_intro = _make_intro("k")
            elif key == ord("l"):
                if show_l:
                    show_l = False
                    puzzle = None
                    if pending_intro and pending_intro["key"] == "l":
                        pending_intro = None
                else:
                    show_l = True
                    pending_intro = _make_intro("l")
            elif key == ord("t"):
                if show_terre:
                    show_terre = False
                    terre = None
                    if pending_intro and pending_intro["key"] == "t":
                        pending_intro = None
                else:
                    show_terre = True
                    pending_intro = _make_intro("t")
            elif key == ord("v"):
                if show_tetris and tetris is not None and tetris["game_over"]:
                    tetris = demo_tetris.new_tetris(w, h)
                elif show_tetris:
                    show_tetris = False
                    tetris = None
                    if pending_intro and pending_intro["key"] == "v":
                        pending_intro = None
                else:
                    show_tetris = True
                    pending_intro = _make_intro("v")
            elif key == ord("i"):
                show_landmarks = not show_landmarks
            elif key == ord("j"):
                fullscreen = not fullscreen
                cv2.setWindowProperty(
                    WINDOW_NAME, cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL,
                )

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
