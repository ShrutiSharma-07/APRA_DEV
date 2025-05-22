--TITLE MATCHING
CREATE OR REPLACE TABLE adc_works_exact_match_title_variants AS (
  WITH cte1 AS (
    SELECT 
      apra_work_id,
      apra_cleaned_title,
      UPPER(REGEXP_REPLACE(APRA_ISWC, '[^A-Za-z0-9]', '')) AS apra_iswc,
    FROM ADC_WORKS_TITLE_VARIANTS_CLEAN 
    WHERE apra_cleaned_title IS NOT NULL AND apra_cleaned_title <> ''
  ),
  cte2 AS (
    SELECT 
      UPPER(muzooka_track_id) AS muzooka_track_id,
      muzooka_cleaned_title,
      muzooka_iswc
    FROM mzk_tracks_title_variants_clean
    WHERE muzooka_cleaned_title IS NOT NULL AND muzooka_cleaned_title <> ''
  )
  SELECT DISTINCT
    cte1.apra_work_id, 
    cte1.apra_cleaned_title,
    cte1.apra_iswc,
    cte2.muzooka_track_id,
    cte2.muzooka_cleaned_title,
    cte2.muzooka_iswc,
    100 AS match_score,
    CASE WHEN cte1.apra_iswc = cte2.muzooka_iswc THEN 'Y' ELSE 'N' END AS YN_ISWC_MATCH
  FROM cte1 
  JOIN cte2
  ON UPPER(cte1.apra_cleaned_title) = UPPER(cte2.muzooka_cleaned_title)
  -- where cte1.apra_work_id = 'GW00577031'
);



CREATE OR REPLACE TABLE ADC_WORKS_NON_EXACT_MATCH_TITLE_VARIANTS AS
SELECT DISTINCT
  a.apra_work_id,
  UPPER(a.apra_cleaned_title) AS apra_cleaned_title,
  UPPER(REGEXP_REPLACE(a.apra_iswc, '[^A-Za-z0-9]', '')) AS apra_iswc
FROM adc_works_title_variants_clean a
WHERE a.apra_cleaned_title <> '' -- Filter empty titles first for better performance
AND NOT EXISTS (
  SELECT 1 
  FROM mzk_tracks_title_variants_clean m
  WHERE UPPER(a.apra_cleaned_title) = UPPER(m.muzooka_cleaned_title)
);



--FINAL COMBINED RESULTS

CREATE OR REPLACE TABLE EDW_APPS.MATCHING.adc_works_title_matches_combined  AS
SELECT 
    APRA_WORK_ID,
    APRA_CLEANED_TITLE,
    APRA_ISWC,
    MUZOOKA_TRACK_ID,
    MUZOOKA_CLEANED_TITLE,
    MUZOOKA_ISWC,
    MATCH_SCORE,
    YN_ISWC_MATCH
FROM 
    EDW_APPS.MATCHING.FUZZY_TITLE_MATCHING
UNION
SELECT 
    APRA_WORK_ID,
    APRA_CLEANED_TITLE,
    APRA_ISWC,
    MUZOOKA_TRACK_ID,
    MUZOOKA_CLEANED_TITLE,
    MUZOOKA_ISWC,
    MATCH_SCORE,
    YN_ISWC_MATCH
FROM 
    EDW_APPS.MATCHING.ADC_WORKS_EXACT_MATCH_TITLE_VARIANTS
WHERE 
    -- Check if this record doesn't already exist in the fuzzy table
    NOT EXISTS (
        SELECT 1 
        FROM EDW_APPS.MATCHING.FUZZY_TITLE_MATCHING f 
        WHERE f.APRA_WORK_ID = ADC_WORKS_EXACT_MATCH_TITLE_VARIANTS.APRA_WORK_ID
        AND f.MUZOOKA_TRACK_ID = ADC_WORKS_EXACT_MATCH_TITLE_VARIANTS.MUZOOKA_TRACK_ID
    );
















-- COMPOSERS

create or replace TABLE EDW_APPS.MATCHING.ADC_WORKS_TRACKS_MATCHED_COMPOSERS AS (
SELECT
	A.ADC_COMPOSER_ID, 
	A.APRA_WORK_ID, 
	A.IPI, 
	UPPER(A.NAME) AS COMPOSER_NAME,
	F.MUZOOKA_TRACK_ID 
FROM ADCCOMPOSERS A
INNER JOIN FUZZY_TITLE_MATCHING F
ON A.APRA_WORK_ID = F.APRA_WORK_ID);



create or replace TABLE EDW_APPS.MATCHING.MZK_TRACKS_WORKS_MATCHED_COMPOSERS AS (
SELECT DISTINCT
	C.COMPOSER_ID,
    UPPER(C.TRACK_ID) AS MUZOOKA_TRACK_ID,
    UPPER(C.COMPOSER) AS COMPOSER_NAME,
	C.IPI, 
FROM COMPOSERS C
INNER JOIN adc_works_title_matches_combined F
ON UPPER(C.TRACK_ID) = UPPER(F.MUZOOKA_TRACK_ID));





CREATE OR REPLACE TABLE adc_works_exact_match_composer_names AS (
  WITH cte1 AS (
    SELECT *
    FROM adc_works_tracks_matched_composers 
  ),
  cte2 AS (
    SELECT *
    FROM mzk_tracks_works_matched_composers
  )
  SELECT DISTINCT
    cte1.adc_composer_id, 
    cte1.apra_work_id,
    cte1.muzooka_track_id,
    cte1.ipi,
    cte1.composer_name as apra_composer_name,
    cte2.composer_name as muzooka_composer_name,
    100 AS composer_match_score,
    CASE WHEN cte1.IPI = cte2.IPI THEN 'Y' ELSE 'N' END AS YN_IPI_MATCH
  FROM cte1 
  JOIN cte2
  ON UPPER(cte1.composer_name) = UPPER(cte2.composer_name)
  -- where cte1.apra_work_id = 'GW00577031'
);




CREATE OR REPLACE TABLE adc_works_non_exact_match_composer_names AS
SELECT DISTINCT
      a.adc_composer_id,
      a.apra_work_id,
      a.composer_name as apra_composer_name,
      a.ipi,
      a.muzooka_track_id
FROM adc_works_tracks_matched_composers a
WHERE a.composer_name <> '' -- Filter empty titles first for better performance
AND NOT EXISTS (
  SELECT 1 
  FROM mzk_tracks_works_matched_composers m
  WHERE UPPER(a.composer_name) = UPPER(m.composer_name)
);