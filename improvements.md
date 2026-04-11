# Améliorations possibles

## Démo B — Bulles à éclater

- [x] Plusieurs bulles simultanées avec un compteur de score
- [x] Minuterie : éclater le maximum de bulles en X secondes
- [ ] Bulles qui bougent aléatoirement (cibles mouvantes)

## Démo C — Bulle physique

- [ ] Gravité permanente (la bulle tombe si on ne la pousse plus)
- [ ] Plusieurs bulles qui se percutent entre elles (collisions inter-bulles)
- [ ] Obstacles fixes sur l'écran à éviter

## Nouvelles démos

- [ ] Démo D — Dessin dans l'air : tracer avec l'index, effacer en ouvrant la main
- [ ] Démo E — Contrôle de volume : écarter/rapprocher pouce et index pour simuler un curseur
- [ ] Démo F — Reconnaissance de gestes : détecter des formes précises (pouce levé, poing, victoire) et afficher leur nom

## Qualité visuelle

- [ ] Fond noir ou flou cinématique derrière les landmarks pour mieux les isoler
- [ ] Traînées de mouvement (motion trail) sur les doigts
- [ ] Particules qui suivent les extrémités des doigts en permanence

## Architecture

- [ ] Séparer chaque démo dans son propre fichier (`demo_a.py`, `demo_b.py`…) et les importer dans `hand_motion.py`
- [ ] Fichier `config.py` centralisé pour tous les paramètres ajustables
- [ ] Affichage du FPS en temps réel pour mesurer l'impact des démos
