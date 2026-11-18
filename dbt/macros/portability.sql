{#
    Trino runs the models in production, DuckDB runs the same models in CI.
    Only the few functions the two engines spell differently go through these macros.
#}

{% macro select_days(first_date, last_date, from_relation) -%}
    {{ return(adapter.dispatch('select_days', 'openlakehouse')(first_date, last_date, from_relation)) }}
{%- endmacro %}

{% macro trino__select_days(first_date, last_date, from_relation) -%}
    select day_value
    from {{ from_relation }}
    cross join unnest(sequence({{ first_date }}, {{ last_date }}, interval '1' day)) as t (day_value)
{%- endmacro %}

{% macro duckdb__select_days(first_date, last_date, from_relation) -%}
    select cast(unnest(generate_series({{ first_date }}, {{ last_date }}, interval 1 day)) as date) as day_value
    from {{ from_relation }}
{%- endmacro %}


{% macro iso_day_of_week(date_expression) -%}
    {{ return(adapter.dispatch('iso_day_of_week', 'openlakehouse')(date_expression)) }}
{%- endmacro %}

{% macro trino__iso_day_of_week(date_expression) -%}
    day_of_week({{ date_expression }})
{%- endmacro %}

{% macro duckdb__iso_day_of_week(date_expression) -%}
    isodow({{ date_expression }})
{%- endmacro %}
