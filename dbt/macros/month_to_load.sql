{#
    Which source months an incremental run reloads.
    With --vars '{month: 2024-03}', only that month: the orchestrator always passes it.
    Without it, the months silver has and the table does not yet hold.
#}
{% macro month_to_load_filter() -%}
    {%- set month = var('month', none) -%}
    {%- if month -%}
        {%- if not modules.re.match('^[0-9]{4}-(0[1-9]|1[0-2])$', month | string) -%}
            {{ exceptions.raise_compiler_error("var 'month' doit être au format AAAA-MM, reçu : " ~ month) }}
        {%- endif -%}
        source_month = '{{ month }}'
    {%- else -%}
        source_month not in (select distinct source_month from {{ this }})
    {%- endif -%}
{%- endmacro %}
