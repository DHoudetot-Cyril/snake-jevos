<h1 align="center">🐍 Snake × jevos</h1>

<p align="center">
  <strong>Un Snake dans le navigateur, jouable à la main ou piloté par un petit modèle de décision<br/>
  qui tourne sur le processeur (~48 ms par coup), avec chaque décision affichée en direct.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3-blue?logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/IA-locale_sur_CPU-2F81F7" alt="IA locale sur CPU">
  <img src="https://img.shields.io/badge/dépendances-bibliothèque_standard-success" alt="Bibliothèque standard uniquement">
  <img src="https://img.shields.io/badge/projet-personnel-lightgrey" alt="Projet personnel">
</p>

---

Le jeu peut être piloté par **jevos**
([feder-cr/jev](https://github.com/feder-cr/jev)), un modèle de décision open source (MIT)
qui répond à des questions oui/non en quelques dizaines de millisecondes, sur le processeur.

![jevos aux commandes : le plateau, les probabilités des 4 directions et le journal des décisions en direct](docs/screenshot-v2.png)

## 🚀 Installer et lancer

Prérequis : Linux x64, Python 3, `curl`, `unzip`.

```bash
./setup.sh    # télécharge jevos-v5 (~650 Mo) dans jevos/  (fait automatiquement par start.sh)
./start.sh
```

Puis ouvrir http://127.0.0.1:8080

- Flèches / ZQSD : jouer · Espace : pause · J ou bouton « Jevos joue » : jevos prend la main
- Toucher une flèche pendant que jevos joue = reprise en main
- À droite : chaque décision en direct (cliquer une ligne pour voir le texte envoyé et les réponses)

`start.sh` lance jevos sur le port 8018 (modifiable : `JEVOS_PORT=8017 ./start.sh` réutilise un jevos déjà lancé).

## 🧠 Fonctionnement (mode « assisté »)

```mermaid
flowchart LR
    G["🎮 Jeu dans le navigateur<br/>web/index.html"] -->|"POST /api/decide<br/>état de la grille"| S["🐍 server.py<br/>Python, bibliothèque standard"]
    S --> F["🔎 Analyse de chaque direction<br/>mortelle · pomme · piège"]
    F -->|"8 questions oui/non<br/>en 1 requête"| J["🧠 jevos-v5<br/>modèle de décision sur CPU"]
    J -->|"P(sûr) et P(pomme)<br/>par direction"| SC["🧮 score = P(sûr)² × (0,4 + 0,6 × P(pomme))"]
    SC -->|"meilleure direction<br/>~48 ms par coup"| G
```

À chaque pas, `server.py` :

1. analyse la grille et décrit chaque direction en texte : mortelle (mur / corps), mange la pomme,
   rapproche ou éloigne de la pomme, piège (pas assez d'espace libre ensuite) ;
2. pose **8 questions oui/non** à jevos en une seule requête : pour chaque direction,
   « ce coup est-il sûr ? » et « rapproche-t-il de la pomme ? » ;
3. calcule `score = P(sûr)² × (0,4 + 0,6 × P(pomme))` et joue la direction au meilleur score.

jevos ne lit pas la grille brute (testé : 2/6 bonnes réponses, il répond « up » à chaque fois),
c'est pourquoi le code lui fournit des faits sur chaque direction.

## 📊 Mesures (grille 16×16, CPU 16 threads)

| Version des questions | Score moyen | Latence médiane |
|---|---|---|
| 1 question « meilleur coup ? » par direction | 15,8 (4 parties) | ~56 ms |
| 2 questions combinées (actuelle) | **54,6** (5 parties) | ~48 ms |

Avec la version actuelle, aucune mort ne vient d'un choix mortel : le serpent meurt quand il s'est
enfermé dans son propre corps (la détection de piège ne regarde qu'un coup à l'avance).

```bash
python3 tools/simulate.py 5      # rejoue 5 parties sans navigateur
```

## 📁 Dossiers

- `setup.sh` : télécharge jevos dans `jevos/` (non versionné, trop lourd pour Git)
- `start.sh` : lance jevos puis le jeu
- `web/index.html` : le jeu
- `server.py` : serveur web + lien avec jevos (bibliothèque standard Python uniquement)

## 👤 Auteur

**Cyril D'Houdetot** · [GitHub](https://github.com/DHoudetot-Cyril)
