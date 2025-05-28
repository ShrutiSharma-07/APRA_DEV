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
  F.RDC_WORKS_ID,
	A.ADC_COMPOSER_ID, 
	A.APRA_WORK_ID, 
	A.IPI, 
	UPPER(A.NAME) AS COMPOSER_NAME,
	F.MUZOOKA_TRACK_ID 
FROM ADCCOMPOSERS A
INNER JOIN ADC_WORKS_TITLE_MATCHES_COMBINED F
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








--ARTISTS

create or replace table adc_works_tracks_matched_artists as (
select distinct 
   b.rdc_works_id,
   a.apra_work_id,
   a.apra_artist_id,
   b.muzooka_track_id,
   UPPER(a.name) as apra_artist_name
   from adcartists a
   inner join adc_composer_delimiter_count_clean b
   on a.apra_work_id = b.apra_work_id );



create or replace table mzk_tracks_matched_artists as (
select distinct 
   a.recordings_id,
   UPPER(a.track_id) as muzooka_track_id,
   UPPER(a.artist_name) as muzooka_artist_name
   from recordings a
   inner join adc_composer_delimiter_count_clean b
   on UPPER(a.track_id) = b.muzooka_track_id );
