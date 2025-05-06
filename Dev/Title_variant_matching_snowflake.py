import snowflake.snowpark as snowpark
from snowflake.snowpark.functions import col, lit, udf, call_udf, expr
import pandas as pd
import numpy as np

# Define view/table names
ADC_WORKS_VIEW = "ADC_WORKS_TITLE_VARIANT_VW"
MAZOOKA_TRACKS_VIEW = "MZK_TRACKS_TITLE_VARIANT_VW"

# Use the base table instead of the problematic view for recordings
MAZOOKA_RECORDINGS_TABLE = "EDW_APPS.MATCHING.MAZOOKA_RECORDINGS_TITLE_VARIANTS"

# Define output table for results
RESULTS_TABLE = "EDW_APPS.MATCHING.TITLE_VARIANT_MATCHING_RESULTS_2"


def create_title_similarity_udf():
    """Create JavaScript UDF for title similarity calculation"""
    try:
        print("Creating title similarity function...")

        # Create the JavaScript UDF
        title_similarity_js = """
        CREATE OR REPLACE FUNCTION TITLE_SIMILARITY(str1 STRING, str2 STRING)
        RETURNS FLOAT
        LANGUAGE JAVASCRIPT
        AS
        $$
          // Normalize inputs - lowercase, remove extra spaces, special chars, etc.
          function normalizeString(str) {
            if (!str) return '';
            return str.toLowerCase()
                      .replace(/[^\w\s]/g, ' ')  // Replace special chars with space
                      .replace(/\s+/g, ' ')      // Replace multiple spaces with single space
                      .trim();
          }

          // Jaro-Winkler similarity implementation
          function jaroWinkler(s1, s2) {
            s1 = normalizeString(s1);
            s2 = normalizeString(s2);

            if (s1 === s2) return 1.0;
            if (s1.length === 0 || s2.length === 0) return 0.0;

            // Maximum distance to look for matching characters
            const matchDistance = Math.floor(Math.max(s1.length, s2.length) / 2) - 1;

            // Arrays to track matched characters
            const s1Matches = new Array(s1.length).fill(false);
            const s2Matches = new Array(s2.length).fill(false);

            // Count matching characters
            let matchingChars = 0;
            for (let i = 0; i < s1.length; i++) {
              // Look for matches within the match distance
              const start = Math.max(0, i - matchDistance);
              const end = Math.min(i + matchDistance + 1, s2.length);

              for (let j = start; j < end; j++) {
                if (!s2Matches[j] && s1[i] === s2[j]) {
                  s1Matches[i] = true;
                  s2Matches[j] = true;
                  matchingChars++;
                  break;
                }
              }
            }

            // Return 0 if no matching characters
            if (matchingChars === 0) return 0.0;

            // Count transpositions
            let transpositions = 0;
            let j = 0;

            for (let i = 0; i < s1.length; i++) {
              if (s1Matches[i]) {
                // Find the next matched character in s2
                while (j < s2Matches.length && !s2Matches[j]) j++;

                if (j < s2Matches.length && s1[i] !== s2[j]) transpositions++;
                j++;
              }
            }

            // Calculate Jaro similarity
            const m = matchingChars;
            transpositions = Math.floor(transpositions / 2);

            const jaroSimilarity = (
              (m / s1.length) +
              (m / s2.length) +
              ((m - transpositions) / m)
            ) / 3.0;

            // Apply Winkler prefix adjustment
            const prefixLength = Math.min(4, (() => {
              let i = 0;
              while (i < Math.min(s1.length, s2.length) && s1[i] === s2[i]) i++;
              return i;
            })());

            // Winkler scaling factor - standard value is 0.1
            const scalingFactor = 0.1;

            return jaroSimilarity + (prefixLength * scalingFactor * (1 - jaroSimilarity));
          }

          // Additional title matching logic
          function titleSimilarity(title1, title2) {
            if (!title1 || !title2) return 0.0;

            const jw = jaroWinkler(title1, title2);

            // Check for word token matching
            const tokens1 = normalizeString(title1).split(' ').filter(t => t.length > 0);
            const tokens2 = normalizeString(title2).split(' ').filter(t => t.length > 0);

            // Calculate token overlap
            let matchedTokens = 0;
            for (const t1 of tokens1) {
              if (tokens2.includes(t1)) matchedTokens++;
            }

            const tokenRatio = tokens1.length > 0 && tokens2.length > 0 ?
              matchedTokens / Math.max(tokens1.length, tokens2.length) : 0;

            // Weighted combination of Jaro-Winkler and token matching
            return Math.max(jw, 0.8 * tokenRatio);
          }

          return titleSimilarity(STR1, STR2);
        $$;
        """

        # Execute the SQL statement
        session.sql(title_similarity_js).collect()
        print("Title similarity UDF created successfully.")
        return True
    except Exception as e:
        print(f"Error creating title similarity UDF: {e}")
        return False


