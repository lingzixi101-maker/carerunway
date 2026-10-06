import json, math, sys
import numpy as np
from shapely.geometry import shape
from model_v4 import L_on, L_off, LINE, YEARS, sites, checks, seniors, d

T = LINE
RAMP = {'Now': '#B9200D', 2027: '#E8321C', 2028: '#F2664A', 2029: '#F7967E', 2030: '#FBC2B2', 2031: '#FDE3DA', 'Later': '#BFCED5'}
LABEL = {'Later': 'Not by 2031'}
town_to_pa = {t.upper(): t for t in L_on.index}
town_to_pa.update({'KALLANG': 'Kallang/Whampoa', 'DOWNTOWN CORE': 'Central Area', 'OUTRAM': 'Central Area', 'ROCHOR': 'Central Area'})

# ---------- map ----------
g = json.load(open('pa_hi.geojson'))
feats = []
for f in g['features']:
    shp = shape(f['geometry']).simplify(0.00025, preserve_topology=True)
    polys = [p for p in ([shp] if shp.geom_type == 'Polygon' else list(shp.geoms)) if p.area > 2e-6]
    if polys: feats.append((f['properties']['name'], polys))
kx = math.cos(math.radians(1.35))
xs, ys = [], []
for _, polys in feats:
    for p in polys:
        for lon, lat in p.exterior.coords: xs.append(lon * kx); ys.append(-lat)
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

def build_map(W, H, PAD, focus):
    s = min((W - 2 * PAD) / (maxx - minx), (H - 2 * PAD) / (maxy - miny))
    ox = PAD + ((W - 2 * PAD) - (maxx - minx) * s) / 2
    oy = PAD + ((H - 2 * PAD) - (maxy - miny) * s) / 2
    proj = lambda lon, lat: (ox + (lon * kx - minx) * s, oy + (-lat - miny) * s)
    ring = lambda cs: 'M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in (proj(a, b) for a, b in cs)) + 'Z'
    out = ['<defs><pattern id="nd" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<rect width="5" height="5" fill="#F8FAFA"/><rect width="1.1" height="5" fill="#EAEEF0"/></pattern></defs>']
    sel = ''
    for name, polys in feats:
        t = town_to_pa.get(name)
        fill = RAMP[L_on.loc[t, 'year']] if t else 'url(#nd)'
        dstr = ''.join(ring(p.exterior.coords) + ''.join(ring(i.coords) for i in p.interiors) for p in polys)
        out.append(f'<path d="{dstr}" fill="{fill}" fill-rule="evenodd" stroke="#FFFFFF" stroke-width="0.8" stroke-linejoin="round"/>')
    out.append(sel)
    # existing polyclinics (approximate locations; replace with official coordinates in build)
    existing = [(1.3743,103.8454),(1.3196,103.8872),(1.3700,103.8920),(1.3263,103.8573),(1.4180,103.8330),(1.3350,103.8485),
                (1.4370,103.7890),(1.4300,103.8360),(1.4410,103.8010),(1.3500,103.7510),(1.3830,103.7450),(1.3150,103.7640),
                (1.3470,103.7300),(1.3375,103.6975),(1.2980,103.8020),(1.3800,103.7630),(1.3570,103.7360),(1.3260,103.9300),
                (1.2790,103.8240),(1.3190,103.9030),(1.3030,103.9070),(1.2800,103.8400),(1.3730,103.9500),(1.4040,103.9050),
                (1.3920,103.8950),(1.3530,103.9430),(1.3650,103.9380),(1.3530,103.8720)]
    for lat, lon in existing:
        x, y = proj(lon, lat)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#FFFFFF" stroke="#13232B" stroke-width="1.8"/>')
    planned = [(1.3395, 103.8715), (1.3355, 103.9085), (1.3975, 103.7470), (1.3345, 103.7205)]
    for lat, lon in planned:
        x, y = proj(lon, lat)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#13232B" stroke="#FFFFFF" stroke-width="2"/>')
    x, y = proj(103.8485, 1.3508)
    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#FFFFFF" stroke="#13232B" stroke-width="1.8" stroke-dasharray="3 2.2"/>')
    REC_XY = {'Jurong West': (1.3440, 103.7040), 'Hougang': (1.3712, 103.8860), 'Choa Chu Kang': (1.3860, 103.7520),
              'Sengkang': (1.3900, 103.8950), 'Bukit Batok': (1.3530, 103.7600), 'Bukit Panjang': (1.3780, 103.7700)}
    for i, t in enumerate(TOP3, 1):
        lat, lon = REC_XY[t]; x, y = proj(lon, lat)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="#E8321C" stroke="#FFFFFF" stroke-width="2.2"/>'
                   f'<text x="{x:.1f}" y="{y+4.3:.1f}" text-anchor="middle" style="font-size:12px;font-weight:700;fill:#fff">{i}</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(out)}</svg>'

