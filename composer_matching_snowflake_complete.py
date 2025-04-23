# Import Snowpark and other needed packages
import snowflake.snowpark as snowpark
from snowflake.snowpark.functions import col, lit, upper, trim, length, when, split, explode, row_number
from snowflake.snowpark.window import Window
from snowflake.snowpark.functions import col, lit
from snowflake.snowpark.functions import udf
from snowflake.snowpark.types import FloatType, StringType

import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"composer_matching_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def clean_text(text_col):
    """Apply basic cleaning rules: uppercase and remove leading/trailing whitespace"""
    return upper(trim(text_col))


def split_composer_names(session, df, composer_col):
    """Split composers where multiple exist using Snowpark DataFrame operations"""
    logger.info(f"Splitting composer names in column {composer_col}")

    try:
        # First, use the explode function with the split operation for slash delimiter
        from snowflake.snowpark.functions import split, explode, trim

        # Handle the first delimiter ('/')
        df_slash_split = df.withColumn("composer_array", split(col(composer_col), lit("/")))
        df_slash_exploded = df_slash_split.withColumn("composer_temp", explode(col("composer_array")))

        # Handle the second delimiter (';')
        df_semicolon_split = df_slash_exploded.withColumn("composer_array2", split(col("composer_temp"), lit(";")))
        df_semicolon_exploded = df_semicolon_split.withColumn("composer_final", explode(col("composer_array2")))

        # Clean and filter
        df_cleaned = df_semicolon_exploded.withColumn("composer_final", trim(col("composer_final")))
        df_filtered = df_cleaned.filter(~col("composer_final").isin(["TRAD", "TRADITIONAL", "ARR"]))
        df_filtered = df_filtered.filter(col("composer_final") != "")

        # Select columns and rename back to original
        result_columns = [c for c in df.columns if c != composer_col]
        result_df = df_filtered.select([*result_columns, col("composer_final").alias(composer_col)])

        return result_df

    except Exception as e:
        logger.error(f"Error in split_composer_names: {str(e)}")
        # Try a fallback approach if the first method fails
        logger.info("Trying fallback approach for name splitting")
        return fallback_split_composer_names(session, df, composer_col)


def fallback_split_composer_names(session, df, composer_col):
    """Fallback method for splitting composer names using SQL"""
    # Create a SQL statement that doesn't rely on temporary tables
    cols = ", ".join([c for c in df.columns if c != composer_col])

    # Convert the DataFrame to SQL
    df_sql = df._to_sql()

    # Create a SQL query for splitting without creating tables
    sql = f"""
    WITH src AS ({df_sql}),
    slash_split AS (
        SELECT 
            {cols},
            TRIM(s.value) AS slash_value
        FROM 
            src t,
            TABLE(SPLIT_TO_TABLE(t.{composer_col}, '/')) s
    ),
    semicolon_split AS (
        SELECT 
            {cols},
            TRIM(s.value) AS {composer_col}
        FROM 
            slash_split t,
            TABLE(SPLIT_TO_TABLE(t.slash_value, ';')) s
    )
    SELECT 
        {cols}, 
        {composer_col}
    FROM 
        semicolon_split
    WHERE 
        {composer_col} NOT IN ('TRAD', 'TRADITIONAL', 'ARR')
        AND {composer_col} != ''
    """

    try:
        return session.sql(sql)
    except Exception as e:
        logger.error(f"Fallback method also failed: {str(e)}")
        # If both methods fail, return the original dataframe with warning
        logger.warning("Unable to split composer names, returning original dataframe")
        return df


