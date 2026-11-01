# ADR 0005 : compaction et taille des fichiers

## Contexte
Des écritures répétées produisent de petits fichiers, qui ralentissent les lectures et alourdissent les métadonnées.

## Options
- **Pas de maintenance** : simple, avec une dégradation progressive.
- **Compaction continue** : fichiers toujours optimaux, mais du calcul permanent pour un chargement mensuel.
- **Compaction après chaque chargement mensuel** : coût maîtrisé, en phase avec le rythme des données.

## Décision
Après chaque mois chargé : `rewrite_data_files` avec une cible de 256 Mo, puis `expire_snapshots` en gardant 7 jours et au moins 3 snapshots.

## Conséquences
- Le gain de lecture est mesuré entre une table fragmentée et sa version compactée.
- Le time travel reste limité à la rétention des snapshots.
