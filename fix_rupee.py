"""Fix remaining duplicate price lines missing rupee entity."""

HOME = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\home.html'

with open(HOME, encoding='utf-8') as f:
    lines = f.readlines()

fixed = 0
for i, line in enumerate(lines):
    # Fix prod-card-price missing rupee (the <sup></sup> case)
    if 'prod-card-price' in line and 'v.price' in line and '<sup></sup>' in line:
        lines[i] = '          <div class="prod-card-price">{% if v %}<sup>&#8377;</sup>{{ v.price }}{% else %}&mdash;{% endif %}</div>\n'
        print(f'Fixed prod-card-price at L{i+1}')
        fixed += 1
    # Fix rec-card-price missing rupee (no &#8377; prefix)
    elif 'rec-card-price' in line and 'v.price' in line and '&#8377;' not in line:
        lines[i] = '          {% if v %}<div class="rec-card-price">&#8377;{{ v.price }}</div>{% endif %}\n'
        print(f'Fixed rec-card-price at L{i+1}')
        fixed += 1

with open(HOME, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(lines)

print(f'Fixed {fixed} lines. Done.')
