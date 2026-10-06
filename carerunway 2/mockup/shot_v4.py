from playwright.sync_api import sync_playwright
import os
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    for v,w,h in [('full',1280,780),('slide',900,500)]:
        pg=b.new_page(viewport={'width':w,'height':h},device_scale_factor=2)
        pg.goto('file://'+os.path.abspath(f'mockup_v4_{v}.html')); pg.wait_for_timeout(500)
        pg.screenshot(path=f'mockup_v4_{v}.png'); pg.close()
    b.close()
