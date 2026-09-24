# Ménage

Gestion du ménage à plusieurs, pensée pour le téléphone. Toute la navigation
passe par des tuiles, deux par étage, et une tâche se valide d'un seul appui.

## Mise en service

```bash
git clone https://github.com/apierrr/menage.git
cd menage
docker compose up -d --build
```

L'app répond sur http://127.0.0.1:8000. Les données (base SQLite et clé de
signature du cookie) sont écrites dans `./data`, créé au premier démarrage.

Réglages facultatifs, dans un fichier `.env` à côté du `docker-compose.yml` :

| Variable            | Défaut          | Rôle                                                   |
| ------------------- | --------------- | ------------------------------------------------------ |
| `PORT`              | `8000`          | Port d'écoute, dans le container comme sur l'hôte      |
| `CONTAINER_NAME`    | `menage`        | Nom du container (utile pour en faire tourner deux)    |
| `TZ`                | `Europe/Paris`  | Fuseau des décomptes en jours                          |
| `SHARE_WINDOW_DAYS` | `90`            | Fenêtre de la jauge des tâches ponctuelles             |
| `SECRET_KEY`        | générée         | Clé du cookie ; sinon créée dans `data/secret.key`     |

Sur le téléphone, « Ajouter à l'écran d'accueil » installe l'application en
plein écran (manifeste PWA + icônes fournis).

### Exposer l'app

**L'app n'a pas d'authentification.** Le profil choisi est mémorisé dans un
cookie signé, mais n'importe qui atteignant l'URL peut choisir n'importe quel
profil, et créer, modifier ou supprimer tuiles, profils et historique. Par
défaut, le port n'est donc publié que sur `127.0.0.1`.

Pour l'ouvrir au-delà de la machine, mettre devant un contrôle d'accès
(Cloudflare Access, authentification du reverse proxy, VPN…). Un sous-domaine
difficile à deviner n'en est pas un : les enregistrements DNS se découvrent.

Derrière un reverse proxy ou un tunnel sur un réseau Docker partagé, un
`docker-compose.override.yml` (ignoré par git) retire le port publié :

```yaml
services:
  menage:
    ports: !reset []
    networks:
      - proxy

networks:
  proxy:
    external: true
```

Le proxy joint alors `http://<CONTAINER_NAME>:<PORT>`.

## Parcours

1. **Première ouverture** — combien de personnes, puis une tuile par personne
   (prénom + couleur, via le crayon en bas de la tuile).
2. **Choix du profil** — l'identité est retenue dans un cookie signé d'un an.
   On en change depuis le récapitulatif (sigle en haut à gauche).
3. **Accueil** — deux tuiles pleine largeur : *Régulière* et *Ponctuelle*.
4. **Dans un menu** — le pinceau en haut à droite ouvre le mode édition :
   croix de suppression (avec confirmation), crayon de réglages, appui
   maintenu pour réordonner, et menu flottant en bas pour créer une tuile ou
   un sous-menu.
5. **Récapitulatif** — le sigle en haut à gauche ouvre les indicateurs globaux
   et individuels, d'où l'on atteint l'historique des validations et le
   changement de profil.

## Les règles

**Décompte** — en jours pleins, heure de Paris. Un compteur perd un jour au
passage de minuit, pas 24 h après la validation. Passé l'échéance il devient
négatif et la tuile passe au rouge. Le rouge est réservé à cet état : il est
absent du sélecteur de couleurs et refusé par l'API.

**Couleurs** — dans la section régulière, rien n'a de couleur choisie. Une
tâche porte celle de la personne qui doit la faire, et en change donc à chaque
rotation : ni sélecteur de couleur, ni étiquette avec le prénom — la couleur
suffit. Quand la tâche passe en retard, la tuile devient rouge et un liseré sur
le bord gauche rappelle de qui il s'agit.

Un sous-menu régulier se partage entre les couleurs des tâches qu'il contient,
au prorata et à n'importe quelle profondeur : trois tâches dont une à moi, c'est
un tiers de ma couleur et deux tiers de celle de l'autre. Un sous-menu qui en
contient un autre compte aussi les tâches de celui-ci. Ma part est toujours à
gauche. Vide, il reste gris ; en retard, le rouge reprend le dessus. Si les
bandes n'ont pas la même clarté, le texte prend un léger halo pour rester
lisible d'une bande à l'autre.

Les tâches ponctuelles et leurs sous-menus, qui n'ont pas de responsable,
gardent leur propre couleur.

**Le compteur repart à zéro** — valider veut dire « c'est fait », pas « ajoute
une période ». Dès que quelqu'un fait une tâche hebdomadaire, elle est à refaire
dans sept jours pleins, qu'elle ait été faite en avance, à l'heure ou avec trois
semaines de retard. L'échéance ne dépend donc que de la dernière validation, et
jamais de l'échéance précédente.

Il en découle que rappuyer ne déplace rien. Un second appui sur une tâche
régulière déjà validée dans la journée n'enregistre pas de doublon, ne fait pas
tourner le responsable et laisse l'échéance en place ; la tuile affiche
« ✓ faite » jusqu'au lendemain et le message le rappelle. Si c'est *quelqu'un
d'autre* qui la valide le même jour, sa validation compte pour lui — mais
l'échéance, elle, n'est calculée qu'une fois. Les tâches ponctuelles se
valident autant de fois qu'on les fait.

