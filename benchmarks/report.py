"""Turn the raw benchmark results into a Markdown table and a figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9"
PARTITION_TABLES = {
    "non_partitioned": ("Sans partition", "#2a78d6"),
    "partitioned_months": ("Par mois", "#eb6834"),
    "partitioned_days": ("Par jour", "#1baf7a"),
}
QUERY_LABELS = {
    "monthly_aggregate": "Agrégat mensuel",
    "single_day_filter": "Filtre sur un jour",
    "top_zones": "Top zones d'un mois",
    "dimension_join": "Jointure dimension",
}


def markdown(report: dict) -> str:
    lines = ["| Table | Lignes | Fichiers | Taille |", "|---|---:|---:|---:|"]
    for name, stats in report["tables"].items():
        size = stats["size_bytes"] / 1e9
        row = f"| `{name}` | {stats['rows']:,} | {stats['files']:,} | {size:.2f} Go |"
        lines.append(row.replace(",", " "))
    lines += ["", "| Table | Requête | Médiane | p95 |", "|---|---|---:|---:|"]
    for row in report["summary"]:
        label = QUERY_LABELS[row["query"]]
        lines.append(
            f"| `{row['table']}` | {label} | {row['median_s']:.2f} s | {row['p95_s']:.2f} s |"
        )
    return "\n".join(lines) + "\n"


def figure(report: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.2), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    medians = {(r["table"], r["query"]): r["median_s"] for r in report["summary"]}
    queries = list(QUERY_LABELS)
    width = 0.26
    for index, (table, (label, color)) in enumerate(PARTITION_TABLES.items()):
        positions = [q + (index - 1) * (width + 0.015) for q in range(len(queries))]
        values = [medians[(table, query)] for query in queries]
        bars = ax.bar(positions, values, width, color=color, label=label)
        ax.bar_label(bars, fmt="%.2f", color=INK, fontsize=8, padding=2)
    ax.set_xticks(range(len(queries)), [QUERY_LABELS[q] for q in queries], color=MUTED)
    ax.set_ylabel("Latence médiane (s)", color=MUTED)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, labelcolor=MUTED, fontsize=9)
    rows = f"{report['tables']['non_partitioned']['rows']:,}".replace(",", " ")
    title = f"Effet du partitionnement, {rows} trajets"
    ax.set_title(title, loc="left", color=INK,
                 fontsize=12, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", required=True)
    args = parser.parse_args()
    results = ROOT / "results"
    report = json.loads((results / f"results_{args.scale}.json").read_text(encoding="utf-8"))
    (results / f"report_{args.scale}.md").write_text(markdown(report), encoding="utf-8")
    figure(report, results / f"partitioning_{args.scale}.png")
    print(markdown(report))


if __name__ == "__main__":
    main()
