| Table | Lignes | Fichiers | Taille |
|---|---:|---:|---:|
| `non_partitioned` | 93 155 058 | 16 | 4.99 Go |
| `partitioned_days` | 93 155 058 | 138 | 4.61 Go |
| `partitioned_months` | 93 155 058 | 16 | 4.99 Go |
| `fragmented` | 22 377 762 | 1 160 | 1.29 Go |
| `compacted` | 22 377 762 | 29 | 1.13 Go |

| Table | Requête | Médiane | p95 |
|---|---|---:|---:|
| `compacted` | Jointure dimension | 0.36 s | 0.38 s |
| `compacted` | Agrégat mensuel | 0.33 s | 0.38 s |
| `compacted` | Filtre sur un jour | 0.08 s | 0.09 s |
| `compacted` | Top zones d'un mois | 0.15 s | 0.16 s |
| `fragmented` | Jointure dimension | 0.85 s | 0.92 s |
| `fragmented` | Agrégat mensuel | 0.84 s | 0.91 s |
| `fragmented` | Filtre sur un jour | 0.10 s | 0.11 s |
| `fragmented` | Top zones d'un mois | 0.58 s | 0.63 s |
| `non_partitioned` | Jointure dimension | 0.50 s | 0.51 s |
| `non_partitioned` | Agrégat mensuel | 1.15 s | 1.26 s |
| `non_partitioned` | Filtre sur un jour | 0.16 s | 0.18 s |
| `non_partitioned` | Top zones d'un mois | 0.23 s | 0.26 s |
| `partitioned_days` | Jointure dimension | 0.38 s | 0.43 s |
| `partitioned_days` | Agrégat mensuel | 1.15 s | 1.27 s |
| `partitioned_days` | Filtre sur un jour | 0.08 s | 0.09 s |
| `partitioned_days` | Top zones d'un mois | 0.15 s | 0.17 s |
| `partitioned_months` | Jointure dimension | 0.45 s | 0.55 s |
| `partitioned_months` | Agrégat mensuel | 1.17 s | 1.27 s |
| `partitioned_months` | Filtre sur un jour | 0.15 s | 0.17 s |
| `partitioned_months` | Top zones d'un mois | 0.16 s | 0.17 s |