def phase1_preprocessing(session):
    """Phase 1: Preprocessing and identifying truncated composers using Snowpark"""
    logger.info("Starting Phase 1: Preprocessing and truncation identification...")

    try:
        # Load data from Snowflake tables
        adc_composers = session.table("EDW_APPS.MATCHING.ADC_COMPOSERS_MATCHED_ISWC_NO_COMPOSER_ID_VW")
        mazooka_composers = session.table("EDW_APPS.MATCHING.MAZOOKA_COMPOSERS_MATCHED_ISWC_NO_COMPOSER_ID_VW")
        adc_works = session.table("EDW_APPS.MATCHING.ADC_WORKS_MATCHED_ISWC_VW")

        # Get row counts for initial data
        adc_count = adc_composers.count()
        mazooka_count = mazooka_composers.count()
        logger.info(f"Loaded {adc_count} ADC composer rows and {mazooka_count} Mazooka composer rows")

        # Apply Rule 1: Convert text columns to uppercase and trim
        # For ADC data
        for column in adc_composers.columns:
            if adc_composers.schema[column].datatype.type_name() in ['VARCHAR', 'STRING', 'TEXT']:
                adc_composers = adc_composers.withColumn(column, clean_text(col(column)))

        # For Mazooka data
        for column in mazooka_composers.columns:
            if mazooka_composers.schema[column].datatype.type_name() in ['VARCHAR', 'STRING', 'TEXT']:
                mazooka_composers = mazooka_composers.withColumn(column, clean_text(col(column)))

        logger.info("Text columns cleaned and standardized")

        # Create temporary views for SQL access
        adc_composers.create_or_replace_temp_view("temp_adc_composers")
        mazooka_composers.create_or_replace_temp_view("temp_mazooka_composers")

        # Use a direct SQL approach for splitting
        logger.info("Splitting ADC composer names...")
        adc_split_sql = """
        WITH source_data AS (
            SELECT * FROM temp_adc_composers
        ),
        slash_split AS (
            SELECT 
                src.*,
                TRIM(f.value) as split_value
            FROM 
                source_data src,
                LATERAL FLATTEN(input => STRTOK_TO_ARRAY(src.NAME, '/')) f
        ),
        semicolon_split AS (
            SELECT 
                {columns_explicit},
                TRIM(f.value) as NAME
            FROM 
                slash_split s,
                LATERAL FLATTEN(input => STRTOK_TO_ARRAY(s.split_value, ';')) f
        )
        SELECT 
            {columns},
            NAME
        FROM 
            semicolon_split
        WHERE 
            NAME NOT IN ('TRAD', 'TRADITIONAL', 'ARR')
            AND TRIM(NAME) != ''
        """.format(
            columns=', '.join([f'"{c}"' for c in adc_composers.columns if c != 'NAME']),
            columns_explicit=', '.join([f's."{c}"' for c in adc_composers.columns if c != 'NAME'])
        )

        expanded_adc_df = session.sql(adc_split_sql)
        logger.info(f"Expanded ADC data to approximately {expanded_adc_df.count()} rows")

        logger.info("Splitting Mazooka composer names...")
        mazooka_split_sql = """
        WITH source_data AS (
            SELECT * FROM temp_mazooka_composers
        ),
        slash_split AS (
            SELECT 
                src.*,
                TRIM(f.value) as split_value
            FROM 
                source_data src,
                LATERAL FLATTEN(input => STRTOK_TO_ARRAY(src.COMPOSER, '/')) f
        ),
        semicolon_split AS (
            SELECT 
                {columns_explicit},
                TRIM(f.value) as COMPOSER
            FROM 
                slash_split s,
                LATERAL FLATTEN(input => STRTOK_TO_ARRAY(s.split_value, ';')) f
        )
        SELECT 
            {columns},
            COMPOSER
        FROM 
            semicolon_split
        WHERE 
            COMPOSER NOT IN ('TRAD', 'TRADITIONAL', 'ARR')
            AND TRIM(COMPOSER) != ''
        """.format(
            columns=', '.join([f'"{c}"' for c in mazooka_composers.columns if c != 'COMPOSER']),
            columns_explicit=', '.join([f's."{c}"' for c in mazooka_composers.columns if c != 'COMPOSER'])
        )

        expanded_mazooka_df = session.sql(mazooka_split_sql)
        logger.info(f"Expanded Mazooka data to approximately {expanded_mazooka_df.count()} rows")

        # Create temporary views for the expanded dataframes
        expanded_adc_df.create_or_replace_temp_view("temp_expanded_adc")
        expanded_mazooka_df.create_or_replace_temp_view("temp_expanded_mazooka")

        # Count composers per work and per track using explicit SQL
        logger.info("Counting composers per work and track...")

        # For ADC data
        adc_count_sql = """
        SELECT 
            APRA_WORK_ID, 
            COUNT(*) AS ADC_COMPOSERS_COUNT
        FROM 
            temp_expanded_adc
        GROUP BY 
            APRA_WORK_ID
        """
        adc_composer_count = session.sql(adc_count_sql)

        # For Mazooka data
        mazooka_count_sql = """
        SELECT 
            TRACK_ID, 
            ISWC, 
            COUNT(*) AS MAZOOKA_COMPOSERS_COUNT
        FROM 
            temp_expanded_mazooka
        GROUP BY 
            TRACK_ID, ISWC
        """
        mazooka_composer_count = session.sql(mazooka_count_sql)

        # Create temporary view for mazooka_composer_count
        mazooka_composer_count.create_or_replace_temp_view("temp_mazooka_count")

        # Get the max MAZOOKA_COMPOSERS_COUNT for each ISWC
        mazooka_max_sql = """
        SELECT 
            ISWC, 
            MAX(MAZOOKA_COMPOSERS_COUNT) AS MAZOOKA_COMPOSERS_COUNT
        FROM 
            temp_mazooka_count
        GROUP BY 
            ISWC
        """
        mazooka_max_count = session.sql(mazooka_max_sql)

        # Merge work data with composer counts
        work_data = adc_works.join(adc_composer_count, on=["APRA_WORK_ID"], how="left")
        work_data = work_data.join(mazooka_max_count, on=["ISWC"], how="left")

        # Fill NaN values
        work_data = work_data.fillna({"ADC_COMPOSERS_COUNT": 0, "MAZOOKA_COMPOSERS_COUNT": 0})

        # Get composer_names length
        if "COMPOSERS" in work_data.columns:
            work_data = work_data.withColumn("COMPOSER_NAME_LENGTH", length(col("COMPOSERS")))
        else:
            work_data = work_data.withColumn("COMPOSER_NAME_LENGTH", lit(0))

        # Apply the truncation rule
        work_data = work_data.withColumn(
            "YN_COMPOSERS_TRUNC",
            when(
                (col("YN_PERF_OWNERSHIP") == "N") &
                (col("COMPOSER_NAME_LENGTH") >= 39) &
                (col("ADC_COMPOSERS_COUNT") < col("MAZOOKA_COMPOSERS_COUNT")),
                lit("Y")
            ).otherwise(lit("N"))
        )

        # Save intermediate tables to Snowflake
        expanded_adc_df.write.mode("overwrite").save_as_table("PHASE1_CLEANED_ADC_COMPOSERS")
        expanded_mazooka_df.write.mode("overwrite").save_as_table("PHASE1_CLEANED_MAZOOKA_COMPOSERS")
        work_data.write.mode("overwrite").save_as_table("PHASE1_WORK_DATA_WITH_FLAGS")

        logger.info("Phase 1 complete! Intermediate tables created for Phase 2.")

        return {
            "cleaned_adc_composers": expanded_adc_df,
            "cleaned_mazooka_composers": expanded_mazooka_df,
            "work_data_with_flags": work_data
        }
    except Exception as e:
        logger.error(f"Error in phase1_preprocessing: {str(e)}", exc_info=True)
        raise