def check_table_exists(table_name):
    """Check if a table exists"""
    try:
        result = session.sql(f"SELECT 1 FROM {table_name} LIMIT 1").collect()
        print(f"Table {table_name} exists and is accessible.")
        return True
    except Exception as e:
        print(f"Table {table_name} does not exist or is not accessible: {e}")
        return False


def prepare_title_variant_views():
    """Create optimized enhanced views of all title variants from the existing views/tables"""
    try:
        # Create enhanced ADC Works view with normalized titles and title variants
        adc_view_sql = f"""
        CREATE OR REPLACE TEMPORARY VIEW ADC_VARIANTS AS
        SELECT
            *,
            UPPER(TITLE) AS UPPER_TITLE,
            UPPER(TITLE_VARIANT) AS UPPER_TITLE_VARIANT,
            UPPER(ORIGINAL_TITLE) AS UPPER_ORIGINAL_TITLE,
            LOWER(TITLE) AS NORM_TITLE,
            REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9\\s]', ' ') AS CLEAN_TITLE,
            REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9]', '') AS COMPACT_TITLE,
            REGEXP_REPLACE(REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9\\s]', ' '), '^(the|a|an)\\s+', '') AS NO_ARTICLE_TITLE
        FROM {ADC_WORKS_VIEW}
        WHERE ISWC IS NOT NULL AND ISWC != ''
        """

        # Create enhanced Mazooka Tracks view with normalized titles and title variants
        tracks_view_sql = f"""
        CREATE OR REPLACE TEMPORARY VIEW TRACKS_VARIANTS AS
        SELECT
            *,
            UPPER(TITLE) AS UPPER_TITLE,
            UPPER(TITLE_VARIANT) AS UPPER_TITLE_VARIANT,
            UPPER(ORIGINAL_TITLE) AS UPPER_ORIGINAL_TITLE,
            LOWER(TITLE) AS NORM_TITLE,
            REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9\\s]', ' ') AS CLEAN_TITLE,
            REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9]', '') AS COMPACT_TITLE,
            REGEXP_REPLACE(REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9\\s]', ' '), '^(the|a|an)\\s+', '') AS NO_ARTICLE_TITLE
        FROM {MAZOOKA_TRACKS_VIEW}
        WHERE ISWC IS NOT NULL AND ISWC != ''
        """

        # Create recordings view directly from the base table with controlled column selection
        recordings_view_sql = f"""
        CREATE OR REPLACE TEMPORARY VIEW RECORDINGS_VARIANTS AS
        SELECT
            RECORDINGS_ID,
            TRACK_ID,
            ISRC,
            ARTIST_NAME,
            TITLE,
            ALBUM_NAME,
            STATUS,
            HAS_BRACKETS,
            HAS_HYPHENS,
            ISWC,
            ORIGINAL_TITLE,
            TITLE_VARIANT,
            IS_VARIANT,
            -- Add uppercase versions of titles
            UPPER(TITLE) AS UPPER_TITLE,
            UPPER(TITLE_VARIANT) AS UPPER_TITLE_VARIANT,
            UPPER(ORIGINAL_TITLE) AS UPPER_ORIGINAL_TITLE,
            -- Add normalized versions of title
            LOWER(TITLE) AS NORM_TITLE,
            REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9\\s]', ' ') AS CLEAN_TITLE,
            REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9]', '') AS COMPACT_TITLE,
            REGEXP_REPLACE(REGEXP_REPLACE(LOWER(TITLE), '[^a-z0-9\\s]', ' '), '^(the|a|an)\\s+', '') AS NO_ARTICLE_TITLE
        FROM {MAZOOKA_RECORDINGS_TABLE}
        WHERE ISWC IS NOT NULL AND ISWC != ''
        """

        # Execute the SQL statements
        session.sql(adc_view_sql).collect()
        session.sql(tracks_view_sql).collect()
        session.sql(recordings_view_sql).collect()

        print("Created enhanced views with normalized and capitalized titles")
        return True
    except Exception as e:
        print(f"Error creating enhanced views: {e}")
        return False


