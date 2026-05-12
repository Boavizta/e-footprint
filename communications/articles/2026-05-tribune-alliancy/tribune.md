<!--
Champs du formulaire Alliancy (à reporter dans les champs distincts de la soumission) :

- Titre (≤80 car.) : Avant le bilan carbone, le business plan environnemental
- Sous-titre : GreenTech Forum 2026
- Hook (≤170 car.) : Mesurer ce qui existe et appliquer des bonnes pratiques ne suffisent pas. Pour réduire vraiment l'empreinte du numérique, il manque un levier : modéliser pour décider.
- Signature : Publicis Sapient France
- Image : 1280×720 (à fournir séparément)
-->

# Avant le bilan carbone, le business plan environnemental

Pour agir sur l'empreinte environnementale du numérique, deux leviers sont aujourd'hui largement reconnus : mesurer ce qui existe, et appliquer des bonnes pratiques d'écoconception. Il en manque un troisième, encore peu pratiqué : modéliser, en amont, pour décider en connaissance de cause.

## Mesurer et appliquer ne suffisent pas

La mesure — bilans GES, indicateurs de reporting, audits de services en production — est indispensable pour rendre compte. Mais elle intervient par construction après coup, sur des architectures, des fonctionnalités et des volumes déjà actés. C'est, en finance, l'équivalent de ne penser budget qu'au moment de la clôture trimestrielle, sans business plan en amont : indispensable pour piloter, insuffisant pour décider.

Les bonnes pratiques — optimiser les images, sobrifier les requêtes, allonger la durée de vie des terminaux, choisir des hébergements plus efficients — fournissent un répertoire d'actions réutilisables. Elles se heurtent toutefois à un mur de priorisation. Les services numériques varient massivement sur cinq sources d'impact — terminaux utilisateurs, objets edge et IoT, serveurs, stockage, réseau — à croiser avec deux phases (fabrication, usage), et amplifiées par des volumes d'usage très inégaux. La case dominante peut être totalement différente d'un service à l'autre : l'optimisation décisive d'un service de streaming n'est pas celle d'une plateforme d'IA générative, ni celle d'un déploiement IoT industriel. Et cette variabilité ne joue pas seulement entre services : au sein d'un même service, elle évolue avec les volumes, l'ajout de nouvelles fonctionnalités, les changements d'architecture. Aucune contextualisation ex ante des bonnes pratiques ne tient quand le système bouge.

D'où la nécessité d'un troisième levier qui se rejoue à chaque évolution : modéliser le service pour comparer des scénarios et hiérarchiser les efforts.

## Modéliser avant de décider, à chaque décision structurante

Le cas le plus visible est celui du cadrage initial. C'est au moment où l'on définit les fonctionnalités, l'architecture et les choix d'hébergement que se déterminent les contraintes les plus structurantes — celles qu'il sera ensuite long, coûteux et parfois impossible de revisiter. Investir, à ce stade, quelques jours de modélisation pour comparer des options évite des mois d'optimisation marginale en aval.

Mais la même logique s'applique à tout changement structurant ultérieur : montée en charge, ajout d'une fonctionnalité — typiquement une brique d'IA générative —, action d'écoconception envisagée, changement d'hébergement. Chaque fois qu'une décision peut significativement modifier l'empreinte d'un service, modéliser avant de trancher remet l'arbitrage sur des bases informées.

Deux raisons rendent cette modélisation préalable particulièrement précieuse. La première tient au retour sur investissement environnemental : sans modélisation hiérarchisée, on ignore où sont les vrais leviers et l'on optimise à l'aveugle. À effort équivalent, un gain de 90 % sur un poste mineur évite beaucoup moins de tonnes de CO₂ qu'un gain plus modeste sur un poste dominant ; seule la modélisation rend cet arbitrage visible avant qu'on n'engage l'effort.

La seconde tient à l'écart entre les conditions d'aujourd'hui et celles qu'on anticipe à terme. Si un service va passer de 10 000 à 1 million d'utilisateurs, raisonner sur la base du volume actuel revient à se faire l'image d'un système qui n'existera plus. Et la question des géographies pèse au moins autant, mais reste largement négligée : selon le pays d'usage et d'hébergement, l'intensité carbone de l'électricité varie d'un facteur 10. Modéliser aux volumes et géographies cibles donne une lecture plus juste des leviers prioritaires, particulièrement utile lorsqu'on intègre une brique d'IA dont les usages peuvent croître très vite et dont les choix de localisation pèsent lourd dans le bilan.

## Un cas industriel

Un grand groupe industriel international, confronté à la virtualisation du contrôle d'équipements électriques, devait arbitrer entre plusieurs trajectoires d'architecture : virtualisation dans le cloud ou en edge, introduction ou non de briques d'IA et choix de leur localisation, géographies de déploiement, mix d'équipements terrain (PCs industriels, capteurs, IoT). Plutôt que de trancher à l'intuition puis de chercher à optimiser après coup, ses équipes ont choisi de modéliser plusieurs scénarios, à périmètre fonctionnel constant, avant de décider.

L'exercice a permis de comparer les options sur des critères environnementaux objectivés, de mettre en évidence les postes structurants — qui n'étaient pas toujours ceux qu'on pressentait —, et d'orienter les choix d'architecture en connaissance de cause. L'innovation n'a pas été freinée ; elle a été encadrée par des arbitrages explicites. Les développements méthodologiques rendus nécessaires par la complexité du cas — modélisation fine d'objets edge, en particulier — ont en outre été reversés à l'écosystème open source, bénéficiant à d'autres acteurs confrontés à des problématiques similaires.

## Trois leviers pour passer à la pratique

Trois leviers pour ancrer cette démarche dans le quotidien.

**Outiller la décision avant le reporting.** Les équipes n'ont pas besoin de cocher des cases — elles ont besoin de comparer des scénarios, en interne, de manière itérative. C'est cette capacité de comparaison qui transforme une démarche d'écoconception en démarche de pilotage.

**Modéliser aux volumes et géographies cibles.** Les ordres de grandeur du système entier, projetés à l'usage et au déploiement anticipés, valent toujours mieux que les optimisations marginales sur l'existant. C'est ce qui distingue une modélisation utile de l'écueil le plus courant aujourd'hui : raisonner à l'unité — par visite ou par requête — sans jamais poser la question du système réellement déployé.

**S'appuyer sur des outils auditables.** La crédibilité d'un arbitrage environnemental repose sur la transparence de la méthode et sur la possibilité, pour des tiers, d'auditer les calculs et leurs limites. La modélisation du cas industriel évoqué plus haut s'est par exemple appuyée sur e-footprint, un logiciel open source hébergé par l'association Boavizta et auquel nos équipes contribuent, lui-même articulé avec d'autres composants ouverts qui en fournissent les facteurs d'émission et une partie des méthodes de calcul (Boavizta API, EcoLogits). D'autres outils peuvent répondre à la même exigence — l'essentiel est de pouvoir interroger la méthode autant que les résultats.

Aucun de ces trois leviers ne demande de bouleverser l'organisation. Il suffit, sur le prochain projet structurant, d'introduire la modélisation au moment même où l'on estime déjà coût, planning et bénéfice attendu. Loin de remplacer la mesure et les bonnes pratiques, cette modélisation les renforce : la première viendra confronter à la réalité ce qui aura été modélisé, les secondes trouveront leur pleine efficacité une fois identifiés les postes sur lesquels les concentrer.
