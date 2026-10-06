# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Silver: HDB elderly by town, with corrected town labels
# MAGIC The source scrambles town labels in rows 8 to 15 of each year (see README, section 7).
# MAGIC Uses pandas so the original row order is kept; the fix is keyed on row position within each year and group.

# COMMAND ----------

import pandas as pd
CATALOG, SCHEMA = "workspace", "carerunway"
SRC = f"/Volumes/{CATALOG}/{SCHEMA}/raw/HDBElderlyandFutureElderlyResidentPopulationbyGeographicalDistribution.csv"

FIX = {8: "Woodlands", 9: "Choa Chu Kang", 10: "Bukit Batok", 11: "Bukit Panjang",
       12: "Jurong East", 13: "Serangoon", 14: "Bishan", 15: "Pasir Ris"}  # 1-based row in each year/group

h = pd.read_csv(SRC)
h["row_in_year"] = h.groupby(["shs_year", "elderly_pop"]).cumcount() + 1
h["town"] = [FIX.get(r, t) for r, t in zip(h.row_in_year, h.town_estate)]
h["label_corrected"] = h.town != h.town_estate
assert h.groupby(["shs_year", "elderly_pop"]).town.nunique().eq(26).all(), "expected 26 unique towns per year"

(spark.createDataFrame(h).write.mode("overwrite").option("overwriteSchema", True)
   .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_hdb_elderly"))
display(spark.table(f"{CATALOG}.{SCHEMA}.silver_hdb_elderly").filter("label_corrected"))
