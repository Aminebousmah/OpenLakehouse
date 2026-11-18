# ADR 0011 : dbt orchestré par Cosmos dans Airflow

## Contexte
Le DAG lançait `dbt build` dans une seule tâche bash. Un test en échec faisait échouer toute la couche gold, et le retry relançait tous les modèles.

## Options
- **Une tâche `dbt build`** : simple, mais opaque dans Airflow.
- **Une tâche bash par modèle, écrite à la main** : lisible, mais un DAG à maintenir en double du projet dbt.
- **Cosmos** : le graphe dbt est lu au parsing du DAG et rendu en tâches Airflow.

## Décision
Un `DbtTaskGroup` Cosmos, en mode local avec le dbt du venv des outils. Chaque modèle donne une tâche `run` suivie de sa tâche `test`. Les tests de relation entre `fct_trip` et une dimension ont leur propre tâche, après les deux modèles. Le mois du run est transmis à dbt en variable templatée.

## Conséquences
- Un échec désigne un modèle, et le retry ne relance que lui.
- Ajouter un modèle dbt l'ajoute au DAG, sans toucher au code Airflow.
- Cosmos lance `dbt ls` à chaque parsing du DAG, ce qui ajoute quelques secondes au scheduler, et le cache de Cosmos les absorbe.
- La CI charge le DAG dans un vrai Airflow et exécute le groupe dbt sur DuckDB.
