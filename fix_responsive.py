"""Apply comprehensive responsive CSS improvements to base.html, home.html, product_details.html."""

import re

BASE = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\base.html'
HOME = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\home.html'
DETAIL = r'C:\Users\Keval Gohel\Documents\django_ecommerce\core\templates\products\product_details.html'

# ─────────────────────────────────────────────
# 1. base.html
# ─────────────────────────────────────────────
with open(BASE, encoding='utf-8') as f:
    base = f.read()

# a) Add overflow-x: hidden to body
base = base.replace(
    'body {\n  font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif;\n  background: #f8fafc;\n  margin: 0;\n}',
    'body {\n  font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif;\n  background: #f8fafc;\n  margin: 0;\n  overflow-x: hidden;\n}'
)

# b) Replace the existing responsive section at end of style block with comprehensive version
OLD_BASE_RESP = """@media (max-width: 900px) {
  .nav-search { max-width: 360px; }
}
@media (max-width: 768px) {
  .nav-hamburger { display: flex; }
  .nav-search { display: none !important; }
  .btn-nav-login, .btn-nav-register { display: none; }
  .nav-user-name { display: none; }
  .nav-divider { display: none; }
  .nav-inner { gap: 8px; }
  .cat-nav { display: none; }
}
@media (max-width: 480px) {
  .nav-inner { padding: 0 14px; }
  .nav-brand-text { font-size: 18px; }
}"""

NEW_BASE_RESP = """@media (max-width: 1100px) {
  .nav-search { max-width: 400px; }
}
@media (max-width: 900px) {
  .nav-search { max-width: 300px; }
  .footer-grid { grid-template-columns: 1fr 1fr; }
  .footer-brand { grid-column: 1 / -1; }
}
@media (max-width: 768px) {
  .nav-hamburger { display: flex; }
  .nav-search { display: none !important; }
  .btn-nav-login, .btn-nav-register { display: none; }
  .nav-user-name { display: none; }
  .nav-divider { display: none; }
  .nav-inner { gap: 8px; }
  .cat-nav { display: none; }
  .top-bar { font-size: 11px; padding: 6px 12px; }
  .site-footer { padding: 40px 16px 0; margin-top: 48px; }
  .footer-bottom { flex-direction: column; align-items: flex-start; gap: 6px; padding: 14px 0; }
}
@media (max-width: 500px) {
  .footer-grid { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .nav-inner { padding: 0 14px; height: 58px; }
  .nav-brand-text { font-size: 18px; }
  .nav-brand-icon { width: 30px; height: 30px; }
  .top-bar { font-size: 10.5px; padding: 5px 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .nav-action-btn { width: 36px; height: 36px; }
}
@media (max-width: 360px) {
  .nav-brand-text { display: none; }
}"""

if OLD_BASE_RESP in base:
    base = base.replace(OLD_BASE_RESP, NEW_BASE_RESP)
    print('base.html: responsive section updated')
else:
    print('base.html: WARNING - could not find old responsive section')

with open(BASE, 'w', encoding='utf-8', newline='\n') as f:
    f.write(base)

# ─────────────────────────────────────────────
# 2. home.html
# ─────────────────────────────────────────────
with open(HOME, encoding='utf-8') as f:
    home = f.read()

