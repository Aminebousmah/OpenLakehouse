# ADR 0003 : Trino pour le requêtage interactif

## Contexte
Les dashboards et les analystes attendent des réponses interactives. Les transformations lourdes de bronze vers silver ont d'autres besoins.

## Options
- **Spark SQL partout** : une seule technologie, mais des temps de démarrage et une concurrence peu adaptés à l'interactif.
- **Trino** : pensé pour le SQL interactif et concurrent, sans tolérance aux pannes par défaut sur les longues requêtes.

## Décision
Spark pour bronze vers silver, Trino pour les requêtes et pour gold.

## Conséquences
- Deux moteurs à configurer, reliés par Iceberg et le catalogue.
- Les lectures interactives bénéficient de l'élagage de partitions de Trino, mesuré dans les benchmarks.
- Sur une seule machine, Trino et Spark se partagent la mémoire. Ils ne tournent donc jamais en charge en même temps.
