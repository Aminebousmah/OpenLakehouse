"""Create the Superset dashboard through its REST API, from the gold layer. Safe to rerun."""

from __future__ import annotations

import json
import os

import httpx

BASE = os.environ.get("SUPERSET_URL", "http://localhost:8089")
USER = "admin"
PASSWORD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
TITLE = "Trajets taxi et VTC de New York"

DATASETS = {
    "trips_by_month": """
        select
            cast(date_trunc('month', pickup_date) as date) as month,
            service,
            count(*) as trips,
            avg(total_amount) as avg_total,
            avg(tip_amount) as avg_tip,
            avg(duration_minutes) as avg_duration
        from iceberg.gold.fct_trip
        group by 1, 2
    """,
    "top_zones": """
        select z.zone_name, z.borough, count(*) as trips
        from iceberg.gold.fct_trip as t
        inner join iceberg.gold.dim_zone as z on t.pickup_zone_id = z.zone_id
        group by 1, 2
        order by 3 desc
        limit 15
    """,
}


def metric(column: str, label: str, aggregate: str = "SUM") -> dict:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": aggregate,
        "label": label,
    }


def timeseries(metrics: list[dict]) -> dict:
    return {
        "x_axis": "month",
        "time_grain_sqla": "P1M",
        "metrics": metrics,
        "groupby": ["service"],
        "row_limit": 1000,
        "show_legend": True,
        "rich_tooltip": True,
    }


CHARTS = [
    ("Volumes par mois", "echarts_timeseries_bar", "trips_by_month",
     {**timeseries([metric("trips", "Trajets")]), "stack": "Stack"}),
    ("Top des zones de prise en charge", "echarts_timeseries_bar", "top_zones",
     {"x_axis": "zone_name", "metrics": [metric("trips", "Trajets")], "groupby": [],
      "orientation": "horizontal", "row_limit": 15, "show_legend": False,
      "x_axis_sort": "Trajets", "x_axis_sort_asc": True}),
    ("Revenu moyen par trajet ($)", "echarts_timeseries_line", "trips_by_month",
     timeseries([metric("avg_total", "Revenu moyen", "AVG")])),
    ("Pourboire moyen par trajet ($)", "echarts_timeseries_line", "trips_by_month",
     timeseries([metric("avg_tip", "Pourboire moyen", "AVG")])),
    ("Durée moyenne des trajets (min)", "echarts_timeseries_line", "trips_by_month",
     timeseries([metric("avg_duration", "Durée moyenne", "AVG")])),
]


def layout(chart_ids: list[tuple[int, str]]) -> dict:
    """Two charts per row: the minimal position tree that Superset accepts."""
    position: dict = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [],
                    "parents": ["ROOT_ID"]},
    }
    for row_index in range(0, len(chart_ids), 2):
        row_id = f"ROW-{row_index}"
        position["GRID_ID"]["children"].append(row_id)
        row = chart_ids[row_index : row_index + 2]
        position[row_id] = {
            "type": "ROW", "id": row_id, "children": [f"CHART-{cid}" for cid, _ in row],
            "parents": ["ROOT_ID", "GRID_ID"], "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for cid, name in row:
            position[f"CHART-{cid}"] = {
                "type": "CHART", "id": f"CHART-{cid}", "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {"chartId": cid, "sliceName": name, "width": 6, "height": 50},
            }
    return position


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)
    token = client.post(
        "/api/v1/security/login",
        json={"username": USER, "password": PASSWORD, "provider": "db", "refresh": True},
    ).raise_for_status().json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    csrf = client.get("/api/v1/security/csrf_token/").raise_for_status().json()["result"]
    client.headers["X-CSRFToken"] = csrf
    client.headers["Referer"] = BASE

    databases = client.get("/api/v1/database/").raise_for_status().json()["result"]
    database = next(d["id"] for d in databases if d["database_name"] == "lakehouse")

    def find(path: str, column: str, value: str) -> int | None:
        query = json.dumps(
            {"filters": [{"col": column, "opr": "eq", "value": value}], "page_size": 1}
        )
        rows = client.get(path, params={"q": query}).raise_for_status().json()["result"]
        return rows[0]["id"] if rows else None

    datasets = {}
    for name, sql in DATASETS.items():
        found = find("/api/v1/dataset/", "table_name", name)
        datasets[name] = found or client.post(
            "/api/v1/dataset/",
            json={"database": database, "schema": "gold", "table_name": name, "sql": sql},
        ).raise_for_status().json()["id"]

    dashboard = find("/api/v1/dashboard/", "dashboard_title", TITLE)
    if dashboard is None:
        dashboard = client.post(
            "/api/v1/dashboard/", json={"dashboard_title": TITLE, "published": True}
        ).raise_for_status().json()["id"]

    charts = []
    for name, viz, dataset, params in CHARTS:
        payload = {
            "slice_name": name,
            "viz_type": viz,
            "datasource_id": datasets[dataset],
            "datasource_type": "table",
            "params": json.dumps({**params, "viz_type": viz}),
            "dashboards": [dashboard],
        }
        existing = find("/api/v1/chart/", "slice_name", name)
        if existing:
            client.put(f"/api/v1/chart/{existing}", json=payload).raise_for_status()
            charts.append((existing, name))
        else:
            created = client.post("/api/v1/chart/", json=payload).raise_for_status().json()["id"]
            charts.append((created, name))

    client.put(
        f"/api/v1/dashboard/{dashboard}",
        json={"position_json": json.dumps(layout(charts)), "published": True},
    ).raise_for_status()
    print(f"{BASE}/superset/dashboard/{dashboard}/ : {len(charts)} graphiques")


if __name__ == "__main__":
    main()
