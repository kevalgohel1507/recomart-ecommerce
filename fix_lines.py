"""
Fix specific lines in home.html that still have missing rupee symbols / dashes.
Works by line number replacement - safe and precise.
"""

HOME = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\home.html'

with open(HOME, encoding='utf-8') as f:
    lines = f.readlines()

def set_line(lines, search_fragment, new_content):
    """Replace the first line containing search_fragment with new_content."""
    for i, line in enumerate(lines):
        if search_fragment in line:
            lines[i] = new_content + '\n'
            print(f"  Fixed L{i+1}: {new_content[:80]}")
            return True
    print(f"  WARNING: not found: {search_fragment!r}")
    return False

print("Fixing lines...")

# 1. sale-title-chip (trim leading space)
set_line(lines, 'sale-title-chip',
    '    <span class="sale-title-chip">{{ active_sale.banner_text }}</span>')

# 2. hero-tag Hot Deals
set_line(lines, 'hero-tag',
    '      <div class="hero-tag">Hot Deals &mdash; Up to 50% Off</div>')

# 3. prod-card-price (rupee in <sup>)
set_line(lines, 'prod-card-price',
    '          <div class="prod-card-price">{% if v %}<sup>&#8377;</sup>{{ v.price }}{% else %}&mdash;{% endif %}</div>')

# 4. rec-card-price (rupee prefix)
set_line(lines, 'rec-card-price',
    '          {% if v %}<div class="rec-card-price">&#8377;{{ v.price }}</div>{% endif %}')

# 5. Free shipping trust text
set_line(lines, 'Orders above',
    '      <p>Orders above &#8377;499 get free shipping. Express delivery in 24&ndash;48 hrs.</p>')

# 6. Customer support em-dash
set_line(lines, 'always here for you',
    '      <p>Our team is always here for you &mdash; chat, email or call anytime.</p>')

# 7. JS hero slide chips
chip_map = {
    'Electronics': "{chip:'Electronics &mdash; Up to 45% Off'},",
    'Fashion':     "{chip:'Fashion &mdash; Up to 40% Off'},",
    'Watches':     "{chip:'Watches &mdash; Up to 35% Off'},",
    'Footwear':    "{chip:'Footwear &mdash; Up to 50% Off'},",
    'Perfumes':    "{chip:'Perfumes &mdash; Up to 30% Off'},",
    'Home & Living': "{chip:'Home & Living &mdash; Up to 25% Off'},",
}
for keyword, new_chip in chip_map.items():
    for i, line in enumerate(lines):
        if "chip:'" in line and keyword in line:
            lines[i] = '    ' + new_chip + '\n'
            print(f"  Fixed chip L{i+1}: {keyword}")
            break

with open(HOME, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(lines)

print("\nDone. Verifying...")
with open(HOME, encoding='utf-8') as f:
    content = f.read()

checks = {
    '&#8377;': content.count('&#8377;'),
    '&mdash;': content.count('&mdash;'),
    '&ndash;': content.count('&ndash;'),
    'non-ASCII': sum(1 for c in content if ord(c) > 127),
    'prod-card-price &#8377;': '&#8377;</sup>{{ v.price }}' in content,
    'rec-card-price &#8377;': '&#8377;{{ v.price }}' in content,
}
for k, v in checks.items():
    print(f"  {k}: {v}")
