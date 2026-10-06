import json, math
import numpy as np
from shapely.geometry import shape
import model_v4 as m

L_on, L_off, LINE, YEARS = m.L_on, m.L_off, m.LINE, m.YEARS

def recs_for(include_planned):
    base = (m.loads(include_planned) * m.SCALE)
    out = []
    for t in m.d.index:
        w = m.loads(include_planned, (t, 2028, 1.15)) * m.SCALE
        gain, yrs = 0, 0
        for y in YEARS:
            if y < 2028: continue
            if base.loc[t, y] >= LINE and w.loc[t, y] < LINE:
                gain += m.seniors(m.d.loc[t], y); yrs += 1
        if gain: out.append({'town': t, 'seniors': int(round(gain / yrs, -2)), 'years': yrs})
    return sorted(out, key=lambda r: -r['seniors'] * r['years'])[:3]

VERD = {'Ahead of need': 'Opens before it is needed'}
towns = {}
for t in m.d.index:
    towns[t] = {'on': [round(float(L_on.loc[t, y])) for y in YEARS], 'off': [round(float(L_off.loc[t, y])) for y in YEARS],
                'yon': str(L_on.loc[t, 'year']), 'yoff': str(L_off.loc[t, 'year']),
                'seniors26': int(round(m.seniors(m.d.loc[t], 2026), -2)), 'seniors31': int(round(m.seniors(m.d.loc[t], 2031), -2)),
                'seniors': [int(round(m.seniors(m.d.loc[t], y), -2)) for y in YEARS]}
checks = [{'town': t, 'site': s, 'opens': y, 'verdict': VERD.get(v, v)} for t, s, y, v in m.checks]

# geometry projected to a fixed viewBox
g = json.load(open('pa_hi.geojson'))
kx = math.cos(math.radians(1.35))
feats = []
for f in g['features']:
    shp = shape(f['geometry']).simplify(0.00025, preserve_topology=True)
    polys = [p for p in ([shp] if shp.geom_type == 'Polygon' else list(shp.geoms)) if p.area > 2e-6]
    if polys: feats.append((f['properties']['name'], polys))
xs = [lon * kx for _, ps in feats for p in ps for lon, lat in p.exterior.coords]
ys = [-lat for _, ps in feats for p in ps for lon, lat in p.exterior.coords]
W, H, PAD = 720, 452, 6
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
s = min((W - 2 * PAD) / (maxx - minx), (H - 2 * PAD) / (maxy - miny))
ox = PAD + ((W - 2 * PAD) - (maxx - minx) * s) / 2; oy = PAD + ((H - 2 * PAD) - (maxy - miny) * s) / 2
proj = lambda lon, lat: (round(ox + (lon * kx - minx) * s, 1), round(oy + (-lat - miny) * s, 1))
ring = lambda cs: 'M' + 'L'.join(f'{x},{y}' for x, y in (proj(a, b) for a, b in cs)) + 'Z'
pa2town = {t.upper(): t for t in m.d.index}
pa2town.update({'KALLANG': 'Kallang/Whampoa', 'DOWNTOWN CORE': 'Central Area', 'OUTRAM': 'Central Area', 'ROCHOR': 'Central Area'})
areas = [{'pa': n.title(), 'town': pa2town.get(n), 'd': ''.join(ring(p.exterior.coords) + ''.join(ring(i.coords) for i in p.interiors) for p in ps)} for n, ps in feats]
from shapely.ops import unary_union
land = unary_union([p.buffer(0.00015) for _, ps in feats for p in ps]).buffer(-0.00015)
land_polys = [land] if land.geom_type == 'Polygon' else list(land.geoms)
coast = ''.join(ring(p.exterior.coords) for p in land_polys if p.area > 2e-6)
existing = [(1.3743,103.8454),(1.3196,103.8872),(1.3700,103.8920),(1.3263,103.8573),(1.4180,103.8330),(1.3350,103.8485),(1.4370,103.7890),(1.4300,103.8360),(1.4410,103.8010),(1.3500,103.7510),(1.3830,103.7450),(1.3150,103.7640),(1.3470,103.7300),(1.3375,103.6975),(1.2980,103.8020),(1.3800,103.7630),(1.3570,103.7360),(1.3260,103.9300),(1.2790,103.8240),(1.3190,103.9030),(1.3030,103.9070),(1.2800,103.8400),(1.3730,103.9500),(1.4040,103.9050),(1.3920,103.8950),(1.3530,103.9430),(1.3650,103.9380),(1.3530,103.8720)]
planned = [('Bidadari', 1.3395, 103.8715), ('Kaki Bukit', 1.3355, 103.9085), ('Yew Tee', 1.3975, 103.7470), ('Taman Jurong', 1.3345, 103.7205)]
REC_XY = {'Jurong West': (1.3440, 103.7040), 'Hougang': (1.3712, 103.8860), 'Choa Chu Kang': (1.3860, 103.7520), 'Sengkang': (1.3900, 103.8950),
          'Bukit Batok': (1.3530, 103.7600), 'Bukit Panjang': (1.3780, 103.7700), 'Punggol': (1.4000, 103.9100), 'Yishun': (1.4250, 103.8400),
          'Woodlands': (1.4400, 103.7880), 'Tampines': (1.3500, 103.9500), 'Pasir Ris': (1.3720, 103.9500), 'Sembawang': (1.4490, 103.8200), 'Bedok': (1.3300, 103.9280)}
reg = {f['properties']['PLN_AREA_N'].title(): f['properties']['REGION_N'].split()[0].title() for f in json.load(open('pa.geojson'))['features']}
for a in areas: a['region'] = reg.get(a['pa'], '')
data = {'years': YEARS, 'line': round(LINE), 'avg26': round(float(L_on[2026].mean())), 'towns': towns, 'checks': checks,
        'recs': {'on': recs_for(True), 'off': recs_for(False)}, 'areas': areas,
        'existing': [proj(lon, lat) for lat, lon in existing],
        'planned': [{'site': n, 'xy': proj(lon, lat)} for n, lat, lon in planned], 'delayed': proj(103.8485, 1.3508),
        'recxy': {t: proj(lon, lat) for t, (lat, lon) in REC_XY.items()}, 'W': W, 'H': H, 'coast': coast, 'mult': 1.15}
json.dump(data, open('proto_data.json', 'w'), separators=(',', ':'))
print(data['recs'], data['avg26'], data['line'])
print([c for c in checks])
