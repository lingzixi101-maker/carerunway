from playwright.sync_api import sync_playwright
import os
FONT = ''.join(f'@font-face{{font-family:"DM Sans";font-weight:{w};src:url(file://{os.path.abspath(f"node_modules/@fontsource/dm-sans/files/dm-sans-latin-{w}-normal.woff2")})}}' for w in (400,500,600,700))
URL = 'file:///mnt/user-data/outputs/carerunway-prototype.html'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg = b.new_page(viewport={'width':1320,'height':900}, device_scale_factor=2, color_scheme='light')
    pg.goto(URL); pg.add_style_tag(content=FONT); pg.wait_for_timeout(700)
    pg.screenshot(path='mockup_v5_full.png', full_page=True)
    ps = b.new_page(viewport={'width':1000,'height':480}, device_scale_factor=2, color_scheme='light')
    ps.goto(URL + '#slide'); ps.add_style_tag(content=FONT); ps.wait_for_timeout(700)
    ps.screenshot(path='mockup_v5_slide.png', full_page=True)
    print(ps.evaluate('document.body.scrollHeight'))
    b.close()
