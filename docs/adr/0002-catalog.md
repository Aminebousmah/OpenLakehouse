# ADR 0002 : un catalogue REST

## Contexte
Spark et Trino doivent partager la même vue des tables et valider leurs écritures de façon atomique.

## Options
- **Hive Metastore** : éprouvé, mais lourd pour ce besoin, avec une base et un service Java de plus.
- **Nessie** : versionnement du catalogue façon Git, utile surtout si l'on en a l'usage.
- **Catalogue REST Iceberg** : API standardisée, neutre vis-à-vis des moteurs.

## Décision
Le catalogue REST, avec l'image de référence d'Apache Iceberg, adossée à une base SQLite sur volume.

## Conséquences
- Les moteurs parlent une API standard, donc remplacer l'implémentation ne touche pas à leur configuration.
- L'image de référence convient à une démonstration. En production, elle serait remplacée par une implémentation sur une vraie base, comme Polaris ou Lakekeeper.
- Pas de branches de données, une fonctionnalité que Nessie aurait apportée.