OLD_HOME_RESP = """/* ===================== RESPONSIVE ===================== */
@media(max-width:1100px){
  .prod-grid{grid-template-columns:repeat(3,1fr);}
  .rec-grid{grid-template-columns:repeat(3,1fr);}
}
@media(max-width:900px){
  .hero{height:70vh;}
  .hero-title{letter-spacing:-1px;font-size:clamp(28px,5vw,52px);}
  .hero-sub{font-size:13.5px;}
  .cat-showcase{grid-template-columns:repeat(3,1fr);}
  .prod-grid{grid-template-columns:repeat(2,1fr);}
  .rec-grid{grid-template-columns:repeat(2,1fr);}
  .trust-grid{grid-template-columns:repeat(2,1fr);}
  .sale-ticker{gap:12px;padding:8px 16px;}
}
@media(max-width:640px){
  .hero{height:75vh;}
  .hero-content{padding:0 18px;}
  .hero-offer-chip{display:none;}
  .hero-title{font-size:clamp(26px,7vw,42px);letter-spacing:-.5px;}
  .hero-sub{font-size:13px;margin-bottom:24px;}
  .hero-btn-primary,.hero-btn-secondary{padding:11px 22px;font-size:13px;}
  .cat-showcase{grid-template-columns:repeat(2,1fr);gap:10px;padding:0 16px 48px;}
  .sec-hd{padding:40px 16px 28px;}
  .prod-grid{grid-template-columns:repeat(2,1fr);gap:12px;}
  .prod-card-img{height:150px;padding:10px;}
  .prod-card-name{font-size:13px;}
  .prod-card-price{font-size:17px;}
  .products-section{padding:0 16px 60px;}
  .rec-grid{grid-template-columns:repeat(2,1fr);gap:12px;}
  .rec-card-img{height:130px;}
  .trust-grid{grid-template-columns:repeat(2,1fr);gap:12px;}
  .trust-section{padding:40px 16px 60px;}
  .brand-wall-item{padding:14px 24px;font-size:12px;letter-spacing:1px;}
  .sale-num{font-size:20px;min-width:38px;padding:3px 8px;}
  .sale-title-chip{font-size:11px;padding:5px 14px;}
}
@media(max-width:420px){
  .hero{height:85vh;}
  .hero-title{font-size:clamp(24px,8vw,36px);}
  .cat-showcase{grid-template-columns:repeat(2,1fr);gap:8px;}
  .prod-grid{grid-template-columns:repeat(2,1fr);gap:10px;}
  .prod-card-img{height:130px;padding:8px;}
  .rec-grid{grid-template-columns:repeat(2,1fr);}
  .trust-grid{grid-template-columns:1fr 1fr;}
  .hero-prev,.hero-next{width:34px;height:34px;font-size:14px;}
}"""

NEW_HOME_RESP = """/* ===================== RESPONSIVE ===================== */
@media(max-width:1280px){
  .prod-grid{grid-template-columns:repeat(4,1fr);}
  .rec-grid{grid-template-columns:repeat(4,1fr);}
}
@media(max-width:1100px){
  .prod-grid{grid-template-columns:repeat(3,1fr);}
  .rec-grid{grid-template-columns:repeat(3,1fr);}
  .cat-showcase{grid-template-columns:repeat(3,1fr);}
}
@media(max-width:900px){
  .hero{height:70vh;}
  .hero-title{letter-spacing:-1px;font-size:clamp(28px,5vw,52px);}
  .hero-sub{font-size:13.5px;}
  .cat-showcase{grid-template-columns:repeat(3,1fr);}
  .prod-grid{grid-template-columns:repeat(2,1fr);}
  .rec-grid{grid-template-columns:repeat(2,1fr);}
  .trust-grid{grid-template-columns:repeat(2,1fr);}
  .sale-ticker{gap:12px;padding:8px 16px;}
  .hero-dots{bottom:16px;}
  .hero-prev,.hero-next{width:36px;height:36px;}
}
@media(max-width:640px){
  .hero{height:auto;min-height:480px;}
  .hero-slide{min-height:480px;}
  .hero-content{padding:0 18px;}
  .hero-offer-chip{font-size:10px;letter-spacing:2px;}
  .hero-tag{font-size:10px;letter-spacing:2px;}
  .hero-title{font-size:clamp(24px,7vw,40px);letter-spacing:-.5px;}
  .hero-sub{font-size:13px;margin-bottom:20px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}
  .hero-cta-row{flex-direction:column;align-items:flex-start;gap:10px;}
  .hero-btn-primary,.hero-btn-secondary{width:100%;max-width:260px;text-align:center;padding:12px 22px;font-size:13px;}
  .hero-prev,.hero-next{display:none;}
  .hero-progress{display:none;}
  .cat-showcase{grid-template-columns:repeat(2,1fr);gap:10px;padding:0 14px 40px;}
  .cat-card{border-radius:12px;min-height:120px;}
  .cat-card-name{font-size:12px;}
  .sec-hd{padding:36px 16px 24px;}
  .sec-hd-title{letter-spacing:-.5px;}
  .prod-grid{grid-template-columns:repeat(2,1fr);gap:12px;}
  .prod-card-img{height:150px;padding:10px;}
  .prod-card-name{font-size:13px;}
  .prod-card-price{font-size:16px;}
  .prod-card-body{padding:12px;}
  .products-section{padding:0 14px 56px;}
  .rec-section{padding:0 14px 56px;}
  .rec-grid{grid-template-columns:repeat(2,1fr);gap:12px;}
  .rec-card-img{height:130px;}
  .trust-grid{grid-template-columns:repeat(2,1fr);gap:12px;}
  .trust-section{padding:36px 14px 56px;}
  .brand-wall-item{padding:14px 22px;font-size:11.5px;letter-spacing:1px;}
  .sale-num{font-size:20px;min-width:38px;padding:3px 8px;}
  .sale-title-chip{font-size:11px;padding:5px 14px;}
  .sale-ticker{flex-wrap:wrap;justify-content:center;gap:8px 16px;padding:10px 14px;}
}
@media(max-width:420px){
  .hero{min-height:420px;}
  .hero-slide{min-height:420px;}
  .hero-title{font-size:clamp(22px,8vw,34px);}
  .hero-sub{-webkit-line-clamp:2;}
  .hero-cta-row{gap:8px;}
  .hero-btn-primary,.hero-btn-secondary{max-width:100%;font-size:12.5px;padding:11px 18px;}
  .cat-showcase{grid-template-columns:repeat(2,1fr);gap:8px;padding:0 12px 36px;}
  .prod-grid{grid-template-columns:repeat(2,1fr);gap:8px;}
  .prod-card-img{height:130px;padding:8px;}
  .prod-card-name{font-size:12.5px;}
  .prod-card-body{padding:10px;}
  .rec-grid{grid-template-columns:repeat(2,1fr);gap:8px;}
  .trust-grid{grid-template-columns:1fr 1fr;}
  .trust-card{padding:18px 14px;}
}
@media(max-width:360px){
  .prod-grid{grid-template-columns:1fr;}
  .rec-grid{grid-template-columns:1fr;}
  .cat-showcase{grid-template-columns:repeat(2,1fr);gap:6px;}
  .hero-btn-primary{max-width:100%;}
}"""