def parse_name(session):
    """Create UDF to parse names into first and last name components"""
    from snowflake.snowpark.types import StringType, StructType, StructField

    def _parse_name(name):
        """Parse a name string into first and last name components"""
        if name is None or name == "":
            return {"first": "", "last": ""}

        # Special suffixes that should be kept with last name
        suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"]

        # Special prefixes for multi-word last names
        special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"]

        # Clean and split the name
        name = name.strip()
        parts = name.split()

        # Handle name with no spaces
        if len(parts) == 1:
            return {"first": "", "last": parts[0]}

        # Check if this is in "LAST FIRST" format - common in music industry
        if len(parts) == 2:
            # If second part is single letter (likely an initial)
            if len(parts[1]) == 1:
                # This is likely "LASTNAME INITIAL" format
                return {"first": parts[1], "last": parts[0]}
            # If first part is single letter (likely an initial)
            elif len(parts[0]) == 1:
                # This is likely "INITIAL LASTNAME" format
                return {"first": parts[0], "last": parts[1]}

        # Handle standard "FIRST LAST" format first
        first_name_candidate = parts[0]
        last_name_candidate = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Check for special multi-word last names (e.g., "VAN BEETHOVEN")
        for i, part in enumerate(parts):
            if part in special_prefixes and i < len(parts) - 1:
                # Found a special prefix, assume format is "FIRST PREFIX LASTNAME" or just "PREFIX LASTNAME"
                if i == 0:  # If prefix is first word, assume no first name
                    return {"first": "", "last": " ".join(parts)}
                else:  # Otherwise assume format is "FIRST PREFIX LASTNAME"
                    return {"first": " ".join(parts[:i]), "last": " ".join(parts[i:])}

        # Default: standard format "FIRST LAST"
        return {"first": first_name_candidate, "last": last_name_candidate}

    # Create a Snowpark UDF with a struct return type
    return_type = StructType([
        StructField("first", StringType()),
        StructField("last", StringType())
    ])

    return session.udf.register(
        func=_parse_name,
        name="PARSE_NAME_UDF",
        input_types=[StringType()],
        return_type=return_type,
        replace=True
    )


def calculate_name_points(session):
    """Create UDF to calculate the maximum points for a name"""
    from snowflake.snowpark.types import FloatType, StructType, StructField, StringType

    def _calculate_name_points(name_struct):
        """Calculate the maximum points for a name"""
        if name_struct is None:
            return 0.0

        points = 0.0

        # Last name points
        if name_struct["last"]:
            points += 2.0  # Maximum possible for last name

        # First name points
        if name_struct["first"]:
            if len(name_struct["first"]) == 1:  # Initial
                points += 0.5  # Maximum possible for initial
            else:
                points += 1.0  # Maximum possible for full first name

        return points

    return session.udf.register(
        func=_calculate_name_points,
        name="CALCULATE_NAME_POINTS_UDF",
        input_types=[StructType([
            StructField("first", StringType()),
            StructField("last", StringType())
        ])],
        return_type=FloatType(),
        replace=True
    )