def find_iswc_matches():
    """Find all works, tracks, and recordings that share the same ISWC"""
    try:
        match_sql = f"""
        CREATE OR REPLACE TEMPORARY TABLE ISWC_MATCHES AS
        WITH track_recordings AS (
            -- Get all tracks with their recordings
            SELECT 
                t.TRACK_ID,
                t.UPPER_TITLE AS TRACK_UPPER_TITLE,
                t.UPPER_TITLE_VARIANT AS TRACK_TITLE_VARIANT,
                t.UPPER_ORIGINAL_TITLE AS TRACK_ORIGINAL_TITLE,
                t.TITLE AS TRACK_TITLE, 
                t.ISWC AS TRACK_ISWC,
                t.IS_VARIANT AS TRACK_IS_VARIANT,
                t.NORM_TITLE AS TRACK_NORM_TITLE,
                t.CLEAN_TITLE AS TRACK_CLEAN_TITLE,
                t.COMPACT_TITLE AS TRACK_COMPACT_TITLE,
                t.NO_ARTICLE_TITLE AS TRACK_NO_ARTICLE_TITLE,
                r.RECORDINGS_ID,
                r.ISRC,
                r.UPPER_TITLE AS RECORDING_UPPER_TITLE,
                r.UPPER_TITLE_VARIANT AS RECORDING_TITLE_VARIANT,
                r.UPPER_ORIGINAL_TITLE AS RECORDING_ORIGINAL_TITLE,
                r.TITLE AS RECORDING_TITLE,
                r.IS_VARIANT AS RECORDING_IS_VARIANT,
                r.NORM_TITLE AS RECORDING_NORM_TITLE,
                r.CLEAN_TITLE AS RECORDING_CLEAN_TITLE,
                r.COMPACT_TITLE AS RECORDING_COMPACT_TITLE,
                r.NO_ARTICLE_TITLE AS RECORDING_NO_ARTICLE_TITLE,
                -- Flag recordings that have different titles than their tracks
                CASE WHEN r.TITLE IS NOT NULL AND r.TITLE != t.TITLE THEN TRUE ELSE FALSE END AS RECORDING_TITLE_DIFFERS
            FROM 
                TRACKS_VARIANTS t
            LEFT JOIN 
                RECORDINGS_VARIANTS r ON t.TRACK_ID = r.TRACK_ID
        )

        -- Join ADC works with tracks/recordings on ISWC
        SELECT 
            a.APRA_WORK_ID,
            a.UPPER_TITLE AS ADC_UPPER_TITLE,
            a.UPPER_TITLE_VARIANT AS ADC_TITLE_VARIANT,
            a.UPPER_ORIGINAL_TITLE AS ADC_ORIGINAL_TITLE,
            a.TITLE AS ADC_TITLE,
            a.ISWC AS ADC_ISWC,
            a.IS_VARIANT AS ADC_IS_VARIANT,
            a.NORM_TITLE AS ADC_NORM_TITLE,
            a.CLEAN_TITLE AS ADC_CLEAN_TITLE,
            a.COMPACT_TITLE AS ADC_COMPACT_TITLE,
            a.NO_ARTICLE_TITLE AS ADC_NO_ARTICLE_TITLE,
            tr.TRACK_ID,
            tr.TRACK_UPPER_TITLE,
            tr.TRACK_TITLE_VARIANT,
            tr.TRACK_ORIGINAL_TITLE,
            tr.TRACK_TITLE,
            tr.TRACK_ISWC,
            tr.TRACK_IS_VARIANT,
            tr.TRACK_NORM_TITLE,
            tr.TRACK_CLEAN_TITLE,
            tr.TRACK_COMPACT_TITLE,
            tr.TRACK_NO_ARTICLE_TITLE,
            tr.RECORDINGS_ID,
            tr.ISRC,
            tr.RECORDING_UPPER_TITLE,
            tr.RECORDING_TITLE_VARIANT,
            tr.RECORDING_ORIGINAL_TITLE,
            tr.RECORDING_TITLE,
            tr.RECORDING_IS_VARIANT,
            tr.RECORDING_NORM_TITLE,
            tr.RECORDING_CLEAN_TITLE,
            tr.RECORDING_COMPACT_TITLE,
            tr.RECORDING_NO_ARTICLE_TITLE,
            tr.RECORDING_TITLE_DIFFERS
        FROM 
            ADC_VARIANTS a
        JOIN 
            track_recordings tr ON a.ISWC = tr.TRACK_ISWC
        """

        session.sql(match_sql).collect()

        # Get count of matches for reporting
        count_sql = "SELECT COUNT(*) AS MATCH_COUNT FROM ISWC_MATCHES"
        match_count = session.sql(count_sql).collect()
        print(f"Found {match_count[0]['MATCH_COUNT']} ISWC matches between sources")
        return True
    except Exception as e:
        print(f"Error finding ISWC matches: {e}")
        return False


