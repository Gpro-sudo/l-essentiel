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

## Lecture vocale des actualités

Le site propose **🔊 Écouter** sous chaque carte et **▶ Écouter le briefing** pour lire les actualités actuellement affichées dans la rubrique. La lecture prononce le titre visible et le **résumé affiché**, pas le texte intégral d'un site tiers.

- **Pause / Reprendre / Arrêter** et réglage de vitesse (0,85× à 1,3×).
- Choix facultatif parmi les voix **françaises installées** sur l'appareil ; sinon, la voix française par défaut est demandée au navigateur.
- Si la synthèse vocale native du navigateur est disponible, le site utilise l'API Web Speech (`speechSynthesis` et `SpeechSynthesisUtterance`) avec la voix installée sur l'appareil. Sinon, il propose **des fichiers MP3 de secours** générés par le workflow GitHub Actions, puis lus par le lecteur HTML audio standard. Ce secours fonctionne aussi sur des navigateurs mobiles qui ne proposent pas l'API Web Speech ; la voix française de secours (eSpeak NG) est plus synthétique.
- Les MP3 sont générés **hors ligne** lors de chaque déploiement avec eSpeak NG et FFmpeg, puis publiés dans `dist/audio/` avec un manifeste `manifest.json`. Aucun compte ni clé d'API vocale externe n'est nécessaire. La génération dépend de la réussite du workflow ; un article ancien sauvegardé mais absent du manifeste ne dispose pas automatiquement de son MP3. La lecture en arrière-plan dépend toujours du navigateur et du système.
- Cliquer sur « Écouter le briefing » lit les cartes **actuellement affichées** l'une après l'autre, sans ouvrir les articles. Le dossier **Bourse / IPO Maroc** possède en plus son propre bouton « Écouter ce point Bourse », qui lit les chiffres, le calendrier d'introduction, les explications sur la correction du MASI et les perspectives en six séquences. Il comporte aussi Pause/Reprendre et Arrêter, synchronisés avec le lecteur général.
- Passer dans une autre rubrique arrête la lecture. Sur mobile, la lecture peut s'interrompre si l'écran est verrouillé.
- La synthèse vocale n'améliore pas l'exactitude des nouvelles : elle lit fidèlement les résumés disponibles et leur avertissement de provenance reste visible.

## Personnaliser le fil : « Ça m'intéresse » / « Pas pour moi »

- Chaque actualité propose **♡ Ça m'intéresse** et **✕ Pas pour moi**. Le choix porte sur un **sujet détecté** (Tesla, SpaceX, fusion Tesla–SpaceX...), ou sur une histoire précise si le système ne reconnaît pas de thème.
- **Mes sujets** regroupe les nouvelles correspondant aux sujets suivis. Le champ **Suivre un thème** accepte une recherche manuelle comme `Tesla SpaceX`, `BYD` ou `voitures électriques`. Les mots du thème manuel doivent tous figurer dans le titre ou l'extrait pour sélectionner la nouvelle.
- **Pas pour moi** masque les articles correspondants du flux principal. Les thèmes ignorés restent visibles comme étiquettes grises dans **Vos centres d'intérêt**, où on peut annuler le choix.
- Lorsqu'un même événement est identifié par un **storyKey** partagé, un seul article est affiché avec une indication du nombre d'articles regroupés. Il s'agit d'une déduplication heuristique, pas d'une vérification supplémentaire. Les développements distincts ne sont pas nécessairement regroupés.
- Les préférences sont conservées en **localStorage sur cet appareil / navigateur uniquement** ; rien n'est transmis à GitHub ni à OpenRouter. Effacer les données du navigateur les supprime. Les favoris restent indépendants.

### Automobile & Reuters

La rubrique **Automobile & transport** récupère des titres et courts extraits **indexés par Google Actualités** concernant l'industrie automobile, notamment certaines nouvelles de Reuters. Les anciens flux RSS directs de Reuters ne sont plus actifs. Le site fournit un lien vers [Reuters — Autos & Transportation](https://www.reuters.com/business/autos-transportation/), **sans aspirer la page Reuters ni republier ses articles complets**.