def phase2_name_parsing(session):
    """Phase 2: Parse names into first and last name components"""
    logger.info("Starting Phase 2: Name parsing...")

    try:
        # Load tables from Phase 1
        adc_composers = session.table("PHASE1_CLEANED_ADC_COMPOSERS")
        mazooka_composers = session.table("PHASE1_CLEANED_MAZOOKA_COMPOSERS")
        work_data = session.table("PHASE1_WORK_DATA_WITH_FLAGS")

        logger.info(f"Loaded ADC composers and Mazooka composers")

        # Create UDFs for name parsing and scoring
        from snowflake.snowpark.types import StringType, StructType, StructField, FloatType

        # Register the UDFs directly using SQL queries instead
        logger.info("Creating name parsing UDFs...")

        # Create temporary views for the dataframes
        adc_composers.create_or_replace_temp_view("temp_adc_composers")
        work_data.create_or_replace_temp_view("temp_work_data")
        mazooka_composers.create_or_replace_temp_view("temp_mazooka_composers")

        # Create name parsing function in Snowflake
        session.sql("""
        CREATE OR REPLACE FUNCTION PARSE_NAME_SQL(name STRING)
        RETURNS OBJECT
        LANGUAGE JAVASCRIPT
        AS
        $$
        function parseNameJS(name) {
            if (!name || name === "") {
                return {first: "", last: ""};
            }

            // Special suffixes and prefixes
            var suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"];
            var special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"];

            // Clean and split the name
            name = name.trim();
            var parts = name.split(/\s+/);

            // Handle name with no spaces
            if (parts.length === 1) {
                return {first: "", last: parts[0]};
            }

            // Check if this is in "LAST FIRST" format - common in music industry
            if (parts.length === 2) {
                // If second part is single letter (likely an initial)
                if (parts[1].length === 1) {
                    // This is likely "LASTNAME INITIAL" format
                    return {first: parts[1], last: parts[0]};
                }
                // If first part is single letter (likely an initial)
                else if (parts[0].length === 1) {
                    // This is likely "INITIAL LASTNAME" format
                    return {first: parts[0], last: parts[1]};
                }
            }

            // Handle standard "FIRST LAST" format first
            var first_name_candidate = parts[0];
            var last_name_candidate = parts.slice(1).join(" ");

            // Check for special multi-word last names (e.g., "VAN BEETHOVEN")
            for (var i = 0; i < parts.length; i++) {
                if (special_prefixes.includes(parts[i]) && i < parts.length - 1) {
                    // Found a special prefix
                    if (i === 0) {
                        // If prefix is first word, assume no first name
                        return {first: "", last: parts.join(" ")};
                    } else {
                        // Otherwise assume format is "FIRST PREFIX LASTNAME"
                        return {
                            first: parts.slice(0, i).join(" "),
                            last: parts.slice(i).join(" ")
                        };
                    }
                }
            }

            // Default: standard format "FIRST LAST"
            return {first: first_name_candidate, last: last_name_candidate};
        }

        return parseNameJS(NAME);
        $$;
        """).collect()

        # Create name points calculation function in Snowflake
        session.sql("""
        CREATE OR REPLACE FUNCTION CALCULATE_NAME_POINTS_SQL(name_obj OBJECT)
        RETURNS FLOAT
        LANGUAGE JAVASCRIPT
        AS
        $$
        function calculateNamePoints(name_obj) {
            if (!name_obj) {
                return 0.0;
            }

            var points = 0.0;

            // Last name points
            if (name_obj.last) {
                points += 2.0;  // Maximum possible for last name
            }

            // First name points
            if (name_obj.first) {
                if (name_obj.first.length === 1) {  // Initial
                    points += 0.5;  // Maximum possible for initial
                } else {
                    points += 1.0;  // Maximum possible for full first name
                }
            }

            return points;
        }

        return calculateNamePoints(NAME_OBJ);
        $$;
        """).collect()

        logger.info("UDFs created successfully")

        # Process ADC names
        logger.info("Parsing ADC composer names...")

        adc_parsed_sql = """
        SELECT 
            a.APRA_WORK_ID,
            a.ISWC,
            a.NAME as APRA_NAME,
            PARSE_NAME_SQL(a.NAME):first::STRING as APRA_FIRST_NAME,
            PARSE_NAME_SQL(a.NAME):last::STRING as APRA_LAST_NAME,
            CALCULATE_NAME_POINTS_SQL(PARSE_NAME_SQL(a.NAME)) as APRA_NAME_SCORE,
            w.YN_COMPOSERS_TRUNC
        FROM 
            temp_adc_composers a
        LEFT JOIN 
            temp_work_data w
        ON 
            a.APRA_WORK_ID = w.APRA_WORK_ID
        """

        adc_parsed_df = session.sql(adc_parsed_sql)
        adc_count = adc_parsed_df.count()
        logger.info(f"Parsed {adc_count} ADC composer names")

        # Process Mazooka names
        logger.info("Parsing Mazooka composer names...")

        mazooka_parsed_sql = """
        SELECT 
            m.TRACK_ID,
            m.ISWC,
            m.COMPOSER as MAZOOKA_NAME,
            PARSE_NAME_SQL(m.COMPOSER):first::STRING as MAZOOKA_FIRST_NAME,
            PARSE_NAME_SQL(m.COMPOSER):last::STRING as MAZOOKA_LAST_NAME,
            CALCULATE_NAME_POINTS_SQL(PARSE_NAME_SQL(m.COMPOSER)) as MAZOOKA_NAME_SCORE
        FROM 
            temp_mazooka_composers m
        """

        mazooka_parsed_df = session.sql(mazooka_parsed_sql)
        mazooka_count = mazooka_parsed_df.count()
        logger.info(f"Parsed {mazooka_count} Mazooka composer names")

        # Save intermediate results to Snowflake tables
        adc_parsed_df.write.mode("overwrite").save_as_table("PHASE2_ADC_PARSED_NAMES")
        mazooka_parsed_df.write.mode("overwrite").save_as_table("PHASE2_MAZOOKA_PARSED_NAMES")

        logger.info("Phase 2 complete! Parsed name tables saved for Phase 3.")

        return {
            "adc_parsed_df": adc_parsed_df,
            "mazooka_parsed_df": mazooka_parsed_df
        }
    except Exception as e:
        logger.error(f"Error in phase2_name_parsing: {str(e)}", exc_info=True)
        # Print the full traceback for better debugging
        import traceback
        logger.error(traceback.format_exc())
        raise