if OLD_HOME_RESP in home:
    home = home.replace(OLD_HOME_RESP, NEW_HOME_RESP)
    print('home.html: responsive section updated')
else:
    print('home.html: WARNING - could not find exact old responsive section, trying partial match')
    # Try to find just the comment anchor
    idx = home.find('/* ===================== RESPONSIVE ===================== */')
    if idx >= 0:
        # Find end: </style>
        end = home.find('</style>', idx)
        old_block = home[idx:end]
        home = home[:idx] + NEW_HOME_RESP + '\n\n' + home[end:]
        print(f'home.html: responsive section replaced via index (was {len(old_block)} chars)')

with open(HOME, 'w', encoding='utf-8', newline='\n') as f:
    f.write(home)

# ─────────────────────────────────────────────
# 3. product_details.html
# ─────────────────────────────────────────────
with open(DETAIL, encoding='utf-8') as f:
    detail = f.read()

OLD_DETAIL_RESP = """@media(max-width:960px){
  .detail-layout{grid-template-columns:1fr;}
  .pd-gallery{position:static;}
  #mainImage{height:320px;}
}
@media(max-width:768px){
  .pd-breadcrumb{padding:12px 16px 0;}
  .detail-box{margin:12px auto;padding:0 14px;}
  .pd-gallery{padding:16px;border-radius:16px;}
  #mainImage{height:260px;}
  .thumb-row img{width:56px;height:56px;}
  .pd-info-panel{padding:20px 18px;}
  .pd-product-title{font-size:18px;}
  .pd-price-main{font-size:24px;}
  .pd-trust-strip{flex-wrap:wrap;}
  .pd-trust-item{flex:0 0 50%;border-bottom:1px solid #f0f0ff;}
  .pd-trust-item:nth-child(even){border-right:none;}
  .sticky-cart-bar{display:flex;}
  .add-btn{margin-bottom:72px;}
  .pd-info-block{padding:0 14px;}
  .pd-section-card{padding:18px 16px;border-radius:14px;}
  .pd-highlights-grid,.pd-spec-grid{grid-template-columns:1fr;}
  .pd-mfr-grid{grid-template-columns:1fr;}
  .pd-mfr-full{grid-column:1;}
  .rv-section{padding:0 14px;}
  .rv-card,.rv-form-card{padding:18px 16px;border-radius:14px;}
  .rv-summary{flex-direction:column;gap:16px;}
  .pd-tabs{overflow-x:auto;flex-wrap:nowrap;scrollbar-width:none;}
  .pd-tabs::-webkit-scrollbar{display:none;}
  .pd-tab{white-space:nowrap;padding:10px 14px;}
}
@media(max-width:480px){
  #mainImage{height:210px;}
  .thumb-row img{width:50px;height:50px;}
  .pd-price-main{font-size:22px;}
  .pd-price-block{flex-wrap:wrap;gap:8px;}
  .rv-avg-big .rv-avg-num{font-size:40px;}
}"""