**Rythme quotidien** — une tâche « tous les jours » est à faire dès le jour
de sa création ; validée, elle revient le lendemain.

**Personnes concernées** — chaque tâche peut être réservée à certains profils.
Rien de coché (ou tout le monde) : la tâche concerne tout le monde, y compris
les profils ajoutés plus tard. Sinon, la rotation ne tourne qu'entre ces
personnes (une seule : c'est toujours elle), et la jauge d'une tâche
ponctuelle ne compare qu'elles. N'importe qui peut quand même valider. Décocher
le responsable passe la main au suivant ; si toutes les personnes cochées sont
supprimées, la tâche revient à tout le monde. Stocké dans `tile_members`.

**Rythme mensuel** — on mémorise le jour *voulu* (l'ancrage). Une tâche calée
sur le 31 tombe au 28 février (29 les années bissextiles) puis revient au 31
mars. Faite un autre jour que celui prévu, c'est ce jour-là qui devient la
nouvelle référence.

**Rotation** — réglable par tâche :

- *Équité* (défaut) — revient à qui l'a faite le moins souvent ; à égalité, à
  qui l'a faite il y a le plus longtemps, puis l'ordre des profils. Quelqu'un
  en retard sur une tâche peut donc l'enchaîner, le temps de rattraper.
- *Chacun son tour* — la personne suivante dans l'ordre des profils.

À la création, on choisit qui commence ; la rotation prend le relais à la
première validation. Un profil ajouté plus tard est crédité du minimum
constaté sur chaque tâche, pour ne pas hériter de tout d'un coup.

**Tâches ponctuelles** — la barre montre la répartition des validations sur
une fenêtre glissante de 90 jours (`SHARE_WINDOW_DAYS`). Vert = toi (toujours
à gauche), gris = les autres. Le trait blanc marque le **partage égal** : 50 %
à deux, 33 % à trois. Si le vert le dépasse, tu en fais plus que ta part.

Sous la barre, des **nombres de fois** plutôt que des pourcentages — à 3 contre
2, un « 60 % / 40 % » ferait passer un écart d'une seule fois pour un gouffre —
et un verdict : *à l'équilibre*, *1 de plus*, *4 de moins*. Il compare ton
compteur à la moyenne des autres.

**Tri de la page Régulière** — tes tâches d'abord, la plus urgente en tête.
Le sélecteur *Ordre* en haut permet de basculer sur ton propre classement
(celui du glisser-déposer).

**Annulation** — après une validation, un message propose « Annuler » pendant
quelques secondes ; l'échéance et le responsable précédents sont restaurés à
l'identique.

**Historique** — le récapitulatif mène au journal des validations, groupées par
jour. Chacune peut être supprimée. Supprimer la *dernière* validation d'une
tuile restaure son échéance et son responsable d'avant ; supprimer une
validation plus ancienne la retire seulement des compteurs, sans recalculer
l'échéance en cours (la chaîne des reports serait invérifiable). La
confirmation le dit explicitement.

## Piège connu : les bloqueurs de publicité

Les classes CSS de l'indicateur s'appellent `tally-*` et **ne doivent pas**
être renommées en `share-*`. La liste « EasyList Social Widgets », activable
dans uBlock Origin, contient les filtres nus `##.share-bar` et
`##.share-legend` : la jauge et les chiffres étaient masqués par le navigateur,
alors que le panneau qui les contient restait visible — d'où un encart vide
particulièrement déroutant à diagnostiquer.

Avant d'ajouter une classe, un identifiant ou une route d'API, vérifier qu'elle
n'est pas ciblée. Les 115 classes actuelles ont été croisées avec EasyList,
EasyPrivacy, les filtres uBlock et EasyList Social : aucune n'est visée. Le
script de contrôle est dans `tests/check_classes.py`.

## Architecture

Un seul container, construit en deux étages :

- `web/` — React + Vite (moteur de tuiles, glisser-déposer dnd-kit), compilé
  en statique.
- `app/` — FastAPI + SQLAlchemy + SQLite, sert l'API sous `/api` et le front
  pour tout le reste.

Points d'entrée utiles :

| Fichier              | Rôle                                                     |
| -------------------- | -------------------------------------------------------- |
| `app/scheduling.py`  | Moteur de dates et de rotation (fonctions pures)          |
| `app/service.py`     | Lecture des tuiles, validation, statistiques              |
| `app/models.py`      | Modèle de données — une seule table porte la navigation   |
| `web/src/components/TileGrid.jsx` | Grille et glisser-déposer                   |
| `web/src/components/TileCard.jsx` | Rendu d'une tuile selon son type            |

Les données vivent dans `./data` (base SQLite + clé de signature du cookie).
C'est le seul répertoire à sauvegarder.

## Tests

Moteur de dates et de rotation, sans dépendance :

```bash
python3 -m tests.test_scheduling
```

Parcours complet sur l'API, dans un container jetable :

```bash
docker build -t menage-test .
docker run -d --name menage-test -e DATA_DIR=/tmp/mt \
  -e DATABASE_URL=sqlite:////tmp/mt/test.db menage-test
docker exec -i menage-test python - < tests/test_api.py
docker rm -f menage-test
```