Exemple : le rapprochement **Tesla / SpaceX envisagé** constitue un sujet commun, mais il ne faut pas le décrire comme une fusion réalisée. Les projets conjoints, comme Terafab, sont suivis séparément. Les regroupements n'impliquent pas que les deux sociétés ont signé un accord.

## Bourse & IPO Maroc : veille financière ciblée

La rubrique **Économie Maroc** et la page **À la une** contiennent un dossier **Bourse / IPO** documenté, en complément des dépêches générales. Il reprend explicitement les dernières informations disponibles à la date du **27 octobre 2026**, avec la séance officielle MASI du **26 octobre 2026** et le calendrier prévu de l'introduction de Jet Energy.

Ce dossier est une **photographie datée**, pas un flux de cours, ni une analyse recalculée automatiquement. Lorsque plusieurs jours passent, il porte un avertissement « analyse historique ». Les dates futures de l'IPO restent marquées comme prévues ; le prix définitif n'est pas inventé. Le moteur collecte séparément les **nouvelles fraîches** avec des requêtes ciblées sur IPO, AMMC, MASI, taux obligataires, valorisations et résultats. Les médias sous-jacents gardent leur nom d'éditeur pour éviter les faux recoupements par agrégateur.

La section « Pourquoi le MASI corrige » distingue les **faits constatés** des **scénarios de marché attribués à CFG Research**. Aucun conseil d'achat ou de vente n'est donné. Les informations fondamentales doivent être vérifiées dans le prospectus AMMC et dans les publications officielles avant une décision financière.

## Titres factuels plutôt que sensationnalistes

La page conserve le **titre original du média** dans le lien et les données JSON, mais peut afficher un **titre reformulé** lorsque le titre initial contient une accroche sensationnaliste (par exemple « décision radicale », « coup de tonnerre », « scandale »). La reformulation est fondée uniquement sur le titre, la description RSS et les autres titres de recoupement ; elle n'est pas une vérification indépendante du contenu complet.

- Lorsque l'IA produit un titre, un contrôle de longueur, de formulations accrocheuses et de chiffres non fournis est effectué. Les titres prudents (« envisager », « discuter ») ne doivent pas devenir des résultats définitifs (« fusion réalisée », « loi adoptée »).
- **Si l'IA est indisponible**, une phrase complète, non sensationnaliste, peut être reprise telle quelle de la description RSS, avec la mention « Titre reformulé ».
- Si aucune formulation suffisamment fidèle n'est disponible, le titre d'origine porte l'avertissement **« Titre d'origine à vérifier »** et n'est pas choisi pour le briefing court « Essentiel » ; il peut rester dans le flux complet pour transparence.
- Les contrôles sont automatisés et imparfaits. Un article recoupé par plusieurs médias ne prouve pas que tous les détails sont véridiques.

## Comment sont recoupées les informations ?

L'écran **Essentiel** ne montre que les événements retrouvés auprès d'au moins deux rédactions distinctes. Le système analyse le type d'événement (vote, projet, annonce, hausse...), les dates et les termes significatifs ; il rejette notamment les recoupements trompeurs entre « loi examinée » et « loi adoptée ». Deux titres du même groupe de presse ne comptent pas comme deux sources. Il recherche des confirmations dans les flux déjà collectés et dans les résultats RSS de recherche d'actualités.

La mention **« Recoupé · média A + média B »** signifie uniquement que deux médias distincts rapportent un événement concordant. **Ce n'est pas un fact-checking humain ni une garantie d'exactitude de chaque chiffre ou de chaque déclaration.** Les sources peuvent reprendre une même dépêche ou commettre la même erreur. Les faits incertains ne doivent pas être présentés comme des certitudes et les affirmations d'une personne doivent lui être attribuées.

Le bouton **Tout** laisse accessibles les informations de source unique, clairement indiquées **« Source unique · non recoupé »**. Si aucune confirmation suffisante n'a été trouvée pour une rubrique, le briefing ne remplit pas cette rubrique artificiellement. Le moteur de rapprochement reste heuristique : il peut manquer de véritables confirmations ou confondre des sujets proches malgré ses contrôles.

