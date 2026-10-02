-- 01_explore.sql — run these in a Snowsight worksheet (or let CoCo write its own).
-- Goal: find ACS median gross rent (table B25064) and median household income (B19013)
-- at ZIP Code Tabulation Area (ZCTA) level in a FREE Marketplace listing.
-- Screenshot what you run: it's your "used CoCo + Snowflake data" evidence.

-- 1) Which shared databases do you have after "Get"-ing listings?
SHOW DATABASES;

-- 2) Find the ACS tables in the listing (replace <DB> with the database name from step 1).
SHOW TABLES IN DATABASE <DB>;
--   Look for names like AMERICAN_COMMUNITY_SURVEY_TIMESERIES / _ATTRIBUTES, GEOGRAPHY_INDEX.

-- 3) Find the rent + income variables.
--    (Column names below follow the Snowflake Public Data / Cybersyn layout. Adjust if CoCo shows different ones.)
SELECT variable, variable_name, unit, frequency
FROM <DB>.<SCHEMA>.AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES
WHERE variable_name ILIKE '%median gross rent%'
   OR variable_name ILIKE '%median household income%'
LIMIT 50;

-- 4) What geography levels exist? We want ZCTA ("CensusZipCodeTabulationArea" or similar).
SELECT DISTINCT level
FROM <DB>.<SCHEMA>.GEOGRAPHY_INDEX;

-- 5) Spot-check one ZIP and the latest estimate date.
SELECT g.geo_name, t.variable_name, t.date, t.value
FROM <DB>.<SCHEMA>.AMERICAN_COMMUNITY_SURVEY_TIMESERIES t
JOIN <DB>.<SCHEMA>.GEOGRAPHY_INDEX g ON g.geo_id = t.geo_id
WHERE g.level ILIKE '%zip%'
  AND g.geo_name ILIKE '%<YOUR ZIP>%'
  AND (t.variable_name ILIKE '%median gross rent%' OR t.variable_name ILIKE '%median household income%')
ORDER BY t.date DESC
LIMIT 20;
