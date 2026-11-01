# ADR 0008 : le stockage objet, après la disparition de l'image officielle de MinIO

## Contexte
Le lac a besoin d'un stockage compatible S3 qui tourne en local. Le choix naturel était MinIO, mais l'image `minio/minio` n'est plus disponible sur Docker Hub (vérifié le 01/11/2026 : `object not found`), et `quay.io/minio/minio` répond 401 sans authentification.

## Options
- **Build Bitnami figé de MinIO** (`bitnamilegacy/minio`) : même logiciel, éditeur connu, mais plus aucune mise à jour.
- **Fork communautaire** (`pgsty/minio`) : encore mis à jour, mais un éditeur tiers dont je ne peux pas garantir la confiance.
- **SeaweedFS ou Garage** : projets actifs et compatibles S3, à revalider avec Iceberg, Spark et Trino.
- **Compiler MinIO depuis les sources** : image maîtrisée, avec une maintenance supplémentaire pour une démonstration.

## Décision
`bitnamilegacy/minio:2025.7.23-debian-12-r5`, version épinglée. Le projet ne l'utilise qu'en local, sans exposition à Internet, et avec des données publiques. Une image qui ne reçoit plus de correctifs reste donc acceptable ici.

## Conséquences
- **Ce choix ne conviendrait pas à une production** : une image figée ne reçoit plus de correctifs de sécurité.
- Le reste de l'architecture ne dépend que de l'API S3 : remplacer le stockage ne touche que le service `minio` et son point d'accès. SeaweedFS serait la première option à évaluer.
- Le projet illustre un risque concret d'une pile « 100 % open source » : la licence d'un logiciel ne garantit pas la disponibilité de ses binaires.
