f = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\base.html'
with open(f, encoding='utf-8') as fh:
    c = fh.read()

print('Google Fonts removed:', 'fonts.googleapis.com' not in c)
print('System fonts:', 'Segoe UI' in c)
print('Mobile hamburger CSS:', 'nav-hamburger' in c)
print('Mobile drawer HTML:', 'mobile-nav-drawer' in c)
print('Hamburger button:', 'mobileNavBtn' in c)
print('toggleMobileNav JS:', 'toggleMobileNav' in c)
print('Top bar rupee entity:', '&#8377;499' in c)
print('cb-close fixed:', 'class="cb-close"' in c)
print('Broken cb-close gone:', '="cb-close"' not in c)
print('Non-ASCII lines:', sum(1 for line in c.split('\n') if any(ord(ch)>127 for ch in line)))
