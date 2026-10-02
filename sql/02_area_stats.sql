-- 02_area_stats.sql: the query the app runs (leaselens/data.py).
-- Built from CoCo's exploration of SNOWFLAKE_PUBLIC_DATA_FREE (Snowflake Public Data, Free listing).
-- Returns ONE row per Arizona ZCTA (850xx–865xx), latest ACS 5-year estimate:
--   ZIP, PLACE, MEDIAN_RENT, MEDIAN_INCOME, YEAR, LAT, LON
-- Variables (confirmed with CoCo):
--   B25064_001E_5YR        Median gross rent, one variable with history by DATE
--   B19013_001E_5YR_<yyyy> Median household income, one variable per inflation year
-- Geography: GEOGRAPHY_INDEX.LEVEL = 'CensusZipCodeTabulationArea', GEO_ID like 'zip/85281'.
-- LAT/LON come back NULL; the app fills them from data/zcta_centroids.csv.

WITH zcta AS (
    SELECT g.GEO_ID, g.GEO_NAME AS ZIP
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX g
    WHERE g.LEVEL = 'CensusZipCodeTabulationArea'
      AND LEFT(g.GEO_NAME, 3) BETWEEN '850' AND '865'
),
place AS (
    -- A ZCTA can overlap several cities; list them all instead of guessing one.
    SELECT r.GEO_ID,
           LISTAGG(DISTINCT r.RELATED_GEO_NAME, ' / ') WITHIN GROUP (ORDER BY r.RELATED_GEO_NAME) AS PLACE
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_RELATIONSHIPS r
    JOIN zcta z ON z.GEO_ID = r.GEO_ID
    WHERE r.RELATED_LEVEL = 'City' AND r.RELATIONSHIP_TYPE = 'Overlaps'
    GROUP BY r.GEO_ID
),
rent AS (
    SELECT t.GEO_ID, t.VALUE::FLOAT AS MEDIAN_RENT, YEAR(t.DATE) AS YR
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.AMERICAN_COMMUNITY_SURVEY_TIMESERIES t
    JOIN zcta z ON z.GEO_ID = t.GEO_ID
    WHERE t.VARIABLE = 'B25064_001E_5YR' AND t.VALUE IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t.GEO_ID ORDER BY t.DATE DESC) = 1
),
income AS (
    SELECT t.GEO_ID, t.VALUE::FLOAT AS MEDIAN_INCOME
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.AMERICAN_COMMUNITY_SURVEY_TIMESERIES t
    JOIN zcta z ON z.GEO_ID = t.GEO_ID
    WHERE t.VARIABLE LIKE 'B19013_001E_5YR_%' AND t.VALUE IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t.GEO_ID ORDER BY t.DATE DESC, t.VARIABLE DESC) = 1
)
SELECT
    z.ZIP                                                   AS ZIP,
    COALESCE(p.PLACE, 'ZIP ' || z.ZIP)                      AS PLACE,
    ROUND(r.MEDIAN_RENT)                                    AS MEDIAN_RENT,
    ROUND(i.MEDIAN_INCOME)                                  AS MEDIAN_INCOME,
    (r.YR - 4) || '–' || r.YR || ' ACS 5-year'              AS YEAR,
    NULL::FLOAT                                             AS LAT,
    NULL::FLOAT                                             AS LON
FROM zcta z
JOIN rent r        ON r.GEO_ID = z.GEO_ID
LEFT JOIN place p  ON p.GEO_ID = z.GEO_ID
LEFT JOIN income i ON i.GEO_ID = z.GEO_ID
ORDER BY z.ZIP;
