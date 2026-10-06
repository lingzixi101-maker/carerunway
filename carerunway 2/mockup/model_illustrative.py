"""Illustrative-only numbers for the draft 3 mockup (NOT findings).
Uses corrected HDB 2018 town counts + a toy supply assumption to show the product logic."""
import pandas as pd, numpy as np
h = pd.read_csv('data/HDBElderlyandFutureElderlyResidentPopulationbyGeographicalDistribution.csv')
h['idx'] = h.groupby(['shs_year', 'elderly_pop']).cumcount()
# Label correction (see README: data-quality findings). Rows 7-14 re-mapped via 2013 cross-check.
FIX = {7: 'Woodlands', 8: 'Choa Chu Kang', 9: 'Bukit Batok', 10: 'Bukit Panjang',
       11: 'Jurong East', 12: 'Serangoon', 13: 'Bishan', 14: 'Pasir Ris'}
h['town'] = [FIX.get(i, t) for i, t in zip(h.idx, h.town_estate)]
d = h[h.shs_year == 2018].pivot_table(index='town', columns='elderly_pop', values='number')
d.columns = ['E', 'F']
YEARS = list(range(2025, 2032))
PLANNED = {'Toa Payoh': (2027, 1.18), 'Bedok': (2027, 1.12), 'Choa Chu Kang': (2027, 1.16), 'Jurong West': (2030, 1.14)}
def run(include_planned=True):
    out = {}
    for t, r in d.iterrows():
        s18, s31 = r.E, 0.62 * r.E + 1.05 * r.F
        sup0 = r.E ** 0.85 / 12
        loads = []
        for y in YEARS:
            s = s18 + (s31 - s18) * (y - 2018) / 13
            c = sup0
            if include_planned and t in PLANNED and y >= PLANNED[t][0]:
                c *= PLANNED[t][1]
            loads.append(s / c)
        out[t] = loads
    L = pd.DataFrame(out, index=YEARS).T
    T = np.percentile(L[2026], 75)
    def gap(row):
        if row[2026] >= T: return 'Now'
        for y in YEARS[2:]:
            if row[y] >= T: return y
        return 'Later'
    L['gap'] = L.apply(gap, axis=1)
    return L, T
if __name__ == '__main__':
    L, T = run()
    print('threshold', round(T, 1))
    print(L.sort_values(2031, ascending=False).round(1).to_string())
    print(L.gap.value_counts())
