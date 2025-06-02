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
    APRA_ORIGINAL_TITLE,
    APRA_ISWC,
    MUZOOKA_TRACK_ID,
    MUZOOKA_CLEANED_TITLE,
    MUZOOKA_ISWC,
    MATCH_SCORE,
    YN_ISWC_MATCH,
    CD_TYPE,
    YN_PERF_OWNERSHIP
FROM 
    EDW_APPS.MATCHING.FUZZY_TITLE_MATCHING
UNION
SELECT 
    APRA_WORK_ID,
    APRA_CLEANED_TITLE,
    APRA_ORIGINAL_TITLE,
    APRA_ISWC,
    MUZOOKA_TRACK_ID,
    MUZOOKA_CLEANED_TITLE,
    MUZOOKA_ISWC,
    MATCH_SCORE,
    YN_ISWC_MATCH,
    CD_TYPE,
    YN_PERF_OWNERSHIP
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
SELECT DISTINCT
  F.RDC_WORKS_ID,
	A.ADC_COMPOSER_ID, 
	A.APRA_WORK_ID, 
	A.IPI, 
	UPPER(A.NAME) AS COMPOSER_NAME,
	F.MUZOOKA_TRACK_ID 
FROM ADCCOMPOSERS A
INNER JOIN ADC_WORKS_COLUMNS_TITLE_MATCHES_COMBINED F
ON A.APRA_WORK_ID = F.APRA_WORK_ID);



create or replace TABLE EDW_APPS.MATCHING.MZK_TRACKS_WORKS_MATCHED_COMPOSERS AS (
SELECT DISTINCT
	C.COMPOSER_ID,
    UPPER(C.TRACK_ID) AS MUZOOKA_TRACK_ID,
    UPPER(C.COMPOSER) AS COMPOSER_NAME,
	C.IPI, 
FROM COMPOSERS C
INNER JOIN ADC_WORKS_COLUMNS_TITLE_MATCHES_COMBINED F
ON UPPER(C.TRACK_ID) = UPPER(F.MUZOOKA_TRACK_ID));




-- Step 1: Sample 1% of unique IDs
CREATE OR REPLACE TEMPORARY TABLE sampled_ids AS
SELECT DISTINCT apra_work_id
FROM adc_works_tracks_matched_composers
SAMPLE (0.0002);

CREATE OR REPLACE TABLE ADC_COMPOSERS_INTERMIEDIATE AS
SELECT t.*
FROM adc_works_tracks_matched_composers t
INNER JOIN sampled_ids s ON t.apra_work_id = s.apra_work_id;





--ARTISTS

-- create or replace table adc_works_tracks_matched_artists as (
-- select distinct 
--    b.rdc_works_id,
--    a.apra_work_id,
--    a.apra_artist_id,
--    b.muzooka_track_id,
--    UPPER(a.name) as apra_artist_name
--    from adcartists a
--    inner join adc_composer_delimiter_count_clean b
--    on a.apra_work_id = b.apra_work_id );



-- create or replace table mzk_tracks_matched_artists as (
-- select distinct 
--    a.recordings_id,
--    UPPER(a.track_id) as muzooka_track_id,
--    UPPER(a.artist_name) as muzooka_artist_name
--    from recordings a
--    inner join adc_composer_delimiter_count_clean b
--    on UPPER(a.track_id) = b.muzooka_track_id );


create or replace table adc_artists_intermediate as (
select distinct 
   b.rdc_works_id,
   a.apra_work_id,
   a.apra_artist_id,
   b.muzooka_track_id,
   UPPER(a.name) as apra_artist_name
   from adcartists a
   inner join ADC_COMPOSERS_INTERMIEDIATE b
   on a.apra_work_id = b.apra_work_id );


create or replace table mzk_tracks_matched_artists as (
select distinct 
   a.recordings_id,
   UPPER(a.track_id) as muzooka_track_id,
   UPPER(a.artist_name) as muzooka_artist_name
   from recordings a
   inner join ADC_WORKS_TRACKS_MATCHED_COMPOSERS b
   on UPPER(a.track_id) = b.muzooka_track_id );


