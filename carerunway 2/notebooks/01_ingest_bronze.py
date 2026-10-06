# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Ingest: every CSV in the raw volume becomes a bronze Delta table
# MAGIC Table name = `bronze_` + cleaned file name. Column names are cleaned so Delta accepts them
# MAGIC (year columns like `2009` become `y2009`). Re-run any time you add files.

# COMMAND ----------

import re
CATALOG, SCHEMA, VOLUME = "workspace", "carerunway", "raw"
RAW = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/"

def clean(name):
    c = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return ("y" + c) if c[:1].isdigit() else c

for f in dbutils.fs.ls(RAW):
    if not f.name.lower().endswith(".csv"):
        continue
    table = "bronze_" + clean(f.name[:-4])[:55]
    df = spark.read.option("header", True).option("inferSchema", True).csv(f.path)
    df = df.toDF(*[clean(c) for c in df.columns])
    (df.write.mode("overwrite").option("overwriteSchema", True)
       .saveAsTable(f"{CATALOG}.{SCHEMA}.{table}"))
    spark.sql(f"COMMENT ON TABLE {CATALOG}.{SCHEMA}.{table} IS 'Raw copy of {f.name}'")
    print(f"{table}: {df.count()} rows")
