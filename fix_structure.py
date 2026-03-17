"""Restore CSS selector accidentally replaced with HTML div, and fix hero tag."""

HOME = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\home.html'

with open(HOME, encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: In the CSS section (early lines < 200), find the misplaced HTML div and
# restore it to the CSS selector .hero-tag{
for i, line in enumerate(lines):
    if 'class="hero-tag"' in line and i < 200:
        lines[i] = '.hero-tag{\n'
        print(f'Restored CSS selector at L{i+1}')
        break

# Fix 2: In the actual hero HTML section (line > 900), fix the Hot Deals hero tag
for i, line in enumerate(lines):
    if 'class="hero-tag"' in line and i > 900 and 'Hot Deals' in line:
        lines[i] = '      <div class="hero-tag">Hot Deals &mdash; Up to 50% Off</div>\n'
        print(f'Fixed hero HTML at L{i+1}')
        break

with open(HOME, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(lines)
print('Saved.')

# Verify
with open(HOME, encoding='utf-8') as f:
    content = f.read()

import re
print('CSS .hero-tag{:', '.hero-tag{' in content)
print('HTML hero-tag with mdash:', 'hero-tag">Hot Deals &mdash;' in content)
print('Non-ASCII count:', sum(1 for c in content if ord(c) > 127))
print('&#8377; count:', content.count('&#8377;'))
