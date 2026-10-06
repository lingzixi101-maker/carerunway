import json, math, sys
import numpy as np
from shapely.geometry import shape
from model_illustrative import run, YEARS, PLANNED

SCALE = 12  # display scale for the toy load -> "seniors per clinic"
L_on, T = run(True)
L_off, _ = run(False)
disp = lambda v: int(round(v * SCALE, -1))

RAMP = {'Now': '#B9200D', 2027: '#E8321C', 2028: '#F2664A', 2029: '#F7967E', 2030: '#FBC2B2', 2031: '#FDE3DA', 'Later': '#BFCED5'}
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
           '<rect width="5" height="5" fill="#F7F9F9"/><rect width="1.3" height="5" fill="#E6EBED"/></pattern></defs>']
    sel = ''
    for name, polys in feats:
        t = town_to_pa.get(name)
        fill = RAMP[L_on.loc[t, 'gap']] if t else 'url(#nd)'
        dstr = ''.join(ring(p.exterior.coords) + ''.join(ring(i.coords) for i in p.interiors) for p in polys)
        out.append(f'<path d="{dstr}" fill="{fill}" fill-rule="evenodd" stroke="#FFFFFF" stroke-width="0.8" stroke-linejoin="round"/>')
        if name == focus.upper():
            sel = f'<path d="{dstr}" fill="none" stroke="#13232B" stroke-width="2.4" stroke-linejoin="round"/>'
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
    fx, fy = proj(103.7440, 1.3905)
    out.append(f'<text x="{fx-16:.1f}" y="{fy-18:.1f}" class="mlab halo" text-anchor="end">Choa Chu Kang</text>')
    return f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(out)}</svg>'

# ---------- focus chart: Choa Chu Kang ----------
FOCUS = 'Choa Chu Kang'
def build_chart(CW, CH):
    L, R, Tp, B = 22, 20, 30, 22
    on = [L_on.loc[FOCUS, y] * SCALE for y in YEARS]
    off = [L_off.loc[FOCUS, y] * SCALE for y in YEARS]
    th = T * SCALE
    lo, hi = min(on + off + [th]) - 25, max(on + off + [th]) + 20
    cx = lambda i: L + i * (CW - L - R) / (len(YEARS) - 1)
    cy = lambda v: Tp + (CH - Tp - B) * (1 - (v - lo) / (hi - lo))
    pts = lambda arr: ' '.join(f'{cx(i):.1f},{cy(v):.1f}' for i, v in enumerate(arr))
    ticks = ''.join(f'<text x="{cx(i):.1f}" y="{CH-5}" class="tk" text-anchor="middle">{y}</text>' for i, y in enumerate(YEARS))
    i27 = YEARS.index(2027)
    return f'''<svg viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}">
<line x1="{L}" y1="{CH-B}" x2="{CW-R}" y2="{CH-B}" stroke="#C9D2D6"/>
<line x1="{L}" y1="{cy(th):.1f}" x2="{CW-R}" y2="{cy(th):.1f}" stroke="#13232B" stroke-width="1.6" stroke-dasharray="5 4"/>
<text x="{L:.1f}" y="{cy(th)+15:.1f}" class="lg" text-anchor="start" fill="#13232B">Strain line</text>
<polyline points="{pts(off)}" fill="none" stroke="#8A989E" stroke-width="1.8" stroke-dasharray="2 3"/>
<text x="{cx(6):.1f}" y="{cy(off[6])-8:.1f}" class="lg" text-anchor="end" fill="#8A989E">Without planned clinic</text>
<polyline points="{pts(on)}" fill="none" stroke="#E8321C" stroke-width="2.6"/>
<circle cx="{cx(i27):.1f}" cy="{cy(on[i27]):.1f}" r="4.5" fill="#FFFFFF" stroke="#13232B" stroke-width="2"/>
<line x1="{cx(i27):.1f}" y1="16" x2="{cx(i27):.1f}" y2="{cy(on[i27])-6:.1f}" stroke="#13232B" stroke-width="1" stroke-dasharray="2 2"/><text x="{cx(i27):.1f}" y="11" class="ann" text-anchor="middle" fill="#13232B">Yew Tee opens</text>
{ticks}</svg>'''

# ---------- list ----------
over = ((L_on[2031] - T) / T * 100).sort_values(ascending=False)
rows = ''
for i, (t, v) in enumerate(over.head(7).items(), 1):
    gp = L_on.loc[t, 'gap']
    cls = ' class="on"' if t == FOCUS else ''
    rows += (f'<tr{cls}><td class="rk">{i}</td><td class="nm">{t}</td>'
             f'<td class="rt"><span class="bar"><i style="width:{min(100, v/55*100):.0f}%"></i></span>+{v:.0f}%</td>'
             f'<td class="yrc"><b style="background:{RAMP[gp]}"></b>{gp}</td></tr>')
legend = ''.join(f'<span><b style="background:{c}"></b>{k}</span>' for k, c in RAMP.items()) + '<span><b class="nd"></b>No data</span>'
n_more = int(sum(isinstance(g_, (int, np.integer)) for g_ in L_on.gap))

FOOT_FULL = ('Concept mockup: values come from a toy supply assumption and are not findings. Strain line = load per clinic in today\'s '
             'most-stretched quarter of areas. Population: HDB Sample Household Survey 2018 (town labels corrected, see README). '
             'Clinics: MOH 2026 announcements; locations approximate. Boundaries: URA Master Plan 2019.')
FOOT_SLIDE = ('Concept mockup, illustrative values. Strain line = load per clinic in today\'s most-stretched quarter of areas. '
              'Sources: HDB SHS 2018, MOH 2026, URA MP2019.')

def render(variant):
    tpl = open('v3_template.html').read()
    if variant == 'full':
        mp, ch, foot, cls = build_map(718, 452, 6, FOCUS), build_chart(396, 142), FOOT_FULL, ''
    else:
        mp, ch, foot, cls = build_map(490, 312, 4, FOCUS), build_chart(292, 160), FOOT_SLIDE, 'slide'
    rep = {'{{BODYCLASS}}': cls, '{{HEADLINE}}': f'{n_more} more areas cross the strain line by 2031',
           '{{MAP}}': mp, '{{CHART}}': ch, '{{ROWS}}': rows, '{{LEGEND}}': legend, '{{FOOTER}}': foot,
           '{{FNAME}}': FOCUS, '{{FBADGE}}': 'Over the line now',
           '{{F26}}': f'{disp(L_on.loc[FOCUS, 2026]):,}', '{{F31}}': f'{disp(L_on.loc[FOCUS, 2031]):,}', '{{FT}}': f'{disp(T):,}',
           '{{FNOTE}}': 'Yew Tee polyclinic (2027) pulls it under the line for about a year'}
    for k, v in rep.items(): tpl = tpl.replace(k, v)
    open(f'mockup_v3_{variant}.html', 'w').write(tpl)

render('full'); render('slide')
print('headline n =', n_more, '| threshold', round(T * SCALE))
print(L_on.gap.value_counts().to_dict())
