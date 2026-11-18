# ADR 0010 : dbt testé en CI sur DuckDB

## Contexte
La CI ne lançait que ruff et pytest. Les modèles dbt n'étaient exécutés que sur la stack Docker complète, à la main : une erreur SQL ou une régression de l'incrémental passait la CI.

## Options
- **Trino en CI** : le vrai moteur, mais un catalogue Iceberg, un stockage objet et plusieurs minutes de démarrage par run.
- **`dbt parse` seul** : rapide, sans rien exécuter.
- **DuckDB** : les mêmes modèles exécutés en quelques secondes sur un jeu de données synthétique.

## Décision
Une cible `ci` sur DuckDB, alimentée par `tests/fixtures/silver_trips.csv`, typé depuis le contrat de données. Les rares fonctions qui s'écrivent différemment passent par des macros `adapter.dispatch`. La CI lance `dbt build`, les tests unitaires dbt, et vérifie qu'un mois rechargé ne crée pas de doublon. `dbt parse` sur la cible Trino s'assure en plus que le projet reste valide pour la production.

## Conséquences
- La logique des modèles et de l'incrémental est vérifiée à chaque PR.
- La CI ne valide ni le dialecte Trino des macros, ni les propriétés Iceberg, ni les performances : `scripts/run_month.sh` sur la stack reste le test de référence.
- Les tests unitaires tournent en CI seulement. Les runs de production les excluent avec `--exclude-resource-type unit_test`.