def calculate_title_match_scores():
    """Calculate match scores between title variants"""
    try:
        score_sql = f"""
        CREATE OR REPLACE TEMPORARY TABLE TITLE_MATCH_SCORES AS
        SELECT 
            *,
            -- Calculate exact match scores for tracks
            CASE 
                WHEN ADC_NORM_TITLE = TRACK_NORM_TITLE THEN 1.0
                WHEN ADC_CLEAN_TITLE = TRACK_CLEAN_TITLE THEN 0.95
                WHEN ADC_COMPACT_TITLE = TRACK_COMPACT_TITLE THEN 0.90
                WHEN ADC_NO_ARTICLE_TITLE = TRACK_NO_ARTICLE_TITLE THEN 0.85
                ELSE 0.0
            END AS EXACT_TRACK_MATCH_SCORE,

            -- Calculate fuzzy match scores using our JavaScript UDF
            TITLE_SIMILARITY(ADC_TITLE, TRACK_TITLE) AS FUZZY_TRACK_MATCH_SCORE,

            -- Calculate exact match scores for recordings (only if title differs from track)
            CASE 
                WHEN RECORDING_TITLE_DIFFERS AND ADC_NORM_TITLE = RECORDING_NORM_TITLE THEN 1.0
                WHEN RECORDING_TITLE_DIFFERS AND ADC_CLEAN_TITLE = RECORDING_CLEAN_TITLE THEN 0.95
                WHEN RECORDING_TITLE_DIFFERS AND ADC_COMPACT_TITLE = RECORDING_COMPACT_TITLE THEN 0.90
                WHEN RECORDING_TITLE_DIFFERS AND ADC_NO_ARTICLE_TITLE = RECORDING_NO_ARTICLE_TITLE THEN 0.85
                ELSE 0.0
            END AS EXACT_RECORDING_MATCH_SCORE,

            -- Calculate fuzzy match scores for recordings (only if title differs from track)
            CASE
                WHEN RECORDING_TITLE_DIFFERS THEN TITLE_SIMILARITY(ADC_TITLE, RECORDING_TITLE)
                ELSE 0.0
            END AS FUZZY_RECORDING_MATCH_SCORE
        FROM 
            ISWC_MATCHES
        """

        session.sql(score_sql).collect()
        print("Calculated title match scores")
        return True
    except Exception as e:
        print(f"Error calculating title match scores: {e}")
        return False


