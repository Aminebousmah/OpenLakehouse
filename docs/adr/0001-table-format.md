# ADR 0001 : Apache Iceberg comme format de table

## Contexte
Le lac doit servir plusieurs moteurs (Spark pour transformer, Trino pour requêter), supporter des corrections de lignes, et faire évoluer son schéma et son partitionnement sans réécrire les données.

## Options
- **Delta Lake** : très mature avec Spark, écosystème historiquement centré sur Databricks.
- **Apache Hudi** : excellent pour l'upsert à haute fréquence, plus complexe à régler, surtout pensé pour ce cas.
- **Apache Iceberg** : spécification ouverte et indépendante du moteur, partition cachée, évolution de partition.

## Décision
Iceberg, en format de table v2.

## Conséquences
- Trino et Spark lisent et écrivent les mêmes tables sans passerelle.
- L'évolution de partition évite de figer un choix : voir ADR 0004.
- La maintenance (compaction, expiration des snapshots) reste à notre charge : voir ADR 0005.
- Ce choix ne repose pas sur un comparatif chiffré entre les trois formats, qui n'a pas été mené ici.
