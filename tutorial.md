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

## 4. Lancer l'application

```bash
.venv/bin/python hand_motion.py
```

Au premier lancement, le modèle `hand_landmarker_full.task` est téléchargé automatiquement.

---

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| `a` | Activer / désactiver les filaments lumineux entre les deux mains |
| `b` | Activer / désactiver la démo bulles à éclater |
| `c` | Activer / désactiver la démo bulle physique |
| `d` | Activer / désactiver le dessin dans l'air |
| `q` | Quitter l'application |

---

## Architecture du script

| Fonction(s) | Rôle |
|---|---|
| `download_model()` | Téléchargement automatique du modèle `.task` au premier lancement |
| `enhance_frame()` | Prétraitement CLAHE pour compenser l'éclairage inégal |
| `draw_hand()` | Tracé des 21 landmarks et connexions de la main |
| `draw_filaments()` | Démo A — filaments néon entre les extrémités des deux mains |
| `new_bubble()` / `draw_bubble()` / `draw_pop()` | Démo B — bulle brillante à éclater par pincement |
| `new_bubble_c()` / `push_bubble_c()` / `update_bubble_c()` / `draw_bubble_c()` | Démo C — bulle avec physique poussée par l'index |
| `is_index_only()` / `is_open_hand()` / `draw_palette()` | Démo D — détection des gestes de dessin et effacement |
| `main()` | Boucle principale : capture webcam, détection MediaPipe, rendu, touches |

---

## Notes techniques

**Général**
- MediaPipe 0.10+ n'expose plus `mp.solutions` — la Tasks API (`mediapipe.tasks.python.vision.HandLandmarker`) et un fichier modèle `.task` séparé sont requis.
- Le modèle `.task` est exclu du dépôt git (`.gitignore`) et téléchargé automatiquement.
- Le mode `VIDEO` exploite la continuité temporelle entre frames pour un suivi plus stable qu'`IMAGE`.
- `MOVEMENT_THRESHOLD` (défaut : 15 px) — diminuer pour détecter des mouvements plus subtils.

**Démo A — Filaments (touche `a`)**
- Nécessite les **deux mains simultanément** visibles dans le champ de la webcam.
- Effet néon obtenu par fusion additive d'un calque GaussianBlur sur la frame.
- Une couleur distincte par paire de doigts (pouce, index, majeur, annulaire, auriculaire).

**Démo B — Bulles à éclater (touche `b`)**
- `BUBBLE_COUNT` bulles (défaut : 5) apparaissent simultanément, positionnées sans chevauchement.
- Pincer le **pouce** (landmark 4) et l'**index** (landmark 8) à moins de `PINCH_THRESHOLD` px sur une bulle pour l'éclater — une nouvelle bulle remplace immédiatement celle éclatée.
- La partie dure `GAME_DURATION` secondes (défaut : 30 s) : une barre de progression et un compteur de secondes sont affichés en haut au centre, le score en temps réel à droite.
- À la fin du temps, un écran de fin affiche le score final ; appuyer à nouveau sur `b` relance une partie.
- Paramètres : `PINCH_THRESHOLD`, `BUBBLE_RADIUS`, `BUBBLE_COUNT`, `GAME_DURATION`, `POP_DURATION`.

**Démo C — Bulle physique (touche `c`)**
- L'**index** (landmark 8) pousse la bulle : vitesse du doigt = impulsion appliquée à la bulle.
- La bulle rebondit sur les 4 bords et ralentit progressivement (`DAMPING = 0.97`).
- Un cercle translucide indique la zone de contact ; une flèche montre la vitesse courante.
- Paramètres : `PUSH_FACTOR`, `PUSH_RADIUS`, `DAMPING`, `MAX_VEL`.

**Démo D — Dessin dans l'air (touche `d`)**
- **Index seul étendu** (majeur/annulaire/auriculaire repliés) → mode dessin : une ligne est tracée entre la position courante et la précédente de l'index (landmark 8).
- **Main ouverte** (4 doigts étendus) → effacement complet du canvas avec un flash blanc animé.
- Une **palette de 6 couleurs** est affichée en haut à droite ; pointer l'index dessus change la couleur active (encadrée en blanc).
- Le dessin persiste sur un calque fusionné additivement sur la frame (zones noires = transparentes).
- Paramètres : `DRAW_COLORS` (liste de couleurs BGR), `DRAW_THICKNESS` (épaisseur du trait).
