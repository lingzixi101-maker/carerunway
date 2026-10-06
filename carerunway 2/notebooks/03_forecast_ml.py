# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Area forecast: machine learning vs the standard method
# MAGIC
# MAGIC **Question:** how many residents will each planning area have in each 5-year age band, 5 years ahead?
# MAGIC
# MAGIC - **Standard method (baseline):** Hamilton-Perry cohort-change ratios. Each age band ages into the next band
# MAGIC   at the rate it did over the previous 5 years.
# MAGIC - **ML method:** gradient boosting predicts that 5-year change ratio from the area's age mix, recent growth and region.
# MAGIC - **Backtest:** train on windows ending by 2015 and predict 2020; train on windows ending by 2020 and predict 2025.
# MAGIC - **Rule:** we use ML only where it beats the baseline on the backtest. Both errors are logged to MLflow.
# MAGIC
# MAGIC **Input table** `workspace.carerunway.silver_pa_age` with columns:
# MAGIC `year` (int), `planning_area` (str), `region` (str), `age_band` (int, lower bound: 0, 5, ..., 90 where 90 = 90+), `pop` (int).
# MAGIC Build it from SingStat's "Singapore Residents by Planning Area, Age Group, Sex and Type of Dwelling" (sum over sex and dwelling).

# COMMAND ----------

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

CATALOG, SCHEMA = "workspace", "carerunway"
STEP = 5
TOP = 90  # open-ended top band

def load():
    return spark.table(f"{CATALOG}.{SCHEMA}.silver_pa_age").toPandas()

# COMMAND ----------

# MAGIC %md ## Build the training rows: one row per area, age band and 5-year window

# COMMAND ----------

def make_rows(df):
    """For each area/band/start year t: cohort at t (band a) -> band a+5 at t+5. Target = log change ratio."""
    p = df.pivot_table(index=["planning_area", "region", "year"], columns="age_band", values="pop", aggfunc="sum").fillna(0)
    years = sorted(df.year.unique())
    rows = []
    for (area, region), g in p.groupby(level=[0, 1]):
        g = g.droplevel([0, 1])
        for t in years:
            if t + STEP not in g.index or t - STEP not in g.index:
                continue
            now, nxt, prev = g.loc[t], g.loc[t + STEP], g.loc[t - STEP]
            total, total_prev = now.sum(), prev.sum()
            share65 = now[[c for c in now.index if c >= 65]].sum() / max(total, 1)
            for a in [c for c in now.index if c < TOP]:
                b = a + STEP
                start = now[a] + (now[TOP] if b == TOP else 0)
                # observed ratio over the previous window (what Hamilton-Perry carries forward)
                prev_start = prev.get(a, 0) + (prev[TOP] if b == TOP else 0)
                prev_ratio = (now[b] / prev_start) if prev_start > 0 else np.nan
                if start <= 0 or np.isnan(prev_ratio) or prev_ratio <= 0:
                    continue
                rows.append({"planning_area": area, "region": region, "t": t, "age_band": a,
                             "start_pop": start, "end_pop": nxt[b],
                             "prev_log_ratio": np.log(prev_ratio),
                             "area_growth": np.log(max(total, 1) / max(total_prev, 1)),
                             "share65": share65, "band_share": now[a] / max(total, 1),
                             "log_total": np.log(max(total, 1))})
    r = pd.DataFrame(rows)
    r["target"] = np.log(np.maximum(r.end_pop, 0.5) / r.start_pop)
    r["region_code"] = r.region.astype("category").cat.codes
    return r

FEATURES = ["age_band", "prev_log_ratio", "area_growth", "share65", "band_share", "log_total", "region_code"]

# COMMAND ----------

# MAGIC %md ## Backtest: baseline vs ML, plus a forecast range (10th to 90th percentile)

# COMMAND ----------

def seniors_error(test, pred_log):
    """Error on what the product uses: residents aged 65+ per area at the end of the window (MAPE)."""
    d = test.assign(pred=test.start_pop * np.exp(pred_log))
    d = d[d.age_band + STEP >= 65].groupby("planning_area")[["end_pop", "pred"]].sum()
    d = d[d.end_pop > 0]
    return float((abs(d.pred - d.end_pop) / d.end_pop).mean() * 100)

def backtest(rows, test_starts=(2015, 2020)):
    """Each fold trains only on windows that finished by the test start year, then predicts t -> t+5."""
    out = []
    for test_t in test_starts:
        train = rows[rows.t + STEP <= test_t]
        test = rows[rows.t == test_t]
        if len(train) < 50 or test.empty:
            continue
        base = test.prev_log_ratio.values  # Hamilton-Perry: carry the previous ratio forward
        model = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=0)
        model.fit(train[FEATURES], train.target)
        ml = model.predict(test[FEATURES])
        out.append({"test_window": f"{test_t}-{test_t + STEP}", "baseline_mape": seniors_error(test, base),
                    "ml_mape": seniors_error(test, ml), "n_train": len(train), "n_test": len(test)})
    return pd.DataFrame(out)

def fit_final(rows):
    point = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=0)
    lo = HistGradientBoostingRegressor(loss="quantile", quantile=0.1, max_depth=3, max_iter=300, random_state=0)
    hi = HistGradientBoostingRegressor(loss="quantile", quantile=0.9, max_depth=3, max_iter=300, random_state=0)
    for m in (point, lo, hi):
        m.fit(rows[FEATURES], rows.target)
    return point, lo, hi

# COMMAND ----------

# MAGIC %md ## Run, log to MLflow, register only if ML wins

# COMMAND ----------

def run(df, register=True):
    import mlflow
    from mlflow.models import infer_signature
    rows = make_rows(df)
    bt = backtest(rows)
    display(bt)
    ml_wins = bool(len(bt) and (bt.ml_mape < bt.baseline_mape).all())
    mlflow.set_registry_uri("databricks-uc")
    with mlflow.start_run(run_name="area_forecast"):
        mlflow.log_params({"features": ",".join(FEATURES), "step_years": STEP, "model": "HistGradientBoosting"})
        for _, r in bt.iterrows():
            mlflow.log_metric(f"baseline_mape_{r.test_window}", r.baseline_mape)
            mlflow.log_metric(f"ml_mape_{r.test_window}", r.ml_mape)
        mlflow.log_metric("ml_wins_all_folds", int(ml_wins))
        point, lo, hi = fit_final(rows)
        sig = infer_signature(rows[FEATURES], point.predict(rows[FEATURES]))
        info = mlflow.sklearn.log_model(point, "model", signature=sig, input_example=rows[FEATURES].head(3))
        mlflow.sklearn.log_model(lo, "model_p10", signature=sig)
        mlflow.sklearn.log_model(hi, "model_p90", signature=sig)
        if register and ml_wins:
            mlflow.register_model(info.model_uri, f"{CATALOG}.{SCHEMA}.area_forecast")
    print("ML beats the standard method on every fold" if ml_wins else "ML does not win on every fold: keep the standard method")
    return bt

# COMMAND ----------

# Uncomment once silver_pa_age exists:
# bt = run(load())
