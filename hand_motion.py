import urllib.request
import os
import time
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

BaseOptions = mp_python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

# --- Modèle ---
MODEL_PATH = "hand_landmarker_full.task"
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)

MOVEMENT_THRESHOLD = 15  # pixels

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
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erreur : impossible d'ouvrir la webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    w_cam = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_cam = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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

    # --- Démo G ---
    show_g        = False
    trail_history = {}

    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
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
                draw_hand(frame, hand_landmarks, w, h)

                cx, cy = palm_center(hand_landmarks, w, h)
                current_positions[idx] = (cx, cy)
                cv2.circle(frame, (cx, cy), 7, (255, 0, 0), -1)

                if idx in prev_positions:
                    px, py = prev_positions[idx]
                    dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                    if dist > MOVEMENT_THRESHOLD:
                        status_text  = f"Mouvement detecte !  ({dist:.0f} px)"
                        status_color = (0, 80, 255)
                        cv2.arrowedLine(frame, (px, py), (cx, cy), (0, 0, 255), 2, tipLength=0.4)
                    else:
                        status_text  = "Main immobile"
                        status_color = (0, 220, 0)
                else:
                    status_text = "Main detectee"

                if results.handedness and idx < len(results.handedness):
                    side = results.handedness[idx][0].display_name
                    hands_by_side[side] = hand_landmarks

                if show_d and canvas is not None:
                    draw_color_idx, erased = demo_d.process(
                        frame, hand_landmarks, w, h, canvas,
                        prev_draw_pos, draw_color_idx, idx,
                    )
                    if erased:
                        erase_flash = 12

                if show_f:
                    demo_f.update_history(gesture_history, idx, hand_landmarks)

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

            # --- Rendu démos ---
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
                demo_f.render(frame, gesture_history, active_ids, current_positions, w, h)

            if show_g:
                demo_g.render(frame, trail_history, active_ids, w, h)

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
            ]):
                color = (0, 220, 255) if active else (120, 120, 120)
                state = "ON" if active else "OFF"
                cv2.putText(frame, f"{label} : {state}", (10, 28 + row * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            cv2.putText(frame, "a:filaments b:bulles c:physique d:dessin f:gestes g:trainées q:quitter",
                        (w - 720, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 180, 180), 1)

            cv2.imshow("Detection de mouvement de la main", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("a"):
                show_a = not show_a
            elif key == ord("b"):
                show_b = not show_b
                if show_b:
                    bubbles    = [demo_b.new_bubble(w, h, [])]
                    for _ in range(demo_b.BUBBLE_COUNT - 1):
                        bubbles.append(demo_b.new_bubble(w, h, bubbles))
                    pops, score, game_start = [], 0, time.time()
                else:
                    bubbles, pops, score, game_start = [], [], 0, None
            elif key == ord("c"):
                show_c = not show_c
                if show_c:
                    bubble_c = demo_c.new_bubble_c(w, h)
                else:
                    bubble_c = None
                    prev_index_c.clear()
            elif key == ord("d"):
                show_d = not show_d
                if show_d:
                    canvas = np.zeros((h, w, 3), dtype=np.uint8)
                    prev_draw_pos.clear()
                    erase_flash = 0
                else:
                    canvas = None
                    prev_draw_pos.clear()
            elif key == ord("f"):
                show_f = not show_f
                if not show_f:
                    gesture_history.clear()
            elif key == ord("g"):
                show_g = not show_g
                if not show_g:
                    trail_history.clear()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
