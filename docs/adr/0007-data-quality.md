# ADR 0007 : contrôle qualité dérivé du contrat de données

## Contexte
La couche silver doit être vérifiée avant de nourrir gold. La spécification proposait Great Expectations ou Soda.

## Options
- **Great Expectations** : très complet, avec beaucoup de configuration et de dépendances.
- **Soda Core** : syntaxe légère, avec une seconde définition des règles à côté du contrat.
- **Contrôles générés depuis le contrat YAML** : une seule source de vérité, moins de fonctionnalités.

## Décision
`quality/check_contract.py` génère les contrôles SQL depuis `governance/contracts/silver_trips.yaml`, et les tests dbt couvrent gold. Ni Great Expectations ni Soda ne sont utilisés : le contrat suffit à ce volume de règles, et une seule définition évite que les deux divergent.

## Conséquences
- Modifier le contrat modifie immédiatement les contrôles.
- Pas de profilage automatique ni de rapports riches. Si ce besoin arrive, Soda serait la première option à reconsidérer.
