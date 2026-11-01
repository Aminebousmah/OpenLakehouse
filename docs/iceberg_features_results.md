# Fonctionnalités Iceberg : résultats mesurés

Table de démonstration : 1,273,544 trajets du 1er et du 2 janvier 2024.

## `MERGE INTO`
2,824 lignes corrigées de +1 $. Total : 41,719,861.59 $ devenu 41,722,685.59 $.

## Time travel
Lecture du premier snapshot après la correction : 41,719,861.59 $, soit le total d'origine (identique).

## Évolution de schéma
Colonne ajoutée. Fichiers réécrits : 0. Les 1,273,544 lignes existantes lisent la nouvelle colonne à `null`.

## Évolution de partition
Passage de `month` à `day`, sans réécrire l'existant. 3 fichier(s) restent partitionnés par mois, 2 le sont par jour.

## Expiration des snapshots
3 snapshots avant, 1 après.