def generate_final_results():
    """Generate final results with best match scores"""
    try:
        final_sql = f"""
        CREATE OR REPLACE TABLE {RESULTS_TABLE} AS
        SELECT 
            APRA_WORK_ID,
            TRACK_ID,
            RECORDINGS_ID,
            ISRC,
            ADC_TITLE_VARIANT,
            ADC_ORIGINAL_TITLE,
            TRACK_TITLE_VARIANT,
            TRACK_ORIGINAL_TITLE AS MZK_ORIGINAL_TITLE,
            RECORDING_TITLE_VARIANT,
            RECORDING_ORIGINAL_TITLE AS MZK_REC_ORIGINAL_TITLE,
            ADC_ISWC,
            TRACK_ISWC,
            RECORDING_TITLE_DIFFERS,
            -- Take the maximum score between exact and fuzzy matching for tracks
            GREATEST(EXACT_TRACK_MATCH_SCORE, FUZZY_TRACK_MATCH_SCORE) AS TRACK_MATCH_SCORE,
            -- Take the maximum score between exact and fuzzy matching for recordings
            GREATEST(EXACT_RECORDING_MATCH_SCORE, FUZZY_RECORDING_MATCH_SCORE) AS RECORDING_MATCH_SCORE,
            -- Source variant flags
            ADC_IS_VARIANT,
            TRACK_IS_VARIANT,
            RECORDING_IS_VARIANT
        FROM 
            TITLE_MATCH_SCORES
        """

        session.sql(final_sql).collect()
        print(f"Generated final results in table: {RESULTS_TABLE}")
        return True
    except Exception as e:
        print(f"Error generating final results: {e}")
        return False


def generate_match_statistics():
    """Generate statistics about the matches"""
    try:
        stats_sql = f"""
        SELECT 
            COUNT(*) AS TOTAL_MATCHES,
            COUNT(DISTINCT APRA_WORK_ID) AS UNIQUE_WORKS,
            COUNT(DISTINCT TRACK_ID) AS UNIQUE_TRACKS,
            COUNT(DISTINCT RECORDINGS_ID) AS UNIQUE_RECORDINGS,

            -- Track match statistics
            SUM(CASE WHEN TRACK_MATCH_SCORE = 1.0 THEN 1 ELSE 0 END) AS PERFECT_TRACK_MATCHES,
            SUM(CASE WHEN TRACK_MATCH_SCORE >= 0.9 AND TRACK_MATCH_SCORE < 1.0 THEN 1 ELSE 0 END) AS HIGH_TRACK_MATCHES,
            SUM(CASE WHEN TRACK_MATCH_SCORE >= 0.7 AND TRACK_MATCH_SCORE < 0.9 THEN 1 ELSE 0 END) AS MEDIUM_TRACK_MATCHES,
            SUM(CASE WHEN TRACK_MATCH_SCORE < 0.7 THEN 1 ELSE 0 END) AS LOW_TRACK_MATCHES,
            AVG(TRACK_MATCH_SCORE) AS AVG_TRACK_MATCH_SCORE,

            -- Recording match statistics (only for different titles)
            SUM(CASE WHEN RECORDING_TITLE_DIFFERS = TRUE THEN 1 ELSE 0 END) AS DIFFERENT_RECORDING_TITLES,
            SUM(CASE WHEN RECORDING_MATCH_SCORE = 1.0 AND RECORDING_TITLE_DIFFERS = TRUE THEN 1 ELSE 0 END) AS PERFECT_RECORDING_MATCHES,
            SUM(CASE WHEN RECORDING_MATCH_SCORE >= 0.9 AND RECORDING_MATCH_SCORE < 1.0 AND RECORDING_TITLE_DIFFERS = TRUE THEN 1 ELSE 0 END) AS HIGH_RECORDING_MATCHES,
            AVG(CASE WHEN RECORDING_TITLE_DIFFERS = TRUE THEN RECORDING_MATCH_SCORE ELSE NULL END) AS AVG_RECORDING_MATCH_SCORE,

            -- Variant statistics
            SUM(CASE WHEN ADC_IS_VARIANT = TRUE THEN 1 ELSE 0 END) AS ADC_VARIANT_COUNT,
            SUM(CASE WHEN TRACK_IS_VARIANT = TRUE THEN 1 ELSE 0 END) AS TRACK_VARIANT_COUNT,
            SUM(CASE WHEN RECORDING_IS_VARIANT = TRUE THEN 1 ELSE 0 END) AS RECORDING_VARIANT_COUNT
        FROM 
            {RESULTS_TABLE}
        """

        stats = session.sql(stats_sql).to_pandas()
        print("\nMatch Statistics:")
        print(stats)
        return stats
    except Exception as e:
        print(f"Error generating match statistics: {e}")
        return None


