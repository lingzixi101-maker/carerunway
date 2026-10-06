from playwright.sync_api import sync_playwright
import os, sys
FONT = ''.join(f'@font-face{{font-family:"DM Sans";font-weight:{w};src:url(file://{os.path.abspath(f"node_modules/@fontsource/dm-sans/files/dm-sans-latin-{w}-normal.woff2")})}}' for w in (400,500,600,700))
URL = 'file:///mnt/user-data/outputs/carerunway-prototype.html'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg = b.new_page(viewport={'width':1440,'height':900}, device_scale_factor=2)
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL + '#clean'); pg.add_style_tag(content=FONT); pg.wait_for_timeout(700)
    print('height', pg.evaluate('document.body.scrollHeight'))
    pg.screenshot(path='mock6_full.png', full_page=True)
    pg.click('#planned'); pg.wait_for_timeout(200); pg.screenshot(path='mock6_off.png', full_page=True)
    m = b.new_page(viewport={'width':390,'height':844}); m.goto(URL); m.wait_for_timeout(500)
    print('mobile width', m.evaluate('document.documentElement.scrollWidth'))
    print('errors', errs); b.close()
