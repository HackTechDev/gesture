#!/usr/bin/env python3
"""menu.py — Sélecteur de démos en mode terminal (TUI curses)."""
import curses
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEMOS = [
    ("a", "Filaments néon",      "2 mains",   "Filaments colorés entre les bouts de doigts"),
    ("b", "Bulles à éclater",    "1-2 mains", "Éclatez le max de bulles en 30 secondes"),
    ("c", "Bulle physique",      "1 main",    "Poussez la bulle avec l'index"),
    ("d", "Dessin dans l'air",   "1 main",    "Index dessine, main ouverte efface"),
    ("e", "Flammes",             "1-2 mains", "Main ouverte → flammes sur les doigts"),
    ("f", "Gestes",              "1-2 mains", "7 gestes reconnus dont Dr Strange"),
    ("g", "Traînées",            "1-2 mains", "Traînées lumineuses sur les 5 doigts"),
    ("h", "Bulle d'eau 3D",      "2 mains",   "Bulle modelable entre les paumes"),
    ("k", "Galaxie spirale 3D",  "2 mains",   "Galaxie 3D avec 1 500 étoiles"),
    ("l", "Puzzle 3×3",          "1 main",    "Reconstituez linux.jpg en 3 minutes"),
    ("n", "Corde et boule",      "2 mains",   "La boule glisse et rebondit sur la corde"),
    ("p", "Pixelisation",        "2 mains",   "Zone vidéo pixelisée entre les doigts"),
    ("t", "Globe terrestre 3D",  "2 mains",   "Texture 2K, rotation par les mains"),
    ("v", "Tetris",              "1 main",    "Index déplace, poing pour chute rapide"),
]

_NAMES = {key: name for key, name, *_ in DEMOS}

# Paires de couleurs
_C_TITLE   = 1   # cyan gras
_C_ACTIVE  = 2   # vert — démo sélectionnée
_C_NORMAL  = 3   # blanc — texte courant
_C_HEADER  = 4   # jaune — en-têtes / statut
_C_CURSOR  = 5   # noir sur cyan — ligne curseur
_C_DIM     = 6   # gris — aide


def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(_C_TITLE,  curses.COLOR_CYAN,   -1)
    curses.init_pair(_C_ACTIVE, curses.COLOR_GREEN,  -1)
    curses.init_pair(_C_NORMAL, curses.COLOR_WHITE,  -1)
    curses.init_pair(_C_HEADER, curses.COLOR_YELLOW, -1)
    curses.init_pair(_C_CURSOR, curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(_C_DIM,    curses.COLOR_WHITE,  -1)


def _draw(stdscr, cursor, selected):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    def safe_addstr(y, x, text, attr=0):
        if y < 0 or y >= rows:
            return
        text = text[:max(0, cols - x - 1)]
        try:
            stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    # ── Titre ────────────────────────────────────────────────────────────────
    title = "  GESTURE RECOGNITION  —  Sélecteur de démos  "
    safe_addstr(0, max(0, (cols - len(title)) // 2), title,
                curses.color_pair(_C_TITLE) | curses.A_BOLD)
    safe_addstr(1, 0, "─" * (cols - 1))

    # ── En-têtes colonnes ────────────────────────────────────────────────────
    header = f"  {'':3}  {'':2}   {'Démo':<22}  {'Mains':<11}  Description"
    safe_addstr(2, 0, header, curses.color_pair(_C_HEADER) | curses.A_BOLD)
    safe_addstr(3, 0, "─" * (cols - 1))

    # ── Liste démos ──────────────────────────────────────────────────────────
    list_rows = rows - 8
    scroll    = max(0, cursor - list_rows + 1)

    for i, (key, name, hands, desc) in enumerate(DEMOS):
        row = 4 + i - scroll
        if row < 4 or row >= rows - 4:
            continue
        check = "●" if key in selected else "○"
        line  = f"  {check}   {key}   {name:<22}  {hands:<11}  {desc}"
        if i == cursor:
            safe_addstr(row, 0, " " * (cols - 1), curses.color_pair(_C_CURSOR) | curses.A_BOLD)
            safe_addstr(row, 0, line,              curses.color_pair(_C_CURSOR) | curses.A_BOLD)
        elif key in selected:
            safe_addstr(row, 0, line, curses.color_pair(_C_ACTIVE) | curses.A_BOLD)
        else:
            safe_addstr(row, 0, line, curses.color_pair(_C_NORMAL))

    # ── Pied de page ─────────────────────────────────────────────────────────
    fy = rows - 4
    safe_addstr(fy, 0, "─" * (cols - 1))

    if selected:
        order  = [k for k, *_ in DEMOS if k in selected]
        status = "  Lancement : " + "  +  ".join(
            f"{k} ({_NAMES[k]})" for k in order
        )
        safe_addstr(fy + 1, 0, status, curses.color_pair(_C_HEADER))
    else:
        cur_key  = DEMOS[cursor][0]
        cur_name = _NAMES[cur_key]
        safe_addstr(fy + 1, 0, f"  Lancement : {cur_key} ({cur_name})",
                    curses.color_pair(_C_HEADER))

    shortcuts = ("  ENTRÉE Lancer    ESPACE Multi-sélection    "
                 "A Tout / Rien    ↑↓ Naviguer    Q Quitter")
    safe_addstr(fy + 2, 0, shortcuts,
                curses.color_pair(_C_DIM) | curses.A_DIM)

    stdscr.refresh()


def _run_tui(stdscr):
    curses.curs_set(0)
    _init_colors()

    selected = set()
    cursor   = 0

    while True:
        _draw(stdscr, cursor, selected)
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = (cursor - 1) % len(DEMOS)
        elif key == curses.KEY_DOWN:
            cursor = (cursor + 1) % len(DEMOS)
        elif key == ord(" "):
            demo_key = DEMOS[cursor][0]
            if demo_key in selected:
                selected.discard(demo_key)
            else:
                selected.add(demo_key)
        elif key in (ord("a"), ord("A")):
            if len(selected) == len(DEMOS):
                selected.clear()
            else:
                selected = {d[0] for d in DEMOS}
        elif key in (curses.KEY_ENTER, 10, 13):
            return selected if selected else {DEMOS[cursor][0]}
        elif key in (ord("q"), ord("Q"), 27):
            return None

    return None


def main():
    import hand_motion

    while True:
        result = curses.wrapper(_run_tui)

        if result is None:
            break

        hand_motion.main(initial_demos=result)


if __name__ == "__main__":
    main()
