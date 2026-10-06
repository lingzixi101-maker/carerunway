-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 00 Quick start: seniors per clinic, 2009 to 2022
-- MAGIC Needs two files in `/Volumes/workspace/carerunway/raw/` (names unchanged from the DAISI pack).
-- MAGIC Expected check: 2015 = 259, 2022 = 293.

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS workspace.carerunway;
CREATE VOLUME IF NOT EXISTS workspace.carerunway.raw;

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.carerunway.seniors_by_year
COMMENT 'Population aged 65+ by year (total row), from the DAISI pack'
AS
SELECT CAST(yr AS INT) AS year, MAX(CAST(v AS BIGINT)) AS seniors
FROM (
  SELECT * FROM read_files('/Volumes/workspace/carerunway/raw/TotalPopulationByBroadAgeGroupAndSexAtEndJuneAnnual.csv',
                           format => 'csv', header => true)
  WHERE trim(DataSeries) = '65 Years & Over'
)
UNPIVOT (v FOR yr IN (`2009`,`2010`,`2011`,`2012`,`2013`,`2014`,`2015`,`2016`,`2017`,`2018`,`2019`,`2020`,`2021`,`2022`))
GROUP BY yr;  -- MAX keeps the total row; the other two rows are male and female

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.carerunway.clinics_by_year
COMMENT 'Polyclinics plus GP clinics by year (national), from the DAISI pack'
AS
SELECT CAST(year AS INT) AS year, SUM(CAST(no_of_facilities AS INT)) AS clinics
FROM read_files('/Volumes/workspace/carerunway/raw/Health Facilities (Primary Care, Dental Clinics and Pharmacies).csv',
                format => 'csv', header => true)
WHERE facility_type_b IN ('Polyclinics', 'General Practioner Clinics')  -- spelling as in the source
GROUP BY year;

-- COMMAND ----------

SELECT s.year, s.seniors, c.clinics, ROUND(s.seniors / c.clinics) AS seniors_per_clinic
FROM workspace.carerunway.seniors_by_year s
JOIN workspace.carerunway.clinics_by_year c USING (year)
ORDER BY year;
