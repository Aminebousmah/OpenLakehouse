import ast
from pathlib import Path

import pytest
import yaml

from benchmarks.stats import median, percentile
from ingestion.download import object_key, parse_months, source_url
from quality.check_contract import CONTRACT, contract_checks

ROOT = Path(__file__).resolve().parent.parent


class TestMonths:
    def test_range_spans_a_new_year(self):
        assert parse_months("2023-11..2024-02") == ["2023-11", "2023-12", "2024-01", "2024-02"]

    def test_list_and_duplicates(self):
        assert parse_months("2024-03,2024-01,2024-01..2024-02") == [
            "2024-01", "2024-02", "2024-03",
        ]

    def test_single_month(self):
        assert parse_months("2024-01") == ["2024-01"]

    def test_inverted_range_is_refused(self):
        with pytest.raises(ValueError):
            parse_months("2024-03..2024-01")


def test_paths_follow_the_tlc_naming():
    assert source_url("fhvhv", "2024-01").endswith("/fhvhv_tripdata_2024-01.parquet")
    assert object_key("yellow", "2024-01") == "yellow/month=2024-01/yellow_tripdata_2024-01.parquet"


class TestContract:
    @pytest.fixture
    def contract(self):
        return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_has_owner_sla_and_key(self, contract):
        assert contract["owner"]
        assert contract["sla"]["freshness"]
        assert contract["primary_key"] == ["trip_id"]

    def test_checks_cover_every_rule_type(self, contract):
        names = [name for name, _ in contract_checks(contract)]
        assert "trip_id: non nul" in names
        assert "total_amount: >= 0" in names
        assert "service: valeurs admises" in names
        assert any(name.startswith("clé primaire") for name in names)

    def test_month_scope_is_applied(self, contract):
        for _, sql in contract_checks(contract, "2024-01"):
            assert "source_month = '2024-01'" in sql


class TestStatistics:
    def test_percentile_returns_an_observed_value(self):
        values = [float(v) for v in range(1, 21)]
        assert percentile(values, 0.95) == 19.0
        assert percentile(values, 0.5) == 10.0

    def test_percentile_of_one_value(self):
        assert percentile([3.0], 0.95) == 3.0

    def test_median_even_and_odd(self):
        assert median([1.0, 3.0]) == 2.0
        assert median([3.0, 1.0, 2.0]) == 2.0


class TestGovernance:
    def test_analyst_is_read_only_on_gold(self):
        import json

        rules = json.loads((ROOT / "governance/roles/trino_rules.json").read_text("utf-8"))
        analyst = [r for r in rules["tables"] if r.get("user") == "analyst"]
        assert [(r["schema"], r["privileges"]) for r in analyst] == [("gold", ["SELECT"])]

    def test_dbt_models_follow_the_naming_convention(self):
        models = (ROOT / "dbt/models").rglob("*.sql")
        assert all(m.stem.split("_")[0] in {"stg", "int", "fct", "dim"} for m in models)

    @pytest.mark.parametrize(
        "script",
        ["airflow/dags/monthly_pipeline.py", "spark_jobs/bronze_to_silver.py",
         "spark_jobs/maintenance.py"],
    )
    def test_scripts_outside_the_python_env_are_valid(self, script):
        ast.parse((ROOT / script).read_text(encoding="utf-8"))

    def test_at_least_six_adrs(self):
        assert len(list((ROOT / "docs/adr").glob("*.md"))) >= 6
