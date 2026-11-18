# ADR 0009 : `fct_trip` incrémental, rechargé par mois source

## Contexte
`fct_trip` était une table reconstruite en entier à chaque `dbt build` : 93 millions de lignes réécrites pour ajouter un mois. Le chargement est mensuel, et un mois peut être rechargé après un retry ou une correction de la TLC.

## Options
- **Table complète** : simple et toujours juste, mais un coût qui croît avec l'historique.
- **Incrémental `merge` sur `trip_id`** : ne réécrit que les lignes modifiées, mais une jointure sur 93 millions de clés SHA-256, là où Trino a déjà manqué de mémoire.
- **Incrémental `delete+insert` sur `source_month`** : le mois rechargé est supprimé puis réinséré, sans jointure sur les clés.

## Décision
`delete+insert` avec `unique_key: source_month`. L'orchestrateur passe le mois avec `--vars '{month: AAAA-MM}'`, validé au format. Sans variable, un run charge les mois que silver a et que la table n'a pas.

## Conséquences
- Rejouer un mois ne duplique aucune ligne, et une correction de la TLC remplace l'ancienne version. Les deux cas sont testés en CI.
- `source_month` rejoint `fct_trip`. La table existante doit être reconstruite une fois avec `--full-refresh`, et `on_schema_change: fail` le rappelle plutôt que de laisser passer des lignes sans mois.
- La suppression porte sur `source_month` alors que la partition est `month(pickup_date)` : Trino écrit des fichiers de suppression, que la compaction absorbe.