TOP3 = list(sites.index[:3])
NOTES = {'Jurong West': 'or bring Taman Jurong forward from 2030', 'Hougang': 'no new clinic planned',
         'Choa Chu Kang': 'a second site after Yew Tee', 'Sengkang': 'no new clinic planned'}
recs = ''
for i, t in enumerate(TOP3, 1):
    r = sites.loc[t]
    avg = int(round(r.senior_years / r.years, -3))
    recs += (f'<tr><td class="n"><i>{i}</i></td><td class="a"><b>{t}</b><small>{NOTES.get(t, "")}</small></td>'
             f'<td class="m"><b>{avg:,} seniors</b><small>adequately served for {int(r.years)} more yrs</small></td></tr>')
CLS = lambda v: 'c-bad' if ('late' in v or 'hurts' in v) else ('c-good' if v in ('On target',) or v.startswith('Buys') else 'c-mid')
chk = ''
for town, site, yr, v in checks:
    chk += f'<tr><td class="nm" style="width:auto"><b style="font-weight:600">{site}</b> <span style="color:#8A989E;font-size:12px">{town}</span></td><td class="rt">{yr}</td><td class="vd"><span class="chip {CLS(v)}">{v}</span></td></tr>'
legend = ''.join(f'<span><b style="background:{c}"></b>{LABEL.get(k, k)}</span>' for k, c in RAMP.items()) + '<span><b class="nd"></b>Non-residential</span>'
n_under = int(sum(L_on.year != 'Later'))

FOOT_FULL = ('Concept mockup: illustrative values from a toy supply model calibrated to ~330 seniors per clinic (real national figure in 2022: 293). '
             'Under-served = more seniors per clinic than today\'s worst-served quarter of areas. Population: HDB Sample Household Survey 2018, '
             'town labels corrected. Clinics: MOH 2026 announcements; locations approximate. Boundaries: URA Master Plan 2019.')
FOOT_SLIDE = ('Concept mockup, illustrative values. Under-served = more seniors per clinic than today\'s worst-served quarter of areas. '
              'Sources: HDB SHS 2018, MOH 2026, URA MP2019.')
def render(variant):
    tpl = open('v4_template.html').read()
    if variant == 'full':
        mp, foot, cls = build_map(718, 452, 6, ''), FOOT_FULL, ''
    else:
        mp, foot, cls = build_map(440, 282, 4, ''), FOOT_SLIDE, 'slide'
    rep = {'{{BODYCLASS}}': cls, '{{HEADLINE}}': f'{n_under} areas will be under-served by 2031',
           '{{MAP}}': mp, '{{RECS}}': recs, '{{CHECKS}}': chk, '{{LEGEND}}': legend, '{{FOOTER}}': foot,
           '{{AVG}}': str(int(round(L_on[2026].mean()))), '{{LINE}}': str(int(round(LINE)))}
    for k, v in rep.items(): tpl = tpl.replace(k, v)
    open(f'mockup_v4_{variant}.html', 'w').write(tpl)

render('full'); render('slide')
print(TOP3, n_under)