L'interface affiche un titre sur deux lignes au besoin, trois lignes de texte au maximum, et l'identité des médias de recoupement. Il n'est pas nécessaire de consulter les sites externes pour lire le bref rappel des faits, mais les liens permettent d'aller plus loin.

## Sources et contenus

Sources RSS configurées dans `scripts/update_news.py` : RFI, France 24, franceinfo, Hespress français, Le Courrier de l'Atlas, 01net, Numerama, Blog du Modérateur, Clubic. Chaque article renvoie à sa source.

Sans clé OpenRouter ou si le modèle échoue, les textes courts proviennent des **descriptions RSS des éditeurs**, limitées à environ 190 caractères. Avec clé, une synthèse IA des extraits RSS et des titres d'autres médias est tentée pour **une actualité recoupée prioritaire par rubrique** (jusqu'à sept articles en une requête, avec une tentative de repli si le routeur refuse le format). Le résultat est contrôlé sommairement (longueur et chiffres nouveaux). Chaque carte générée par l'IA affiche « Synthèse IA » ; les autres restent RSS. L'IA ne lit **pas** l'article complet et ne vérifie pas les faits indépendamment. Vérifiez toujours la source originale.

La pertinence est basée sur une sélection de sources, des filtres thématiques, un score de fraîcheur, quelques mots-clés de signal et un dédoublonnage approximatif. Ce filtrage est imparfait : des sujets importants peuvent passer à travers et les sources peuvent avoir des angles différents. Le traitement peut laisser une rubrique peu remplie dans les dernières 24 h ; sélectionner **7 jours** pour élargir. La classification « Économie Maroc » détecte des mots liés à l'économie dans les titres marocains, et ne doit pas être considérée comme un classement éditorial parfait.

Si certains flux RSS sont temporairement indisponibles, les autres continuent à fonctionner. Les sources peuvent changer leur format ou les droits de réutilisation ; respecter leurs conditions et attribuer le contenu. **Utilisation personnelle prévue**, publication publique ou commerciale à évaluer selon les licences des éditeurs.

## Activer les synthèses IA (OpenRouter, facultatif)

Le site GitHub Pages reste statique : **aucune clé API ne doit apparaître dans `index.html`, `news.json` ou un fichier versionné**. Seul le workflow GitHub Actions contacte OpenRouter. Les titres et descriptions RSS des articles sélectionnés sont transmis au fournisseur de modèle, et **pas** les données personnelles des lecteurs.

1. Créer une clé API sur [OpenRouter](https://openrouter.ai/settings/keys).
2. Dans le dépôt GitHub, ouvrir **Settings → Secrets and variables → Actions → Secrets → New repository secret**.
3. Nom du secret : `OPENROUTER_API_KEY`. Y coller la clé ; ne jamais la communiquer par chat ni la mettre dans le code.
4. Optionnel : dans **Variables**, créer `OPENROUTER_MODEL` pour choisir un modèle. Par défaut : `liquid/lfm-2.5-2.6b:free`, un modèle gratuit capable de produire du JSON structuré. Vous pouvez choisir un autre modèle avec `OPENROUTER_MODEL`.
5. Ouvrir **Actions → Actualiser les actualités → Run workflow**. Vérifier l'étape « Actualiser les informations » : le nombre de brèves IA validées y est affiché.

Le workflow effectue normalement **une requête API par exécution**, et une deuxième tentative seulement si le format est rejeté (erreur 400) ; l'exécution est prévue environ une fois par heure. Les quotas gratuits sont limités et les tentatives échouées peuvent être décomptées. Les limitations de requêtes et la disponibilité des modèles gratuits peuvent varier. Si la clé est absente, invalide, si le quota est atteint, ou si la sortie IA ne passe pas la validation, l'application conserve les descriptions RSS ou, pour le même article toujours recoupé et récent, une synthèse IA précédemment validée. Elle n'interrompt pas le déploiement. Les modèles payants configurés volontairement peuvent engendrer des frais. La réponse du modèle reste une synthèse, non une preuve indépendante de véracité.

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
