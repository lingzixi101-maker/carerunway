"""Illustrative-only numbers for the draft 4 mockup (NOT findings).
Corrected HDB 2018 town counts + a toy supply assumption, calibrated so the
2026 town average is ~330 seniors per clinic (real 2022 national figure: 293)."""
import pandas as pd, numpy as np
h = pd.read_csv('data/HDBElderlyandFutureElderlyResidentPopulationbyGeographicalDistribution.csv')
h['idx'] = h.groupby(['shs_year', 'elderly_pop']).cumcount()
FIX = {7: 'Woodlands', 8: 'Choa Chu Kang', 9: 'Bukit Batok', 10: 'Bukit Panjang',
       11: 'Jurong East', 12: 'Serangoon', 13: 'Bishan', 14: 'Pasir Ris'}
h['town'] = [FIX.get(i, t) for i, t in zip(h.idx, h.town_estate)]
d = h[h.shs_year == 2018].pivot_table(index='town', columns='elderly_pop', values='number')
d.columns = ['E', 'F']
YEARS = list(range(2025, 2032))
PLANNED = {  # town: (site, year it opens, supply multiplier)
    'Choa Chu Kang': ('Yew Tee', 2027, 1.16), 'Toa Payoh': ('Bidadari', 2027, 1.18),
    'Bedok': ('Kaki Bukit', 2027, 1.12), 'Jurong West': ('Taman Jurong', 2030, 1.14),
    'Bishan': ('Bishan', 2032, 1.20)}  # 'after 2030' -> outside horizon

def seniors(r, y):
    s18, s31 = r.E, 0.62 * r.E + 1.05 * r.F
    return s18 + (s31 - s18) * (y - 2018) / 13

def loads(include_planned=True, extra=None):
    """extra = (town, open_year, multiplier) for a hypothetical new clinic."""
    out = {}
    for t, r in d.iterrows():
        sup0 = r.E ** 0.85
        row = []
        for y in YEARS:
            c = sup0
            if include_planned and t in PLANNED and y >= PLANNED[t][1]: c *= PLANNED[t][2]
            if extra and t == extra[0] and y >= extra[1]: c *= extra[2]
            row.append(seniors(r, y) / c)
        out[t] = row
    L = pd.DataFrame(out, index=YEARS).T
    return L

base = loads(True)
SCALE = 330 / base[2026].mean()
L_on = base * SCALE
L_off = loads(False) * SCALE
LINE = float(np.percentile(L_on[2026], 75))

def first_year(row):
    if row[2026] >= LINE: return 'Now'
    for y in YEARS[2:]:
        if row[y] >= LINE: return y
    return 'Later'
L_on['year'] = L_on.apply(first_year, axis=1)
L_off['year'] = L_off.apply(first_year, axis=1)

def site_value(t, open_year=2028, mult=1.15):
    """Senior-years kept under the line, 2028-2031, by one new clinic in town t."""
    with_ = loads(True, (t, open_year, mult)) * SCALE
    gain, years_under = 0, 0
    for y in YEARS:
        if y < open_year: continue
        if L_on.loc[t, y] >= LINE and with_.loc[t, y] < LINE:
            gain += seniors(d.loc[t], y); years_under += 1
    return gain, years_under

sites = pd.DataFrame([(t, *site_value(t)) for t in d.index], columns=['town', 'senior_years', 'years']).set_index('town')
sites = sites[sites.senior_years > 0].sort_values('senior_years', ascending=False)

def verdict(t):
    site, yr, _ = PLANNED[t]
    on, off = L_on.loc[t], L_off.loc[t]
    if yr > 2031:
        return site, 'After 2030', ('Delay is low-risk' if off['year'] == 'Later' else 'Delay hurts')
    under_with = [y for y in YEARS if y >= yr and on[y] < LINE and off[y] >= LINE]
    if off['year'] == 'Later': return site, str(yr), 'Ahead of need'
    if off['year'] == 'Now' and yr >= 2029: return site, str(yr), f'{yr - 2026} years late'
    if under_with and all(on[y] < LINE for y in YEARS if y >= yr): return site, str(yr), 'On target'
    if under_with: return site, str(yr), f'Buys {len(under_with)} year' + ('s' if len(under_with) > 1 else '')
    return site, str(yr), 'Too small alone'
checks = [(t, *verdict(t)) for t in PLANNED]

if __name__ == '__main__':
    print('scale', round(SCALE, 2), 'line', round(LINE), 'mean2026', round(L_on[2026].mean()))
    print(L_on.sort_values(2031, ascending=False).round(0).to_string())
    print(sites.head(6))
    for c in checks: print(c)
    print('under-served by 2031:', sum(L_on.year != 'Later'), 'now:', sum(L_on.year == 'Now'))
