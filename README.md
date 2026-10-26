# L'Essentiel — l'actualité sans le bruit

Un lecteur d'actualités en **HTML / CSS / JavaScript**, avec 7 rubriques, des résumés courts, un accès aux sources, une recherche et des favoris (stockés localement). **Pas de vidéos, pas de publicité, pas de backend payant obligatoire.** L'IA est facultative et utilise une clé privée OpenRouter.

## Démarrage local

Il faut **Python 3.10+** et une connexion Internet. Aucune dépendance à installer.

```bash
python -m scripts.update_news
python -m http.server 8000
```

Ouvrir <http://localhost:8000>. Ne pas ouvrir `index.html` directement en `file://` : le navigateur bloque alors le chargement du JSON.

## Mise en ligne gratuite sur GitHub Pages

1. Créer un dépôt GitHub (public ou compatible avec votre offre GitHub Pages).
2. Copier **tous les fichiers, y compris le dossier `.github/workflows`**, sur la branche `main`.
3. Dans **Settings → Pages → Build and deployment**, choisir **Source: GitHub Actions**.
4. Ouvrir **Actions → Actualiser les actualités → Run workflow** pour déclencher le premier briefing (sinon il s'exécutera à la prochaine heure planifiée).
5. L'adresse du site sera indiquée dans le déploiement GitHub Pages (pour un dépôt public classique : `https://VOTRE-COMPTE.github.io/NOM-DU-DEPOT/`).

Le workflow récupère les RSS et publie directement le site (sans commit automatique). Il est planifié **une fois par heure**, avec une heure qui peut dériver selon la charge de GitHub Actions. Le bouton de rafraîchissement de l'interface recharge le JSON disponible sur le site ; il ne déclenche pas une nouvelle exécution GitHub Actions.

## Sources et contenus

Sources RSS configurées dans `scripts/update_news.py` : RFI, France 24, franceinfo, Hespress français, Le Courrier de l'Atlas, 01net, Numerama, Blog du Modérateur, Clubic. Chaque article renvoie à sa source.

Sans clé OpenRouter, les textes courts proviennent des **descriptions RSS des éditeurs**, limitées à environ 190 caractères. Avec clé, une synthèse IA des extraits RSS est réalisée pour **une actualité prioritaire par rubrique** (jusqu'à sept articles en une seule requête), puis vérifiée sommairement (longueur et chiffres nouveaux). Chaque carte générée par l'IA affiche « Synthèse IA » ; les autres restent RSS. L'IA ne lit **pas** l'article complet et ne vérifie pas les faits indépendamment. Vérifiez toujours la source originale.

La pertinence est basée sur une sélection de sources, des filtres thématiques, un score de fraîcheur, quelques mots-clés de signal et un dédoublonnage approximatif. Ce filtrage est imparfait : des sujets importants peuvent passer à travers et les sources peuvent avoir des angles différents. Le traitement peut laisser une rubrique peu remplie dans les dernières 24 h ; sélectionner **7 jours** pour élargir. La classification « Économie Maroc » détecte des mots liés à l'économie dans les titres marocains, et ne doit pas être considérée comme un classement éditorial parfait.

Si certains flux RSS sont temporairement indisponibles, les autres continuent à fonctionner. Les sources peuvent changer leur format ou les droits de réutilisation ; respecter leurs conditions et attribuer le contenu. **Utilisation personnelle prévue**, publication publique ou commerciale à évaluer selon les licences des éditeurs.

## Activer les synthèses IA (OpenRouter, facultatif)

Le site GitHub Pages reste statique : **aucune clé API ne doit apparaître dans `index.html`, `news.json` ou un fichier versionné**. Seul le workflow GitHub Actions contacte OpenRouter. Les titres et descriptions RSS des articles sélectionnés sont transmis au fournisseur de modèle, et **pas** les données personnelles des lecteurs.

1. Créer une clé API sur [OpenRouter](https://openrouter.ai/settings/keys).
2. Dans le dépôt GitHub, ouvrir **Settings → Secrets and variables → Actions → Secrets → New repository secret**.
3. Nom du secret : `OPENROUTER_API_KEY`. Y coller la clé ; ne jamais la communiquer par chat ni la mettre dans le code.
4. Optionnel : dans **Variables**, créer `OPENROUTER_MODEL` pour choisir un modèle. Par défaut : `openrouter/free`, le routeur de modèles gratuits.
5. Ouvrir **Actions → Actualiser les actualités → Run workflow**. Vérifier l'étape « Actualiser les informations » : le nombre de brèves IA validées y est affiché.

Le workflow effectue au maximum **une requête API par exécution**, avec environ une exécution par heure. Les limitations de requêtes et la disponibilité des modèles gratuits peuvent varier. Si la clé est absente, invalide, si le quota est atteint, ou si la sortie IA ne passe pas la validation, l'application **conserve automatiquement les descriptions RSS**, sans interrompre le déploiement. Les modèles payants configurés volontairement peuvent engendrer des frais. La réponse du modèle reste une synthèse, non une preuve indépendante de véracité.

### Ajouter une rubrique ou un flux

- Modifier la liste `FEEDS` et `CATEGORIES` dans `scripts/update_news.py`.
- Ajouter sa catégorie avec `id`, `name`, `label`, `icon`, `title`, `detail` dans la variable `CATEGORIES` de `index.html`.
- Relancer le script et tester les résultats.

## Dépannage

- **Le flux est vide après un lancement local :** vérifier la connexion Internet, la date système et la sortie du script. Les articles de plus de 7 jours sont exclus.
- **GitHub Actions affiche une erreur de publication :** s'assurer que la source Pages est bien `GitHub Actions`, que les permissions Pages sont autorisées dans le dépôt et que le workflow s'exécute sur `main`.
- **Données anciennes :** les jobs `schedule` peuvent être retardés. Ouvrir l'onglet Actions pour diagnostiquer les erreurs de RSS.
- **Les favoris disparaissent dans un autre navigateur :** ils ne sont pas synchronisés, leur sauvegarde est locale.

## Architecture

- `index.html` — interface responsive statique
- `scripts/update_news.py` — collecte, filtre, date, doublons et JSON
- `scripts/ai_summarize.py` — synthèse IA facultative via OpenRouter (côté serveur)
- `news.json` — généré automatiquement ; le fichier livré est initialement vide, pour ne pas présenter de fausses actualités
- `.github/workflows/actualites.yml` — traitement et déploiement périodiques
