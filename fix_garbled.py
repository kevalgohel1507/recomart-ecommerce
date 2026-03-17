"""
Fix garbled (double/triple encoded) UTF-8 characters in home.html.
Reads the file as raw bytes, applies undo-encoding logic, saves clean UTF-8.
"""
import re, sys

HOME = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\home.html'

# Read raw bytes
with open(HOME, 'rb') as f:
    raw = f.read()

# Decode as UTF-8 to get the "middle" (still garbled) string
text = raw.decode('utf-8')

# -----------------------------------------------------------------------
# Strategy: For each line with non-ASCII, try to undo one level of
# latin-1 mis-encoding: encode the suspicious chars back to bytes as
# latin-1, then re-decode as UTF-8.  Do this up to 3 times.
# -----------------------------------------------------------------------
def try_undo(s):
    """Try to undo one layer of UTF-8-as-latin-1 encoding."""
    # Collect consecutive "mojibake" chars (U+0080-U+00FF + control 0x80-0x9F)
    # and try to decode them as UTF-8 bytes
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        cp = ord(c)
        # Candidate start of mojibake sequence
        if 0x00C0 <= cp <= 0x00FF:
            # Grab a run of chars that could be latin-1 encoded UTF-8 bytes
            run = []
            j = i
            while j < len(s):
                cc = ord(s[j])
                if 0x0080 <= cc <= 0x00FF:
                    run.append(cc)
                    j += 1
                else:
                    break
            if run:
                b = bytes(run)
                try:
                    decoded = b.decode('utf-8')
                    out.append(decoded)
                    i = j
                    continue
                except UnicodeDecodeError:
                    # Partial decode: try subsets
                    best = 1
                    for l in range(len(run), 0, -1):
                        try:
                            decoded = bytes(run[:l]).decode('utf-8')
                            out.append(decoded)
                            i += l
                            best = 0
                            break
                        except UnicodeDecodeError:
                            continue
                    if best:
                        out.append(c)
                        i += 1
                    continue
        out.append(c)
        i += 1
    return ''.join(out)

def fix_text(s, max_iters=4):
    for _ in range(max_iters):
        new_s = try_undo(s)
        if new_s == s:
            break
        s = new_s
    return s

# Apply fix line by line (only to lines with non-ASCII)
lines = text.split('\n')
fixed_lines = []
changes = 0
for line in lines:
    if any(ord(c) > 127 for c in line):
        fixed = fix_text(line)
        if fixed != line:
            changes += 1
        fixed_lines.append(fixed)
    else:
        fixed_lines.append(line)

text = '\n'.join(fixed_lines)

# -----------------------------------------------------------------------
# Now do symbol replacements with HTML entities
# -----------------------------------------------------------------------
replacements = [
    ('₹', '&#8377;'),
    ('\u20B9', '&#8377;'),   # rupee sign (clean form)
    ('→', '&rarr;'),
    ('←', '&larr;'),
    ('—', '&mdash;'),
    ('–', '&ndash;'),
    ('·', '&middot;'),
    ('•', '&bull;'),
    ('©', '&copy;'),
    ('®', '&reg;'),
    ('™', '&trade;'),
    ('°', '&deg;'),
    ('×', '&times;'),
    ('÷', '&divide;'),
    ('«', '&laquo;'),
    ('»', '&raquo;'),
]
for old, new in replacements:
    text = text.replace(old, new)

# -----------------------------------------------------------------------
# Remove remaining non-ASCII (emojis) — replace with empty string
# Preserve: a-z, A-Z, 0-9, ASCII punctuation + HTML safe entities above
# -----------------------------------------------------------------------
# Keep only ASCII + a few safe ranges
def clean_non_ascii(match):
    return ''

# Remove isolated non-ASCII characters (leftover emojis / garbled)
text = re.sub(r'[^\x00-\x7F]+', '', text)

# -----------------------------------------------------------------------
# Fix specific known broken patterns that survive above
# -----------------------------------------------------------------------
# Hero tag / chip dashes  
text = text.replace(' - Up to', ' &mdash; Up to')

# -----------------------------------------------------------------------
# Fix trust icons that lost their emoji (replace empty trust-icon divs with SVG)
# -----------------------------------------------------------------------
SECURE_SVG = '<svg width="24" height="24" fill="none" stroke="#5b21b6" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
RETURN_SVG  = '<svg width="24" height="24" fill="none" stroke="#166534" stroke-width="2" viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-5"/></svg>'

# Replace the two trust-icon divs that had emoji (secure payment + easy returns)
text = text.replace(
    '<div class="trust-icon" style="background:#dcfce7;"></div>',
    f'<div class="trust-icon" style="background:#dcfce7;">{RETURN_SVG}</div>'
)
text = text.replace(
    '<div class="trust-icon" style="background:#ede9fe;"></div>',
    f'<div class="trust-icon" style="background:#ede9fe;">{SECURE_SVG}</div>'
)

# -----------------------------------------------------------------------
# Fix JS hero slide chip text (remove empty leading symbols after ASCII strip)
# -----------------------------------------------------------------------
# Pattern:  {chip:' Electronics  Up to 45% Off'}  → clean up double spaces
text = re.sub(r"\{chip:'(\s*)(\w[^']+)'\}", lambda m: "{chip:'" + m.group(2).strip() + "'}", text)

# -----------------------------------------------------------------------
# Verify
# -----------------------------------------------------------------------
non_ascii = re.findall(r'[^\x00-\x7F]', text)
print(f"Lines fixed: {changes}")
print(f"Remaining non-ASCII chars: {len(non_ascii)}")
if non_ascii:
    print("Sample:", repr(non_ascii[:20]))

# Save
with open(HOME, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print("Saved OK.")
