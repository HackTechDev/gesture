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

Le code source complet se trouve dans `hand_motion.py` à la racine du projet.
Le modèle MediaPipe (`hand_landmarker_full.task`) est téléchargé automatiquement au premier lancement.

### Architecture du script

| Section | Rôle |
|---|---|
| Constantes | Seuils, rayons, physique — tous ajustables en tête de fichier |
| `download_model()` | Téléchargement automatique du modèle `.task` |
| `enhance_frame()` | Prétraitement CLAHE (éclairage) |
| `draw_hand()` | Tracé des landmarks et connexions |
| `draw_filaments()` | Démo A — filaments néon entre les deux mains |
| `new_bubble()` / `draw_bubble()` / `draw_pop()` | Démo B — bulle à éclater |
| `new_bubble_c()` / `push_bubble_c()` / `update_bubble_c()` / `draw_bubble_c()` | Démo C — bulle physique |
| `main()` | Boucle principale : capture, détection, rendu, gestion des touches |

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
| `c` | Activer / désactiver la démo physique (pousser la bulle avec l'index) |
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
- Paramètres ajustables démo B : `PINCH_THRESHOLD` (sensibilité du pincement), `BUBBLE_RADIUS` (taille), `POP_DURATION` (durée de l'animation en frames).
- La démo C utilise l'**index** (landmark 8) pour pousser une bulle avec physique : vitesse de l'index = vitesse de la bulle. La bulle rebondit sur les 4 bords et ralentit progressivement (amortissement `DAMPING = 0.97`).
- Un cercle translucide indique la zone de contact autour de la bulle (démo C) ; une flèche montre sa vitesse et direction courantes.
- Paramètres ajustables démo C : `PUSH_FACTOR` (intensité de la poussée), `PUSH_RADIUS` (zone de contact), `DAMPING` (friction), `MAX_VEL` (vitesse maximale).