--OMMITTED AND USED FULL 
CREATE OR REPLACE TEMPORARY TABLE artist_sampled_ids AS
SELECT DISTINCT apra_work_id
FROM ADC_ARTISTS_INTERMEDIATE
SAMPLE (0.0002);

CREATE OR REPLACE TABLE ADC_ARTISTS_INTERMIEDIATE_WITH_SAMPLE AS
SELECT t.*
FROM ADC_ARTISTS_INTERMEDIATE t
INNER JOIN artist_sampled_ids s ON t.apra_work_id = s.apra_work_id;

select * from ADC_ARTISTS_INTERMIEDIATE_WITH_SAMPLE



---FINAL TABLE

CREATE or replace TABLE ADC_WORKS_ARTISTS_COMPOSERS_MATCHED AS (
SELECT DISTINCT
    t1.RDC_WORKS_ID,
    t1.APRA_WORK_ID,
    t1.APRA_ORIGINAL_TITLE as APRA_TITLE,
    t1.APRA_ISWC,
    t1.MUZOOKA_TRACK_ID,
    UPPER(t1.MUZOOKA_ORIGINAL_TITLE) as MUZOOKA_TITLE,
    --t1.MUZOOKA_CLEANED_TITLE as MUZOOKA_TITLE,
    t1.MUZOOKA_ISWC,
    (t1.MATCH_SCORE)/100 AS TITLE_MATCH_SCORE,
    t1.YN_ISWC_MATCH,
    t3.adc_total_composers AS APRA_COMPOSER_CT,
    t3.mzk_total_composers AS MUZOOKA_COMPOSER_CT,
    (t3.composer_mtch_pcntg)*100 as WRITER_MATCH_PERCENTAGE,
    t4.artist_match_total AS ARTIST_MATCH_SCORE,
    t1.CD_TYPE,
    CASE 
        WHEN t1.YN_PERF_OWNERSHIP = 'N' 
             AND (LENGTH(t2.COMPOSER_NAMES) = 40 
                  OR (LENGTH(t2.COMPOSER_NAMES) = 39 AND RIGHT(t2.COMPOSER_NAMES, 1) = ' ')) 
                      AND (t3.adc_total_composers < t3.mzk_total_composers)
        THEN 'Y'
        ELSE 'N'
    END AS YN_COMPOSERS_TRUNCATED
FROM ADC_WORKS_COLUMNS_TITLE_MATCHES_COMBINED_1 t1
INNER JOIN ADCWORKS t2 
            ON t1.APRA_WORK_ID = t2.APRA_WORK_ID 
INNER JOIN COMPOSER_PART_BY_PART_MATCH_FULL t3 
            ON t1.APRA_WORK_ID = t3.APRA_WORK_ID 
            AND T1.MUZOOKA_TRACK_ID = T3.MUZOOKA_TRACK_ID
LEFT JOIN ARTIST_PART_BY_PART_MATCH_FULL t4
            ON t1.APRA_WORK_ID = t4.APRA_WORK_ID 
            AND T1.MUZOOKA_TRACK_ID = T4.MUZOOKA_TRACK_ID
--WHERE T1.APRA_WORK_ID = 'GW33624310'
);




--- ISRC MATCHING 
CREATE OR REPLACE TABLE ISRC_WITH_WORKS_TRACKS AS (
WITH DISTINCT_TITLE_MATCHES AS (
    SELECT DISTINCT 
           APRA_WORK_ID,
           MUZOOKA_TRACK_ID,
           RDC_WORKS_ID
    FROM ADC_WORKS_COLUMNS_TITLE_MATCHES_COMBINED_1
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY i.ADC_ISRC_ID) AS RDC_ISRC_ID,
    c.RDC_WORKS_ID,
    i.APRA_WORK_ID,
    c.MUZOOKA_TRACK_ID,
    i.ISRC,
    CASE WHEN r.isrc = i.ISRC THEN 'Y' ELSE 'N' END AS YN_ISRC_MATCH,
FROM 
    DISTINCT_TITLE_MATCHES c
    INNER JOIN ADCISRC i
        ON i.APRA_WORK_ID = c.APRA_WORK_ID
    INNER JOIN recordings r
        ON c.MUZOOKA_TRACK_ID = UPPER(r.track_id)
--WHERE I.APRA_WORK_ID = 'GW33624310'
);