def get_example_matches(limit=10):
    """Get example matches for verification"""
    try:
        examples_sql = f"""
        SELECT 
            ADC_TITLE_VARIANT,
            ADC_ORIGINAL_TITLE,
            TRACK_TITLE_VARIANT,
            MZK_ORIGINAL_TITLE,
            RECORDING_TITLE_VARIANT,
            MZK_REC_ORIGINAL_TITLE,
            TRACK_MATCH_SCORE,
            RECORDING_MATCH_SCORE,
            RECORDING_TITLE_DIFFERS,
            ADC_IS_VARIANT,
            TRACK_IS_VARIANT,
            RECORDING_IS_VARIANT
        FROM 
            {RESULTS_TABLE}
        ORDER BY 
            TRACK_MATCH_SCORE DESC, RECORDING_MATCH_SCORE DESC
        LIMIT {limit}
        """

        examples = session.sql(examples_sql).to_pandas()
        print("\nExample Matches:")
        print(examples)
        return examples
    except Exception as e:
        print(f"Error getting example matches: {e}")
        return None


def run_title_variant_matching():
    """Main function to execute title variant matching"""
    print("Starting title variant matching across ADC Works and Mazooka sources...")

    # Step 1: Create title similarity UDF
    if not create_title_similarity_udf():
        print("Failed to create title similarity UDF. Aborting process.")
        return False

    # Step 2: Check if all required views/tables exist
    adc_view_exists = check_table_exists(ADC_WORKS_VIEW)
    tracks_view_exists = check_table_exists(MAZOOKA_TRACKS_VIEW)
    recordings_table_exists = check_table_exists(MAZOOKA_RECORDINGS_TABLE)

    if not (adc_view_exists and tracks_view_exists and recordings_table_exists):
        missing = []
        if not adc_view_exists: missing.append(ADC_WORKS_VIEW)
        if not tracks_view_exists: missing.append(MAZOOKA_TRACKS_VIEW)
        if not recordings_table_exists: missing.append(MAZOOKA_RECORDINGS_TABLE)

        print(f"The following required objects are missing: {', '.join(missing)}")
        print("Please ensure all required objects exist. Aborting process.")
        return False

    # Step 3: Prepare enhanced views with normalized titles
    if not prepare_title_variant_views():
        print("Failed to prepare enhanced views. Aborting process.")
        return False

    # Step 4: Find matches based on ISWC
    if not find_iswc_matches():
        print("Failed to find ISWC matches. Aborting process.")
        return False

    # Step 5: Calculate title match scores
    if not calculate_title_match_scores():
        print("Failed to calculate title match scores. Aborting process.")
        return False

    # Step 6: Generate final results
    if not generate_final_results():
        print("Failed to generate final results. Aborting process.")
        return False

    # Generate match statistics and examples
    generate_match_statistics()
    get_example_matches(10)

    print("\nTitle variant matching process completed successfully!")
    print(f"Results saved to table: {RESULTS_TABLE}")

    return True


if __name__ == "__main__":
    try:
        success = run_title_variant_matching()
        if success:
            print("\nTitle variant matching completed successfully. Check the results table for matched titles.")
        else:
            print("\nTitle variant matching failed. See error messages above.")
    except Exception as e:
        print(f"\nUnexpected error in title variant matching: {e}")