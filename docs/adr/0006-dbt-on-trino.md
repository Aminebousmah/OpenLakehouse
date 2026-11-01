# ADR 0006 : dbt sur Trino pour la couche gold

## Contexte
Le modèle en étoile doit être testé, documenté et lisible par des analystes.

## Options
- **Transformations Spark** : puissantes, mais du code PySpark moins accessible, et pas de tests ni de lignage intégrés.
- **dbt sur Spark** : même outil, avec un démarrage plus lent pour de petites itérations.
- **dbt sur Trino** : SQL standard, itérations rapides, tests et documentation inclus.

## Décision
dbt sur Trino, avec les préfixes `stg_`, `fct_` et `dim_`.

## Conséquences
- Les tests et le lignage sont générés par `dbt build` et `dbt docs generate`.
- Les gros volumes passent par Trino sans tolérance aux pannes. Sur une machine, un `fct_trip` multi-mois doit tenir en mémoire, ce qui limite la volumétrie atteignable.
