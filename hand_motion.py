import urllib.request
import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

BaseOptions = mp_python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

# --- Modèle ---
MODEL_PATH = "hand_landmarker_full.task"
MODEL_URL = (
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


def download_model():
    if not os.path.exists(MODEL_PATH):
        print(f"Téléchargement du modèle vers {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Modèle téléchargé.")


def enhance_frame(frame):
    """Égalisation CLAHE sur le canal L pour compenser l'éclairage inégal."""
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def draw_hand(frame, hand_landmarks, w, h):
    for start, end in HAND_CONNECTIONS:
        x1, y1 = int(hand_landmarks[start].x * w), int(hand_landmarks[start].y * h)
        x2, y2 = int(hand_landmarks[end].x * w), int(hand_landmarks[end].y * h)
        cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
    for lm in hand_landmarks:
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (255, 255, 255), -1)


def palm_center(hand_landmarks, w, h):
    lm = hand_landmarks[9]  # base du majeur
    return int(lm.x * w), int(lm.y * h)


def main():
    download_model()

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.VIDEO,   # suivi temporel activé
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erreur : impossible d'ouvrir la webcam.")
        return

    # Qualité de capture
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    prev_positions = {}

    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            # Prétraitement éclairage
            enhanced = enhance_frame(frame)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB),
            )
            results = landmarker.detect_for_video(mp_image, timestamp_ms)

            status_text = "Aucune main detectee"
            status_color = (200, 200, 200)
            current_positions = {}

            for idx, hand_landmarks in enumerate(results.hand_landmarks or []):
                draw_hand(frame, hand_landmarks, w, h)

                cx, cy = palm_center(hand_landmarks, w, h)
                current_positions[idx] = (cx, cy)
                cv2.circle(frame, (cx, cy), 7, (255, 0, 0), -1)

                if idx in prev_positions:
                    px, py = prev_positions[idx]
                    dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                    if dist > MOVEMENT_THRESHOLD:
                        status_text = f"Mouvement detecte !  ({dist:.0f} px)"
                        status_color = (0, 80, 255)
                        cv2.arrowedLine(frame, (px, py), (cx, cy), (0, 0, 255), 2, tipLength=0.4)
                    else:
                        status_text = "Main immobile"
                        status_color = (0, 220, 0)
                else:
                    status_text = "Main detectee"

            prev_positions = current_positions

            # Bandeau d'état
            cv2.rectangle(frame, (0, h - 42), (w, h), (30, 30, 30), -1)
            cv2.putText(frame, status_text, (10, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)
            cv2.putText(frame, "q : quitter", (w - 105, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

            cv2.imshow("Detection de mouvement de la main", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
