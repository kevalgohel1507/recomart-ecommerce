import re

f = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\home.html'
with open(f, 'rb') as fh:
    raw = fh.read()
if raw.startswith(b'\xef\xbb\xbf'):
    raw = raw[3:]
text = raw.decode('latin-1')

# Fix all corrupted byte sequences
fixes = [
    ('\xe2\x82\xb9', '&#8377;'),
    ('\xe2\x80\x94', '-'),
    ('\xe2\x80\x93', '-'),
    ('\xf0\x9f\x94\xa5', ''),
    ('\xf0\x9f\x91\x97', ''),
    ('\xe2\x8c\x9a', ''),
    ('\xf0\x9f\x91\x9f', ''),
    ('\xe2\x9c\xa8', ''),
    ('\xf0\x9f\x9b\x8b', ''),
    ('\xe2\x9a\xa1', ''),
    ('\xf0\x9f\x94\x92', ''),
    ('\xf0\x9f\x94\x84', ''),
    ('\xf0\x9f\x8e\xa7', ''),
    ('\xf0\x9f\x9a\x9a', ''),
    ('\xc2\xb7', '&middot;'),
    ('\xe2\x80\x9c', ''),
    ('\xe2\x80\x9d', ''),
]
for bad, good in fixes:
    text = text.replace(bad, good)

# Remove Buy Now button (keep only View Details button, full-width)
text = re.sub(
    r'\s*<a href="\{%\s*url \'product_detail\' p\.id\s*%\}" class="btn-prod-cart">Buy Now</a>',
    '',
    text
)

# Make product image a clickable link
text = re.sub(
    r'(<div class="prod-card-img">)',
    r'<a href="{% url \'product_detail\' p.id %}" class="prod-card-img-link">\n        \1',
    text
)
# Close the link after prod-card-img div
text = re.sub(
    r'(</div>\n        <div class="prod-card-body">)',
    r'</div>\n        </a>\n        <div class="prod-card-body">',
    text,
    count=1
)

# Rename "Details" button text to "View Details"
text = text.replace(
    '" class="btn-prod-view">Details</a>',
    '" class="btn-prod-view">View Details</a>'
)

# Make btn-prod-view full width in CSS
text = text.replace(
    '.prod-card-actions{\n  margin-top:auto;display:flex;gap:8px;\n}',
    '.prod-card-actions{\n  margin-top:auto;\n}'
)
text = text.replace(
    '.btn-prod-view{\n  flex:1;\n  padding:10px;border-radius:12px;\n  border:1.5px solid #e5e7eb;\n  background:#fff;color:#374151;\n  font-size:12.5px;font-weight:600;\n  text-align:center;text-decoration:none;\n  transition:.2s;\n}',
    '.btn-prod-view{\n  display:block;\n  width:100%;\n  padding:11px;\n  border-radius:12px;\n  border:none;\n  background:linear-gradient(135deg,#6366f1,#8b5cf6);\n  color:#fff;\n  font-size:13px;font-weight:700;\n  text-align:center;text-decoration:none;\n  transition:.2s;\n  letter-spacing:.01em;\n}'
)
text = text.replace(
    '.btn-prod-view:hover{border-color:#6366f1;color:#6366f1;background:#f0f0ff;}',
    '.btn-prod-view:hover{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;transform:translateY(-2px);box-shadow:0 8px 20px rgba(99,102,241,.35);}'
)
# Remove unused btn-prod-cart CSS
text = re.sub(
    r'\.btn-prod-cart\{[^}]+\}\s*\.btn-prod-cart:hover\{[^}]+\}',
    '',
    text,
    flags=re.DOTALL
)

# Add prod-card-img-link CSS (display:block so it fills the space)
text = text.replace(
    '.prod-card-img{',
    '.prod-card-img-link{display:block;text-decoration:none;}\n.prod-card-img{'
)

with open(f, 'w', encoding='utf-8') as fh:
    fh.write(text)

# Verify
with open(f, encoding='utf-8') as fh:
    final = fh.read()
garbled = re.findall(r'[\u0250-\uFFFF]', final)
if garbled:
    from collections import Counter
    print('Still garbled:', Counter(garbled).most_common(5))
else:
    print('CLEAN - no garbled characters')
print('btn-prod-cart remaining:', 'btn-prod-cart' in final)
print('prod-card-img-link added:', 'prod-card-img-link' in final)
print('View Details button:', 'View Details' in final)
