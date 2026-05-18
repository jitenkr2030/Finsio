{{ date }} {{ flag }} "{{ narration }}"{% if payee %} "{{ payee }}"{% endif %}{% for tag in tags %} {{ tag }}{% endfor %}{% for link in links %} {{ link }}{% endfor %}
{% for key, value in metadata.items() %}
  {{ key }}: "{{ value }}"
{%- endfor %}
{% for p in postings %}
  {{ p.account }}  {{ p.amount }} {{ p.currency }}
{%- endfor %}