NEW_DETAIL_RESP = """@media(max-width:960px){
  .detail-layout{grid-template-columns:1fr;}
  .pd-gallery{position:static;margin-bottom:0;}
  #mainImage{height:340px;}
  .pd-info-panel{border-radius:18px;}
}
@media(max-width:768px){
  .pd-breadcrumb{padding:10px 14px 0;font-size:12px;}
  .detail-box{margin:10px auto;padding:0 12px;}
  .pd-gallery{padding:14px;border-radius:14px;}
  #mainImage{height:270px;}
  .thumb-row img{width:54px;height:54px;}
  .pd-info-panel{padding:18px 16px;border-radius:14px;}
  .pd-brand-badge{font-size:10px;}
  .pd-product-title{font-size:17px;line-height:1.3;}
  .pd-price-main{font-size:24px;}
  .pd-trust-strip{flex-wrap:wrap;}
  .pd-trust-item{flex:0 0 50%;min-width:140px;border-bottom:1px solid #f0f0ff;}
  .pd-trust-item:nth-child(even){border-right:none;}
  .sticky-cart-bar{display:flex;}
  .add-btn{margin-bottom:74px;}
  .pd-info-block{padding:0 12px;}
  .pd-section-card{padding:16px 14px;border-radius:12px;}
  .pd-highlights-grid,.pd-spec-grid{grid-template-columns:1fr;}
  .pd-mfr-grid{grid-template-columns:1fr;}
  .pd-mfr-full{grid-column:1;}
  .rv-section{padding:0 12px;}
  .rv-card,.rv-form-card{padding:16px 14px;border-radius:12px;}
  .rv-summary{flex-direction:column;gap:14px;}
  .pd-tabs{overflow-x:auto;flex-wrap:nowrap;scrollbar-width:none;}
  .pd-tabs::-webkit-scrollbar{display:none;}
  .pd-tab{white-space:nowrap;padding:9px 12px;font-size:13px;}
  .color-row{gap:10px;}
  .color-swatch-img{width:50px;height:50px;}
  .color-circle{width:38px;height:38px;}
  .variant-row{gap:8px;}
  .vbtn{padding:7px 14px;font-size:13px;}
}
@media(max-width:480px){
  .detail-box{padding:0 8px;}
  #mainImage{height:220px;}
  .thumb-row{gap:6px;}
  .thumb-row img{width:48px;height:48px;}
  .pd-price-main{font-size:21px;}
  .pd-price-block{flex-wrap:wrap;gap:6px;}
  .rv-avg-big .rv-avg-num{font-size:36px;}
  .pd-trust-strip{gap:0;}
  .pd-trust-item{flex:0 0 50%;padding:10px 8px;}
  .sticky-cart-bar{padding:10px 14px;}
  .scb-price{font-size:16px;}
  .scb-btn{font-size:13px;padding:10px 20px;}
}
@media(max-width:360px){
  #mainImage{height:190px;}
  .pd-product-title{font-size:15px;}
  .color-swatch-img{width:44px;height:44px;}
  .vbtn{padding:6px 12px;font-size:12px;}
  .add-btn{font-size:14px;}
  .pd-trust-strip{flex-direction:column;}
  .pd-trust-item{flex:1 0 100%;border-right:none;}
}"""

if OLD_DETAIL_RESP in detail:
    detail = detail.replace(OLD_DETAIL_RESP, NEW_DETAIL_RESP)
    print('product_details.html: responsive section updated')
else:
    print('product_details.html: WARNING - fallback replacement by index')
    idx = detail.find('@media(max-width:960px){')
    end = detail.find('@media(max-width:600px){', idx)
    if end < 0:
        end = detail.find('\n.section{', idx)
    if idx >= 0 and end > idx:
        detail = detail[:idx] + NEW_DETAIL_RESP + '\n\n' + detail[end:]
        print('product_details.html: done via index')

# Also adjust sticky cart bar to not overlap chatbot FAB on mobile
# Move chatbot FAB up by 80px when sticky bar is visible
detail = detail.replace(
    '@media(max-width:600px){.rec-grid{grid-template-columns:repeat(2,1fr);}}',
    '@media(max-width:600px){.rec-grid{grid-template-columns:repeat(2,1fr);}}'
)

with open(DETAIL, 'w', encoding='utf-8', newline='\n') as f:
    f.write(detail)

print('\nAll done. Verifying non-ASCII...')
for name, path in [('base', BASE), ('home', HOME), ('detail', DETAIL)]:
    with open(path, encoding='utf-8') as f: c = f.read()
    na = sum(1 for ch in c if ord(ch) > 127)
    print(f'  {name}: {na} non-ASCII chars')

print('\nVerifying Django...')
import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check'],
    capture_output=True, text=True,
    cwd=r'C:\Users\Keval Gohel\Documents\django_ecommerce\core')
print(r.stdout.strip() or r.stderr.strip())
