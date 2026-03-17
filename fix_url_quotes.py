"""Fix escaped single quotes in {% url %} template tags in home.html."""

HOME = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\home.html'

with open(HOME, encoding='utf-8') as f:
    lines = f.readlines()

import re

fixed = 0
for i, line in enumerate(lines):
    # Replace any \\' or \' sequences inside {% url %} tags with plain '
    if 'url' in line and 'product_detail' in line:
        original = line
        # Remove all backslash escaping of single quotes
        line = line.replace("\\'", "'").replace('\\"', '"')
        # Also handle triple-escaped \\\'  
        line = line.replace("\\\\", "").replace("\\'", "'")
        if line != original:
            lines[i] = line
            fixed += 1
            print(f'Fixed L{i+1}: {line.rstrip()}')
        else:
            print(f'No change L{i+1}: {line.rstrip()}')

with open(HOME, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(lines)

print(f'\nFixed {fixed} lines.')

# Verify
with open(HOME, encoding='utf-8') as f:
    content = f.read()
    
import re
url_tags = re.findall(r'\{%\s*url[^%]+%\}', content)
for tag in url_tags:
    print('URL tag:', tag)
