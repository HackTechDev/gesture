# Tutoriel : Détection de mouvement de la main avec MediaPipe et OpenCV

## Prérequis

- Ubuntu
- Python 3.10
- Une webcam fonctionnelle

---

## 1. Créer le dossier du projet

```bash
mkdir -p ~/PYTHON/gesture
cd ~/PYTHON/gesture
```

## 2. Créer l'environnement virtuel

```bash
python3 -m venv .venv
```

## 3. Installer les dépendances

```bash
.venv/bin/pip install mediapipe opencv-python
```

## 4. Télécharger le modèle MediaPipe

```bash
curl -L -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

## 5. Créer le script `hand_motion.py`

```python
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

BaseOptions = mp_python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

MODEL_PATH = "hand_landmarker.task"
MOVEMENT_THRESHOLD = 15  # pixels

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


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
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erreur : impossible d'ouvrir la webcam.")
        return

    prev_positions = {}

    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
            )
            results = landmarker.detect(mp_image)

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
```

## 6. Lancer l'application

```bash
.venv/bin/python hand_motion.py
```

---

## Notes

- **MediaPipe 0.10+** n'expose plus `mp.solutions` — il faut utiliser la Tasks API (`mediapipe.tasks.python.vision.HandLandmarker`) et un fichier modèle `.task` séparé.
- Le modèle doit être dans le même dossier que le script, ou ajuster `MODEL_PATH` en conséquence.
- `MOVEMENT_THRESHOLD` (défaut : 15 px) contrôle la sensibilité — diminuer la valeur pour détecter des mouvements plus subtils.
- Appuyer sur `q` dans la fenêtre pour quitter proprement.
