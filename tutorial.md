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
.venv/bin/pip install mediapipe opencv-python numpy
```

> `numpy` est utilisé pour les calques de glow (filaments) et les étincelles de la démo bulles.

## 4. Créer le script `hand_motion.py`

Le modèle MediaPipe (`hand_landmarker_full.task`) est téléchargé automatiquement au premier lancement.

```python
import urllib.request
import os
import cv2
import numpy as np
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

# Extrémités des doigts : pouce, index, majeur, annulaire, auriculaire
FINGERTIPS = [4, 8, 12, 16, 20]

# Couleur (BGR) de chaque filament
FILAMENT_COLORS = [
    (255, 180,   0),  # cyan    — pouce
    (0,   255, 180),  # vert    — index
    (180,   0, 255),  # violet  — majeur
    (0,   200, 255),  # jaune   — annulaire
    (255,  50, 150),  # rose    — auriculaire
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


def draw_filaments(frame, left_lm, right_lm, w, h):
    """Dessine des filaments lumineux entre les extrémités des deux mains."""
    glow = np.zeros_like(frame, dtype=np.uint8)

    for tip_idx, color in zip(FINGERTIPS, FILAMENT_COLORS):
        lx, ly = int(left_lm[tip_idx].x * w),  int(left_lm[tip_idx].y * h)
        rx, ry = int(right_lm[tip_idx].x * w), int(right_lm[tip_idx].y * h)

        # Halo extérieur large et diffus
        cv2.line(glow, (lx, ly), (rx, ry), color, 9)
        # Halo intermédiaire plus lumineux
        cv2.line(glow, (lx, ly), (rx, ry), color, 4)

    # Flou gaussien → effet néon/glow
    glow = cv2.GaussianBlur(glow, (21, 21), 0)

    # Fusion additive avec la frame
    frame[:] = cv2.add(frame, glow)

    # Noyau blanc fin par-dessus pour l'éclat central
    for tip_idx, color in zip(FINGERTIPS, FILAMENT_COLORS):
        lx, ly = int(left_lm[tip_idx].x * w),  int(left_lm[tip_idx].y * h)
        rx, ry = int(right_lm[tip_idx].x * w), int(right_lm[tip_idx].y * h)
        cv2.line(frame, (lx, ly), (rx, ry), (255, 255, 255), 1)

        # Petit halo aux extrémités
        for px, py in [(lx, ly), (rx, ry)]:
            cv2.circle(frame, (px, py), 6, color, -1)
            cv2.circle(frame, (px, py), 3, (255, 255, 255), -1)


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

    prev_positions = {}
    show_filaments = False

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

            status_text = "Aucune main detectee"
            status_color = (200, 200, 200)
            current_positions = {}

            # Identifier main gauche et main droite
            hands_by_side = {}  # "Left" | "Right" -> landmarks
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

                # Récupérer le côté détecté par MediaPipe
                if results.handedness and idx < len(results.handedness):
                    side = results.handedness[idx][0].display_name  # "Left" ou "Right"
                    hands_by_side[side] = hand_landmarks

            prev_positions = current_positions

            # Filaments si les deux mains sont présentes et mode actif
            if show_filaments and "Left" in hands_by_side and "Right" in hands_by_side:
                draw_filaments(frame, hands_by_side["Left"], hands_by_side["Right"], w, h)

            # Bandeau d'état
            cv2.rectangle(frame, (0, h - 42), (w, h), (30, 30, 30), -1)
            cv2.putText(frame, status_text, (10, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)

            # Indicateur filaments
            fil_label = "Filaments : ON" if show_filaments else "Filaments : OFF"
            fil_color = (0, 220, 255) if show_filaments else (120, 120, 120)
            cv2.putText(frame, fil_label, (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, fil_color, 2)
            cv2.putText(frame, "a : filaments  |  q : quitter", (w - 310, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

            cv2.imshow("Detection de mouvement de la main", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("a"):
                show_filaments = not show_filaments

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
```

## 5. Lancer l'application

```bash
.venv/bin/python hand_motion.py
```

Au premier lancement, le modèle est téléchargé automatiquement dans `hand_landmarker_full.task`.

---

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| `a` | Activer / désactiver les filaments lumineux |
| `b` | Activer / désactiver la démo bulles (pincer avec pouce + index pour éclater) |
| `q` | Quitter l'application |

## Notes

- **MediaPipe 0.10+** n'expose plus `mp.solutions` — il faut utiliser la Tasks API (`mediapipe.tasks.python.vision.HandLandmarker`) et un fichier modèle `.task` séparé.
- Le modèle `.task` est exclu du dépôt git (voir `.gitignore`) car il est téléchargé automatiquement.
- `MOVEMENT_THRESHOLD` (défaut : 15 px) contrôle la sensibilité — diminuer la valeur pour détecter des mouvements plus subtils.
- Le mode `VIDEO` (vs `IMAGE`) exploite la continuité temporelle pour un suivi plus stable.
- Le prétraitement CLAHE améliore la détection en cas d'éclairage inégal.
- Les filaments nécessitent que les **deux mains soient simultanément visibles** dans le champ de la webcam.
- L'effet lumineux est obtenu par fusion additive d'un calque flou (GaussianBlur) sur la frame principale.
- La démo bulles est indépendante des filaments — les deux modes peuvent être actifs simultanément.
- Pour éclater une bulle : rapprocher le **pouce** (landmark 4) et l'**index** (landmark 8) à moins de 50 px, le point de pincement doit se trouver dans la bulle. Une nouvelle bulle apparaît automatiquement après l'animation d'éclatement.
- Paramètres ajustables : `PINCH_THRESHOLD` (sensibilité du pincement), `BUBBLE_RADIUS` (taille), `POP_DURATION` (durée de l'animation en frames).
