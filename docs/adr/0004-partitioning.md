# ADR 0004 : partitionnement par jour, en partition cachée

## Contexte
La plupart des requêtes filtrent sur la date de prise en charge. Le grain doit éviter à la fois de lire trop de données et de créer trop de petits fichiers.

## Options
- **Pas de partition** : simple, mais toute requête filtrée lit toute la table.
- **`month(pickup_ts)`** : peu de partitions et de gros fichiers, élagage grossier.
- **`days(pickup_ts)`** : élagage fin et risque de fichiers plus petits.

## Décision
`days(pickup_ts)` sur silver, `month(pickup_date)` sur le fait gold. La partition reste cachée : les requêtes filtrent sur la date, sans connaître de colonne technique.

## Conséquences
- `benchmarks/run.py` compare les trois options à volumétrie égale, et le rapport publie les résultats mesurés.
- Une évolution de partition reste possible sans réécriture. `scripts/iceberg_features.py` le démontre.
