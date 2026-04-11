# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Python 3.10 with a local `.venv`. Always activate before running scripts:

```bash
source .venv/bin/activate
python your_script.py
```

Install new dependencies into the venv:

```bash
.venv/bin/pip install <package>
```

## Project Purpose

Gesture recognition system using a webcam. Core stack:

- **MediaPipe** (`mediapipe`) — hand landmark detection (21 keypoints per hand)
- **OpenCV** (`cv2`, including `opencv-contrib`) — webcam capture, frame processing, drawing overlays
- **NumPy** — landmark coordinate math and transformations
- **SoundDevice** — audio feedback triggered by gestures
- **Pillow / Matplotlib** — image utilities and optional visualization

## Key Architectural Notes

MediaPipe's `Hands` solution returns normalized landmark coordinates (0–1 range) relative to the frame. Convert to pixel coords by multiplying by `frame.shape[1]` (width) and `frame.shape[0]` (height).

The typical pipeline:
1. Capture frame with `cv2.VideoCapture`
2. Convert BGR→RGB before passing to MediaPipe (`cv2.cvtColor`)
3. Process landmarks from `results.multi_hand_landmarks`
4. Map landmark geometry to gesture labels
5. Trigger action (audio via `sounddevice`, visual overlay via OpenCV)

OpenCV's `imshow` / `waitKey` loop drives the real-time display; `waitKey(1)` is the standard polling interval for webcam loops.

## Workflow Git

Après chaque modification significative, fais un commit git avec :
- Un titre court et descriptif (format : `type(scope): description`)
  - Types valides : `feat`, `fix`, `refactor`, `docs`, `chore`, `style`
- Un corps de message détaillant les changements effectués

Exemple :
```
feat(auth): ajouter la validation du token JWT

- Ajout de la vérification de l'expiration du token
- Gestion des erreurs 401 avec message explicite
- Mise à jour des tests unitaires correspondants
```