def register_match_score_udf(session):
    """Register a UDF for calculating name match scores"""
    from snowflake.snowpark.types import FloatType, StringType

    def calculate_match_score(apra_first_name, apra_last_name, mazooka_first_name, mazooka_last_name):
        """Calculate match score between two names"""
        if not apra_last_name or not mazooka_last_name:
            return 0.0

        score = 0.0

        # Last name exact match (2 points)
        if apra_last_name == mazooka_last_name:
            score += 2.0

        # First name exact match (1 point)
        if apra_first_name and mazooka_first_name and apra_first_name == mazooka_first_name:
            score += 1.0

        # Initial match (0.5 points) - only if no exact first name match
        elif (apra_first_name and len(apra_first_name) > 0 and
              mazooka_first_name and len(mazooka_first_name) > 0 and
              apra_first_name[0] == mazooka_first_name[0]):
            score += 0.5

        # Name reversal handling - if first name matches last name AND vice versa
        if (apra_first_name and apra_last_name and
                mazooka_first_name and mazooka_last_name):

            if apra_first_name == mazooka_last_name and apra_last_name == mazooka_first_name:
                # Complete reversal - give full score of 3.0
                score = max(score, 3.0)
            elif apra_first_name == mazooka_last_name or apra_last_name == mazooka_first_name:
                # Partial reversal - give 1.5 points
                score = max(score, 1.5)

        # Fuzzy matching (simplified for UDF) - check for substrings
        if score < 2.0 and apra_last_name and mazooka_last_name:
            # Check if one is substring of the other
            if apra_last_name in mazooka_last_name or mazooka_last_name in apra_last_name:
                min_len = min(len(apra_last_name), len(mazooka_last_name))
                max_len = max(len(apra_last_name), len(mazooka_last_name))
                if min_len / max_len >= 0.7:
                    score = max(score, 1.5)

        return score

    # Register the UDF with Snowflake
    return session.udf.register(
        func=calculate_match_score,
        name="MATCH_SCORE_UDF",
        input_types=[StringType(), StringType(), StringType(), StringType()],
        return_type=FloatType(),
        replace=True
    )


