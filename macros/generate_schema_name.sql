{#
  Use the custom schema name verbatim (staging, intermediate, marts)
  instead of dbt's default "<target>_<custom>" prefixing. This keeps the
  warehouse schemas clean and predictable for a DuckDB single-file setup.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema | trim }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