def phase3_matching(session):
    """Phase 3: Generate match scores and final output using pure Python approach"""
    logger.info("Starting Phase 3: Match score generation using pure Python...")

    try:
        # Load intermediate tables from Phase 2
        adc_parsed_df = session.table("PHASE2_ADC_PARSED_NAMES")
        mazooka_parsed_df = session.table("PHASE2_MAZOOKA_PARSED_NAMES")

        logger.info("Loaded intermediate tables from Phase 2")

        # Debug: Print schema and sample data
        logger.info("ADC parsed table schema:")
        for field in adc_parsed_df.schema.fields:
            logger.info(f"Column: {field.name}, Type: {field.datatype}")

        # Get row counts
        adc_count = adc_parsed_df.count()
        mazooka_count = mazooka_parsed_df.count()
        logger.info(f"Found {adc_count} ADC records and {mazooka_count} Mazooka records")

        # Create temporary views for the dataframes
        adc_parsed_df.create_or_replace_temp_view("temp_adc_parsed")
        mazooka_parsed_df.create_or_replace_temp_view("temp_mazooka_parsed")

        # Create match score function in Snowflake
        logger.info("Creating match score function...")

        session.sql("""
        CREATE OR REPLACE FUNCTION MATCH_SCORE_SQL(apra_first STRING, apra_last STRING, 
                                                  mazooka_first STRING, mazooka_last STRING)
        RETURNS FLOAT
        LANGUAGE JAVASCRIPT
        AS
        $$
        function matchScore(apra_first, apra_last, mazooka_first, mazooka_last) {
            // Convert null to empty strings
            apra_first = apra_first || "";
            apra_last = apra_last || "";
            mazooka_first = mazooka_first || "";
            mazooka_last = mazooka_last || "";

            // Skip empty names
            if (!apra_last || !mazooka_last) {
                return 0.0;
            }

            var score = 0.0;

            // Special prefixes for last names
            var prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL"];

            // Process last names for prefixes
            var apra_prefix = "";
            var mazooka_prefix = "";

            for (var i = 0; i < prefixes.length; i++) {
                var prefix = prefixes[i];
                if (apra_last.startsWith(prefix + " ")) {
                    apra_prefix = prefix;
                    apra_last = apra_last.substring(prefix.length + 1);
                    break;
                }
            }

            for (var i = 0; i < prefixes.length; i++) {
                var prefix = prefixes[i];
                if (mazooka_last.startsWith(prefix + " ")) {
                    mazooka_prefix = prefix;
                    mazooka_last = mazooka_last.substring(prefix.length + 1);
                    break;
                }
            }

            // Common prefix bonus
            var prefix_bonus = 0;
            if (apra_prefix && mazooka_prefix && apra_prefix === mazooka_prefix) {
                prefix_bonus = 0.2;
            }

            // Last name exact match (2 points)
            if (apra_last === mazooka_last) {
                score += 2.0;
            } else {
                // Fuzzy matching for last names
                if (apra_last && mazooka_last) {
                    // Check for substring relationship
                    if (apra_last.includes(mazooka_last) || mazooka_last.includes(apra_last)) {
                        var min_len = Math.min(apra_last.length, mazooka_last.length);
                        var max_len = Math.max(apra_last.length, mazooka_last.length);
                        var substring_ratio = min_len / max_len;

                        if (substring_ratio >= 0.93) { // Changed to 0.93 per requirements
                            score += 1.5 + prefix_bonus;
                        }
                    } else {
                        // Calculate similarity based on character overlap
                        var apra_chars = new Set();
                        var mazooka_chars = new Set();

                        for (var i = 0; i < apra_last.length; i++) {
                            apra_chars.add(apra_last[i]);
                        }

                        for (var i = 0; i < mazooka_last.length; i++) {
                            mazooka_chars.add(mazooka_last[i]);
                        }

                        // Calculate common characters
                        var common_chars = new Set();
                        for (var char of apra_chars) {
                            if (mazooka_chars.has(char)) {
                                common_chars.add(char);
                            }
                        }

                        var similarity = common_chars.size / Math.max(apra_chars.size, mazooka_chars.size);

                        if (similarity >= 0.93) { // Changed to 0.93 per requirements
                            score += 1.5 + prefix_bonus;
                        }
                    }
                }
            }

            // First name exact match (1 point)
            if (apra_first && mazooka_first && apra_first === mazooka_first) {
                score += 1.0;
            } else if (apra_first && mazooka_first) {
                // Fuzzy matching for first names
                if (apra_first.includes(mazooka_first) || mazooka_first.includes(apra_first)) {
                    var min_len = Math.min(apra_first.length, mazooka_first.length);
                    var max_len = Math.max(apra_first.length, mazooka_first.length);
                    var substring_ratio = min_len / max_len;

                    if (substring_ratio >= 0.93) { // Changed to 0.93 per requirements
                        score += 0.5;
                    }
                } else {
                    // Calculate similarity based on character overlap
                    var apra_chars = new Set();
                    var mazooka_chars = new Set();

                    for (var i = 0; i < apra_first.length; i++) {
                        apra_chars.add(apra_first[i]);
                    }

                    for (var i = 0; i < mazooka_first.length; i++) {
                        mazooka_chars.add(mazooka_first[i]);
                    }

                    // Calculate common characters
                    var common_chars = new Set();
                    for (var char of apra_chars) {
                        if (mazooka_chars.has(char)) {
                            common_chars.add(char);
                        }
                    }

                    var similarity = common_chars.size / Math.max(apra_chars.size, mazooka_chars.size);

                    if (similarity >= 0.93) { // Changed to 0.93 per requirements
                        score += 0.5;
                    }
                }
            }
            // Initial match (0.5 points) - only if no exact first name match
            else if (apra_first && apra_first.length > 0 && 
                     mazooka_first && mazooka_first.length > 0 && 
                     apra_first[0] === mazooka_first[0]) {
                score += 0.5;
            }

            // Name reversal handling
            if (apra_first && apra_last && mazooka_first && mazooka_last) {
                if (apra_first === mazooka_last && apra_last === mazooka_first) {
                    // Complete reversal - give full score of 3.0
                    score = Math.max(score, 3.0);
                } else if (apra_first === mazooka_last || apra_last === mazooka_first) {
                    // Partial reversal - give 1.5 points
                    score = Math.max(score, 1.5);
                }
            }

            return score;
        }

        return matchScore(APRA_FIRST, APRA_LAST, MAZOOKA_FIRST, MAZOOKA_LAST);
        $$;
        """).collect()

        logger.info("Match score function created successfully")

        # Filter for valid ISWCs that exist in both datasets
        logger.info("Finding common ISWCs between datasets...")

        valid_iswcs_sql = """
        WITH adc_iswcs AS (
            SELECT DISTINCT ISWC 
            FROM temp_adc_parsed 
            WHERE ISWC IS NOT NULL
        ),
        mazooka_iswcs AS (
            SELECT DISTINCT ISWC 
            FROM temp_mazooka_parsed 
            WHERE ISWC IS NOT NULL
        )
        SELECT a.ISWC
        FROM adc_iswcs a
        INNER JOIN mazooka_iswcs m
        ON a.ISWC = m.ISWC
        """

        valid_iswcs = session.sql(valid_iswcs_sql)
        valid_iswcs.create_or_replace_temp_view("temp_valid_iswcs")

        count_valid_iswcs = valid_iswcs.count()
        logger.info(f"Found {count_valid_iswcs} ISWCs that exist in both datasets")

        # If no matching ISWCs, handle gracefully
        if count_valid_iswcs == 0:
            logger.warning("No matching ISWCs found between datasets. Creating empty result.")
            # Create an empty result dataframe with expected schema
            result_columns = [
                "ROW_NUM", "APRA_NAME", "APRA_NAME_SCORE", "MATCH_STATUS", "MAZOOKA_NAME",
                "MAZOOKA_NAME_SCORE", "NAME_MATCHED_SCORE", "WORK_ID", "TRACK_ID",
                "ISWC", "MATCH_PERCENT", "YN_COMPOSERS_TRUNC"
            ]
            empty_df = session.create_dataframe([], schema=result_columns)

            # Save empty results to a Snowflake table
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            final_table_name = f"COMPOSER_NAME_MATCHING_RESULTS_{timestamp}"
            empty_df.write.mode("overwrite").save_as_table(final_table_name)

            logger.info(f"Saved empty results to {final_table_name}")
            return empty_df, final_table_name

        # Calculate TAP (Total Achievable Points) for each work-track combination
        logger.info("Calculating Total Achievable Points (TAP)...")

        tap_calculation_sql = """
        WITH adc_grouped AS (
            SELECT 
                APRA_WORK_ID, 
                ISWC,
                SUM(APRA_NAME_SCORE) AS ATAP
            FROM 
                temp_adc_parsed
            WHERE
                ISWC IN (SELECT ISWC FROM temp_valid_iswcs)
            GROUP BY 
                APRA_WORK_ID, ISWC
        ),
        mazooka_grouped AS (
            SELECT 
                TRACK_ID, 
                ISWC,
                SUM(MAZOOKA_NAME_SCORE) AS STAP
            FROM 
                temp_mazooka_parsed
            WHERE
                ISWC IN (SELECT ISWC FROM temp_valid_iswcs)
            GROUP BY 
                TRACK_ID, ISWC
        )
        SELECT 
            a.APRA_WORK_ID,
            m.TRACK_ID,
            a.ISWC,
            a.ATAP,
            m.STAP,
            GREATEST(a.ATAP, m.STAP) AS TAP
        FROM 
            adc_grouped a
        JOIN 
            mazooka_grouped m
        ON 
            a.ISWC = m.ISWC
        """

        tap_data = session.sql(tap_calculation_sql)
        tap_data.create_or_replace_temp_view("temp_tap_data")

        logger.info(f"Calculated TAP for {tap_data.count()} work-track combinations")

        # Generate potential matches and calculate match scores
        logger.info("Generating potential matches and calculating scores...")

        potential_matches_sql = """
        SELECT 
            a.APRA_NAME,
            a.APRA_NAME_SCORE,
            m.MAZOOKA_NAME,
            m.MAZOOKA_NAME_SCORE,
            MATCH_SCORE_SQL(a.APRA_FIRST_NAME, a.APRA_LAST_NAME, m.MAZOOKA_FIRST_NAME, m.MAZOOKA_LAST_NAME) AS NAME_MATCHED_SCORE,
            a.APRA_WORK_ID AS WORK_ID,
            m.TRACK_ID,
            a.ISWC,
            t.TAP,
            a.YN_COMPOSERS_TRUNC
        FROM 
            temp_adc_parsed a
        JOIN 
            temp_mazooka_parsed m
        ON 
            a.ISWC = m.ISWC
        JOIN 
            temp_tap_data t
        ON 
            a.APRA_WORK_ID = t.APRA_WORK_ID 
            AND m.TRACK_ID = t.TRACK_ID
            AND a.ISWC = t.ISWC
        WHERE
            MATCH_SCORE_SQL(a.APRA_FIRST_NAME, a.APRA_LAST_NAME, m.MAZOOKA_FIRST_NAME, m.MAZOOKA_LAST_NAME) > 0
        """

        potential_matches = session.sql(potential_matches_sql)
        potential_matches.create_or_replace_temp_view("temp_potential_matches")

        logger.info(f"Generated {potential_matches.count()} potential matches with positive scores")

        # Calculate Sum of Matched Points (SMP) and Match Percentage for each work-track combination
        logger.info("Calculating SMP and Match Percentage...")

        work_match_aggregation_sql = """
        SELECT
            WORK_ID,
            TRACK_ID,
            ISWC,
            TAP,
            SUM(NAME_MATCHED_SCORE) AS SMP
        FROM
            temp_potential_matches
        GROUP BY
            WORK_ID, TRACK_ID, ISWC, TAP
        """

        work_match_aggregation = session.sql(work_match_aggregation_sql)
        work_match_aggregation.create_or_replace_temp_view("temp_work_match_aggregation")

        # Final results with match percentage
        logger.info("Generating final results...")

        final_results_sql = """
        SELECT 
            p.APRA_NAME,
            p.APRA_NAME_SCORE,
            'match' AS MATCH_STATUS,
            p.MAZOOKA_NAME,
            p.MAZOOKA_NAME_SCORE,
            p.NAME_MATCHED_SCORE,
            p.WORK_ID,
            p.TRACK_ID,
            p.ISWC,
            CASE 
                WHEN a.TAP > 0 THEN ROUND((a.SMP / a.TAP) * 100)
                ELSE 0
            END AS MATCH_PERCENT,
            p.YN_COMPOSERS_TRUNC
        FROM 
            temp_potential_matches p
        JOIN
            temp_work_match_aggregation a
        ON
            p.WORK_ID = a.WORK_ID
            AND p.TRACK_ID = a.TRACK_ID
            AND p.ISWC = a.ISWC
        """

        result_df = session.sql(final_results_sql)

        # Add row numbers
        logger.info("Adding row numbers...")

        row_number_sql = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY WORK_ID, TRACK_ID, APRA_NAME) AS ROW_NUM,
            APRA_NAME, 
            APRA_NAME_SCORE, 
            MATCH_STATUS, 
            MAZOOKA_NAME, 
            MAZOOKA_NAME_SCORE, 
            NAME_MATCHED_SCORE, 
            WORK_ID, 
            TRACK_ID, 
            ISWC, 
            MATCH_PERCENT, 
            YN_COMPOSERS_TRUNC
        FROM 
            (SELECT * FROM ({0}))
        """.format(final_results_sql)

        result_df = session.sql(row_number_sql)

        # Debug final result
        result_count = result_df.count()
        logger.info(f"Generated {result_count} matches in final result")

        if result_count > 0:
            logger.info("Sample result data:")
            sample_results = result_df.limit(5).collect()
            logger.info(str(sample_results))

        # Save final results to a Snowflake table
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        final_table_name = f"COMPOSER_NAME_MATCHING_RESULTS_{timestamp}"
        result_df.write.mode("overwrite").save_as_table(final_table_name)

        logger.info(f"Successfully wrote {result_count} results to final table: {final_table_name}")
        logger.info("Name matching process complete!")

        return result_df, final_table_name
    except Exception as e:
        logger.error(f"Error in phase3_matching: {str(e)}", exc_info=True)
        # Print the full traceback for better debugging
        import traceback
        logger.error(traceback.format_exc())
        raise


def cleanup_temp_tables(session):
    """Delete all temporary tables created during the process"""
    try:
        # List of temporary tables to drop
        temp_tables = [
            "PHASE1_CLEANED_ADC_COMPOSERS",
            "PHASE1_CLEANED_MAZOOKA_COMPOSERS",
            "PHASE1_WORK_DATA_WITH_FLAGS",
            "PHASE2_ADC_PARSED_NAMES",
            "PHASE2_MAZOOKA_PARSED_NAMES"
        ]

        # Drop each table
        for table in temp_tables:
            logger.info(f"Dropping temporary table: {table}")
            session.sql(f"DROP TABLE IF EXISTS {table}").collect()

        logger.info("All temporary tables have been dropped successfully")
    except Exception as e:
        logger.error(f"Error while cleaning up temporary tables: {str(e)}")
        logger.warning("Continuing execution despite cleanup errors")


def main(session):
    """Main function to orchestrate the three-phase name matching process"""
    logger.info("Starting name matching process with three-phase approach...")

    try:
        # Execute Phase 1: Preprocessing and truncation identification
        logger.info("=== PHASE 1: PREPROCESSING AND TRUNCATION IDENTIFICATION ===")
        phase1_results = phase1_preprocessing(session)

        # Execute Phase 2: Name parsing and score generation
        logger.info("\n=== PHASE 2: NAME PARSING AND SCORE GENERATION ===")
        phase2_results = phase2_name_parsing(session)

        # Execute Phase 3: Match score generation and final output
        logger.info("\n=== PHASE 3: MATCH SCORE GENERATION AND FINAL OUTPUT ===")
        final_results, final_table_name = phase3_matching(session)

        # Clean up temporary tables
        logger.info("\n=== CLEANING UP TEMPORARY TABLES ===")
        cleanup_temp_tables(session)

        logger.info("\nAll phases completed successfully!")
        logger.info(f"Final results saved to table: {final_table_name}")

        return final_results
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}", exc_info=True)
        raise


# In a Snowpark notebook, execute this line to run the process
final_results = main(session)