from snowflake.snowpark.functions import col, lit, upper, trim, length, when, regexp_replace
import datetime
import logging
import pandas as pd


# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler(f"composer_matching_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)


def create_example_dataset(session):
    """Create a small example dataset for testing"""
    print("Creating example dataset for testing...")

    # Example ADC composers data based on the provided example
    adc_composers_data = [
        {"ADC_COMPOSER_ID": 43774657, "APRA_WORK_ID": "GW01421940", "IPI": "323735",
         "NAME": "HAY ROY ERNEST THE GREATEST AND GEMINI ROCK MAC SUN", "ISWC": "T0700428041"},
        {"ADC_COMPOSER_ID": 43774658, "APRA_WORK_ID": "GW01421941", "IPI": "523736", "NAME": "SMITH JOHN",
         "ISWC": "T0700428042"},
        {"ADC_COMPOSER_ID": 43774659, "APRA_WORK_ID": "GW01421942", "IPI": "723737", "NAME": "WILSON BRIAN",
         "ISWC": "T0700428043"},
        {"ADC_COMPOSER_ID": 43774660, "APRA_WORK_ID": "GW01421943", "IPI": "823738", "NAME": "TAYLOR D",
         "ISWC": "T0700428044"},
        {"ADC_COMPOSER_ID": 43774661, "APRA_WORK_ID": "GW01421944", "IPI": "923739", "NAME": "J WAGNER",
         "ISWC": "T0700428045"},
        {"ADC_COMPOSER_ID": 43774662, "APRA_WORK_ID": "GW01421945", "IPI": "123740", "NAME": "VAN BEETHOVEN L",
         "ISWC": "T0700428046"},
        {"ADC_COMPOSER_ID": 43774663, "APRA_WORK_ID": "GW01421946", "IPI": "223741", "NAME": "ARMSTRONG LOUIS DANIEL",
         "ISWC": "T0700428047"},
        {"ADC_COMPOSER_ID": 43774664, "APRA_WORK_ID": "GW01421947", "IPI": "323742", "NAME": "LENNON JOHN WINSTON",
         "ISWC": "T0700428048"}
    ]

    # Example Mazooka composers data
    mazooka_composers_data = [
        {"COMPOSER_ID": "mz-comp-1", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c1",
         "COMPOSER": "ROY ERNEST HAY THE GREATEST ROCK GEMINI SUN MAC", "IPI": "323735", "STATUS": "Active",
         "ISWC": "T0700428041"},
        {"COMPOSER_ID": "mz-comp-2", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c2", "COMPOSER": "JOHN SMITH",
         "IPI": "523736", "STATUS": "Active", "ISWC": "T0700428042"},
        {"COMPOSER_ID": "mz-comp-3", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c3", "COMPOSER": "BRIAN WILSON",
         "IPI": "723737", "STATUS": "Active", "ISWC": "T0700428043"},
        {"COMPOSER_ID": "mz-comp-4", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c4", "COMPOSER": "DAVID TAYLOR",
         "IPI": "823738", "STATUS": "Active", "ISWC": "T0700428044"},
        {"COMPOSER_ID": "mz-comp-5", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c5", "COMPOSER": "JACK WAGNER",
         "IPI": "923739", "STATUS": "Active", "ISWC": "T0700428045"},
        {"COMPOSER_ID": "mz-comp-6", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c6",
         "COMPOSER": "LUDWIG VAN BEETHOVEN", "IPI": "123740", "STATUS": "Active", "ISWC": "T0700428046"},
        {"COMPOSER_ID": "mz-comp-7", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c7",
         "COMPOSER": "LOUIS D. ARMSTRONG", "IPI": "223741", "STATUS": "Active", "ISWC": "T0700428047"},
        {"COMPOSER_ID": "mz-comp-8", "TRACK_ID": "mz-fdbe5c86458643076e5514de8111d3c8", "COMPOSER": "JOHN LENNON",
         "IPI": "323742", "STATUS": "Active", "ISWC": "T0700428048"}
    ]

    # Example ADC works data
    adc_works_data = [
        {"APRA_WORK_ID": "GW01421940", "TITLE": "EXAMPLE WORK 1",
         "COMPOSER_NAMES": "HAY ROY ERNEST THE GREATEST AND GEMINI ROCK MAC SUN", "ISWC": "T0700428041", "CD_TYPE": "1",
         "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW01421941", "TITLE": "EXAMPLE WORK 2", "COMPOSER_NAMES": "SMITH JOHN", "ISWC": "T0700428042",
         "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW01421942", "TITLE": "EXAMPLE WORK 3", "COMPOSER_NAMES": "WILSON BRIAN",
         "ISWC": "T0700428043", "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW01421943", "TITLE": "EXAMPLE WORK 4", "COMPOSER_NAMES": "TAYLOR D", "ISWC": "T0700428044",
         "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW01421944", "TITLE": "EXAMPLE WORK 5", "COMPOSER_NAMES": "J WAGNER", "ISWC": "T0700428045",
         "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW01421945", "TITLE": "EXAMPLE WORK 6", "COMPOSER_NAMES": "VAN BEETHOVEN L",
         "ISWC": "T0700428046", "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW01421946", "TITLE": "EXAMPLE WORK 7", "COMPOSER_NAMES": "ARMSTRONG LOUIS DANIEL",
         "ISWC": "T0700428047", "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW01421947", "TITLE": "EXAMPLE WORK 8", "COMPOSER_NAMES": "LENNON JOHN WINSTON",
         "ISWC": "T0700428048", "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"}
    ]

    # Create DataFrames from the example data
    adc_composers_df = session.create_dataframe(adc_composers_data)
    mazooka_composers_df = session.create_dataframe(mazooka_composers_data)
    adc_works_df = session.create_dataframe(adc_works_data)

    # Return the DataFrames without persisting to tables
    return {
        "adc_composers": adc_composers_df,
        "mazooka_composers": mazooka_composers_df,
        "adc_works": adc_works_df
    }


def clean_text(text_col):
    """Apply basic cleaning rules: uppercase and remove leading/trailing whitespace"""
    # Remove bracket content and clean text
    cleaned_text = regexp_replace(text_col, r'\([^\)]*\)', '')  # Remove content in parentheses
    return upper(trim(cleaned_text))


def split_composer_names(session, df, composer_col):
    """Split composers where multiple exist using Snowpark DataFrame operations"""
    print(f"Splitting composer names in column {composer_col}")

    try:
        # First, clean the text to remove bracket content
        df = df.withColumn(composer_col, clean_text(col(composer_col)))

        # Use the explode function with the split operation for slash delimiter
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
        print(f"Error in split_composer_names: {str(e)}")
        # Try a fallback approach if the first method fails
        print("Trying fallback approach for name splitting")
        return fallback_split_composer_names(session, df, composer_col)


def fallback_split_composer_names(session, df, composer_col):
    """Fallback method for splitting composer names using SQL"""
    # Create a SQL statement that doesn't rely on temporary tables
    cols = ", ".join([c for c in df.columns if c != composer_col])

    # Convert the DataFrame to SQL
    df_sql = df._to_sql()

    # First remove bracket content
    sql = f"""
    WITH cleaned AS (
        SELECT 
            {cols},
            TRIM(REGEXP_REPLACE({composer_col}, '\\\\([^\\\\)]*\\\\)', '')) AS cleaned_{composer_col}
        FROM 
            ({df_sql}) src
    ),
    slash_split AS (
        SELECT 
            {cols},
            TRIM(s.value) AS slash_value
        FROM 
            cleaned t,
            TABLE(SPLIT_TO_TABLE(t.cleaned_{composer_col}, '/')) s
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
        print(f"Fallback method also failed: {str(e)}")
        # If both methods fail, return the original dataframe with warning
        logger.warning("Unable to split composer names, returning original dataframe")
        return df


# Phase 1
def phase1_preprocessing(session, use_example_data=False, data_sources=None, save_to_tables=True):
    """Phase 1: Preprocessing and identifying truncated composers using Snowpark

    Args:
        session: Snowpark session
        use_example_data: If True, uses data from data_sources instead of querying tables
        data_sources: Dictionary with example datasets (only used if use_example_data is True)
        save_to_tables: If True, saves intermediate results to tables
    """
    print("Starting Phase 1: Preprocessing and truncation identification...")

    try:
        # Either use the example data or load from Snowflake tables
        if use_example_data and data_sources:
            print("Using example dataset for Phase 1")
            adc_composers = data_sources["adc_composers"]
            mazooka_composers = data_sources["mazooka_composers"]
            adc_works = data_sources["adc_works"]
        else:
            # Load data from Snowflake tables
            adc_composers = session.table("EDW_APPS.MATCHING.ADC_COMPOSERS_MATCHED_ISWC_VW")
            mazooka_composers = session.table("EDW_APPS.MATCHING.MAZOOKA_COMPOSERS_MATCHED_ISWC_VW")
            adc_works = session.table("EDW_APPS.MATCHING.ADC_WORKS_MATCHED_ISWC_VW")

        # Get row counts for initial data
        adc_count = adc_composers.count()
        mazooka_count = mazooka_composers.count()
        print(f"Loaded {adc_count} ADC composer rows and {mazooka_count} Mazooka composer rows")

        # Apply Rule 1: Convert text columns to uppercase and trim
        # For ADC data
        for column in adc_composers.columns:
            if adc_composers.schema[column].datatype.type_name() in ['VARCHAR', 'STRING', 'TEXT']:
                adc_composers = adc_composers.withColumn(column, clean_text(col(column)))

        # For Mazooka data
        for column in mazooka_composers.columns:
            if mazooka_composers.schema[column].datatype.type_name() in ['VARCHAR', 'STRING', 'TEXT']:
                mazooka_composers = mazooka_composers.withColumn(column, clean_text(col(column)))

        print("Text columns cleaned and standardized")

        # Create temporary views for SQL access with unique names for phase 1
        adc_composers.create_or_replace_temp_view("temp_adc_composers_phase1")
        mazooka_composers.create_or_replace_temp_view("temp_mazooka_composers_phase1")

        # Use a direct SQL approach for splitting
        print("Splitting ADC composer names...")
        adc_split_sql = """
        WITH source_data AS (
            SELECT * FROM temp_adc_composers_phase1
        ),
        cleaned AS (
            SELECT 
                *,
                TRIM(REGEXP_REPLACE(NAME, '\\\\([^\\\\)]*\\\\)', '')) AS cleaned_name
            FROM 
                source_data
        ),
        slash_split AS (
            SELECT 
                src.*,
                TRIM(f.value) as split_value
            FROM 
                cleaned src,
                LATERAL FLATTEN(input => STRTOK_TO_ARRAY(src.cleaned_name, '/')) f
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
        print(f"Expanded ADC data to approximately {expanded_adc_df.count()} rows")

        print("Splitting Mazooka composer names...")
        mazooka_split_sql = """
        WITH source_data AS (
            SELECT * FROM temp_mazooka_composers_phase1
        ),
        cleaned AS (
            SELECT 
                *,
                TRIM(REGEXP_REPLACE(COMPOSER, '\\\\([^\\\\)]*\\\\)', '')) AS cleaned_composer
            FROM 
                source_data
        ),
        slash_split AS (
            SELECT 
                src.*,
                TRIM(f.value) as split_value
            FROM 
                cleaned src,
                LATERAL FLATTEN(input => STRTOK_TO_ARRAY(src.cleaned_composer, '/')) f
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
        print(f"Expanded Mazooka data to approximately {expanded_mazooka_df.count()} rows")

        # Create temporary views for the expanded dataframes with unique names
        expanded_adc_df.create_or_replace_temp_view("temp_expanded_adc_phase1")
        expanded_mazooka_df.create_or_replace_temp_view("temp_expanded_mazooka_phase1")

        # Count composers per work and per track using explicit SQL
        print("Counting composers per work and track...")

        # For ADC data
        adc_count_sql = """
        SELECT 
            APRA_WORK_ID, 
            COUNT(*) AS ADC_COMPOSERS_COUNT
        FROM 
            temp_expanded_adc_phase1
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
            temp_expanded_mazooka_phase1
        GROUP BY 
            TRACK_ID, ISWC
        """
        mazooka_composer_count = session.sql(mazooka_count_sql)

        # Create temporary view for mazooka_composer_count
        mazooka_composer_count.create_or_replace_temp_view("temp_mazooka_count_phase1")

        # Get the max MAZOOKA_COMPOSERS_COUNT for each ISWC
        mazooka_max_sql = """
        SELECT 
            ISWC, 
            MAX(MAZOOKA_COMPOSERS_COUNT) AS MAZOOKA_COMPOSERS_COUNT
        FROM 
            temp_mazooka_count_phase1
        GROUP BY 
            ISWC
        """
        mazooka_max_count = session.sql(mazooka_max_sql)

        # Make sure adc_works is available as a temp view with unique name for phase 1
        adc_works.create_or_replace_temp_view("temp_adc_works_phase1")

        # Merge work data with composer counts
        work_data = adc_works.join(adc_composer_count, on=["APRA_WORK_ID"], how="left")
        work_data = work_data.join(mazooka_max_count, on=["ISWC"], how="left")

        # Fill NaN values
        work_data = work_data.fillna({"ADC_COMPOSERS_COUNT": 0, "MAZOOKA_COMPOSERS_COUNT": 0})

        # Get composer_names length
        if "COMPOSER_NAMES" in work_data.columns:
            work_data = work_data.withColumn("COMPOSER_NAME_LENGTH", length(col("COMPOSER_NAMES")))
        else:
            work_data = work_data.withColumn("COMPOSER_NAME_LENGTH", lit(0))

        # Apply the FIXED truncation rule - now checking for exactly 40 chars or 39 chars with trailing space
        work_data = work_data.withColumn(
            "YN_COMPOSERS_TRUNC",
            when(
                (col("YN_PERF_OWNERSHIP") == "N") &
                (
                        (col("COMPOSER_NAME_LENGTH") == 40) |
                        ((col("COMPOSER_NAME_LENGTH") == 39) &
                         col("COMPOSER_NAMES").endswith(" "))
                ) &
                (col("ADC_COMPOSERS_COUNT") < col("MAZOOKA_COMPOSERS_COUNT")),
                lit("Y")
            ).otherwise(lit("N"))
        )

        # Save intermediate tables to Snowflake if requested
        if save_to_tables:
            expanded_adc_df.write.mode("overwrite").save_as_table("PHASE1_CLEANED_ADC_COMPOSERS")
            expanded_mazooka_df.write.mode("overwrite").save_as_table("PHASE1_CLEANED_MAZOOKA_COMPOSERS")
            work_data.write.mode("overwrite").save_as_table("PHASE1_WORK_DATA_WITH_FLAGS")
            print("Phase 1 complete! Intermediate tables created for Phase 2.")
        else:
            print("Phase 1 complete! (Tables not saved in example mode)")

        return {
            "cleaned_adc_composers": expanded_adc_df,
            "cleaned_mazooka_composers": expanded_mazooka_df,
            "work_data_with_flags": work_data
        }
    except Exception as e:
        print(f"Error in phase1_preprocessing: {str(e)}", exc_info=True)
        raise


# Phase 2
def phase2_name_parsing(session, use_example_data=False, phase1_results=None, save_to_tables=True):
    """Phase 2: Parse names into first and last name components and apply new composition scoring

    Args:
        session: Snowpark session
        use_example_data: If True, uses data from phase1_results instead of querying tables
        phase1_results: Results from Phase 1 (only used if use_example_data is True)
        save_to_tables: If True, saves intermediate results to tables
    """
    print("Starting Phase 2: Name parsing with updated composition scoring...")

    try:
        # Either use the data from Phase 1 or load from Snowflake tables
        if use_example_data and phase1_results:
            print("Using example dataset from Phase 1 for Phase 2")
            adc_composers = phase1_results["cleaned_adc_composers"]
            mazooka_composers = phase1_results["cleaned_mazooka_composers"]
            work_data = phase1_results["work_data_with_flags"]
        else:
            # Load tables from Phase 1
            adc_composers = session.table("PHASE1_CLEANED_ADC_COMPOSERS")
            mazooka_composers = session.table("PHASE1_CLEANED_MAZOOKA_COMPOSERS")
            work_data = session.table("PHASE1_WORK_DATA_WITH_FLAGS")

        print(f"Loaded ADC composers and Mazooka composers")

        # Create temporary views for the dataframes with unique names for phase 2
        adc_composers.create_or_replace_temp_view("temp_adc_composers_phase2")
        work_data.create_or_replace_temp_view("temp_work_data_phase2")
        mazooka_composers.create_or_replace_temp_view("temp_mazooka_composers_phase2")

        # Create the updated name parsing function with improved composition scoring
        print("Creating updated name parsing and scoring functions...")

        session.sql("""
        CREATE OR REPLACE FUNCTION PARSE_NAME_SQL(name STRING)
        RETURNS OBJECT
        LANGUAGE JAVASCRIPT
        AS
        $$
        function parseNameJS(name) {
            if (!name || name === "") {
                return {first: "", last: "", suffix: "", is_initial: false};
            }

            // Remove content in brackets first
            name = name.replace(/\([^)]*\)/g, "");

            // Special suffixes and prefixes
            const suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"];
            const special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"];

            // Clean and split the name
            name = name.trim();
            let parts = name.split(/\s+/);

            // Handle name with no spaces
            if (parts.length === 1) {
                return {first: "", last: parts[0], suffix: "", is_initial: false};
            }

            // Check for and extract suffixes
            let suffix = "";
            for (const suffixTerm of suffixes) {
                const suffixIndex = parts.findIndex(part => part === suffixTerm);
                if (suffixIndex !== -1) {
                    suffix = parts[suffixIndex];
                    parts.splice(suffixIndex, 1); // Remove suffix from parts
                    break;
                }
            }

            // After removing suffix, check if we're back to a single name
            if (parts.length === 1) {
                return {first: "", last: parts[0], suffix: suffix, is_initial: false};
            }

            // Check for special multi-word last names (e.g., "VAN BEETHOVEN")
            for (let i = 0; i < parts.length - 1; i++) {
                if (special_prefixes.includes(parts[i])) {
                    // Found a special prefix
                    if (i === 0) {
                        // If prefix is first word, assume no first name
                        return {
                            first: "", 
                            last: parts.join(" "), 
                            suffix: suffix, 
                            is_initial: false
                        };
                    } else {
                        // Otherwise assume format is "FIRST PREFIX LASTNAME"
                        const firstName = parts.slice(0, i).join(" ");
                        const lastName = parts.slice(i).join(" ");
                        const isInitial = firstName.length === 1;

                        return {
                            first: firstName,
                            last: lastName,
                            suffix: suffix,
                            is_initial: isInitial
                        };
                    }
                }
            }

            // Check if this is in "LAST FIRST" format - common in music industry
            if (parts.length === 2) {
                // If second part is single letter (likely an initial)
                if (parts[1].length === 1) {
                    // This is likely "LASTNAME INITIAL" format
                    return {
                        first: parts[1], 
                        last: parts[0], 
                        suffix: suffix, 
                        is_initial: true
                    };
                }
                // If first part is single letter (likely an initial)
                else if (parts[0].length === 1) {
                    // This is likely "INITIAL LASTNAME" format
                    return {
                        first: parts[0], 
                        last: parts[1], 
                        suffix: suffix, 
                        is_initial: true
                    };
                }
            }

            // Default: standard "FIRST LAST" format (first word is first name, remaining words are last name)
            const firstName = parts[0];
            const lastName = parts.slice(1).join(" ");
            const isInitial = firstName.length === 1;

            return {
                first: firstName, 
                last: lastName, 
                suffix: suffix, 
                is_initial: isInitial
            };
        }

        return parseNameJS(NAME);
        $$;
        """).collect()

        # Updated composition scoring function based on new requirements
        session.sql("""
        CREATE OR REPLACE FUNCTION CALCULATE_NAME_SCORE_SQL(name_obj OBJECT)
        RETURNS FLOAT
        LANGUAGE JAVASCRIPT
        AS
        $$
        function calculateNameScore(name_obj) {
            if (!name_obj) {
                return 0.0;
            }

            let score = 0.0;
            const hasFirst = name_obj.first && name_obj.first.trim().length > 0;
            const hasLast = name_obj.last && name_obj.last.trim().length > 0;
            const isFirstInitial = name_obj.is_initial;

            // Scoring based on the specified requirements:
            // - Last name: 2 points
            if (hasLast) {
                score += 2.0;
            }

            // - First name: 1 point (or 0.5 if it's an initial)
            if (hasFirst) {
                if (isFirstInitial) {
                    score += 0.5;
                } else {
                    score += 1.0;
                }
            }

            // Total possible scores:
            // First Name + Last Name = 3.0
            // First Initial + Last Name = 2.5
            // Only Last Name = 2.0
            // Only First Name = 1.0

            return score;
        }

        return calculateNameScore(NAME_OBJ);
        $$;
        """).collect()

        print("UDFs created successfully")

        # Process ADC names with ADC_COMPOSER_ID
        print("Parsing ADC composer names...")

        adc_parsed_sql = """
        SELECT 
            a.APRA_WORK_ID,
            a.ISWC,
            a.NAME as APRA_NAME,
            a.ADC_COMPOSER_ID,
            PARSE_NAME_SQL(a.NAME):first::STRING as APRA_FIRST_NAME,
            PARSE_NAME_SQL(a.NAME):last::STRING as APRA_LAST_NAME,
            PARSE_NAME_SQL(a.NAME):suffix::STRING as APRA_SUFFIX,
            PARSE_NAME_SQL(a.NAME):is_initial::BOOLEAN as APRA_HAS_INITIAL,
            CALCULATE_NAME_SCORE_SQL(PARSE_NAME_SQL(a.NAME)) as APRA_NAME_SCORE,
            w.YN_COMPOSERS_TRUNC
        FROM 
            temp_adc_composers_phase2 a
        LEFT JOIN 
            temp_work_data_phase2 w
        ON 
            a.APRA_WORK_ID = w.APRA_WORK_ID
        """

        adc_parsed_df = session.sql(adc_parsed_sql)
        adc_count = adc_parsed_df.count()
        print(f"Parsed {adc_count} ADC composer names")

        # Process Mazooka names
        print("Parsing Mazooka composer names...")

        mazooka_parsed_sql = """
        SELECT 
            m.TRACK_ID,
            m.ISWC,
            m.COMPOSER as MAZOOKA_NAME,
            PARSE_NAME_SQL(m.COMPOSER):first::STRING as MAZOOKA_FIRST_NAME,
            PARSE_NAME_SQL(m.COMPOSER):last::STRING as MAZOOKA_LAST_NAME,
            PARSE_NAME_SQL(m.COMPOSER):suffix::STRING as MAZOOKA_SUFFIX,
            PARSE_NAME_SQL(m.COMPOSER):is_initial::BOOLEAN as MAZOOKA_HAS_INITIAL,
            CALCULATE_NAME_SCORE_SQL(PARSE_NAME_SQL(m.COMPOSER)) as MAZOOKA_NAME_SCORE
        FROM 
            temp_mazooka_composers_phase2 m
        """

        mazooka_parsed_df = session.sql(mazooka_parsed_sql)
        mazooka_count = mazooka_parsed_df.count()
        print(f"Parsed {mazooka_count} Mazooka composer names")

        # Save intermediate results to Snowflake tables if requested
        if save_to_tables:
            adc_parsed_df.write.mode("overwrite").save_as_table("PHASE2_ADC_PARSED_NAMES")
            mazooka_parsed_df.write.mode("overwrite").save_as_table("PHASE2_MAZOOKA_PARSED_NAMES")
            print("Phase 2 complete! Parsed name tables saved for Phase 3.")
        else:
            print("Phase 2 complete! (Tables not saved in example mode)")

        return {
            "adc_parsed_df": adc_parsed_df,
            "mazooka_parsed_df": mazooka_parsed_df
        }
    except Exception as e:
        print(f"Error in phase2_name_parsing: {str(e)}", exc_info=True)
        # Print the full traceback for better debugging
        import traceback
        print(traceback.format_exc())
        raise


# Phase 3
def phase3_matching(session, use_example_data=False, phase2_results=None, save_to_tables=True):
    """Phase 3: Generate match scores with new formula and final output

    Args:
        session: Snowpark session
        use_example_data: If True, uses data from phase2_results instead of querying tables
        phase2_results: Results from Phase 2 (only used if use_example_data is True)
        save_to_tables: If True, saves final results to tables
    """
    print("Starting Phase 3: Match score generation using new formula...")

    try:
        # Either use the data from Phase 2 or load from Snowflake tables
        if use_example_data and phase2_results:
            print("Using example dataset from Phase 2 for Phase 3")
            adc_parsed_df = phase2_results["adc_parsed_df"]
            mazooka_parsed_df = phase2_results["mazooka_parsed_df"]
        else:
            # Load intermediate tables from Phase 2
            adc_parsed_df = session.table("PHASE2_ADC_PARSED_NAMES")
            mazooka_parsed_df = session.table("PHASE2_MAZOOKA_PARSED_NAMES")

        print("Loaded parsed name data for matching")

        # Get row counts
        adc_count = adc_parsed_df.count()
        mazooka_count = mazooka_parsed_df.count()
        print(f"Found {adc_count} ADC records and {mazooka_count} Mazooka records")

        # Create temporary views for the dataframes with unique names for phase 3
        adc_parsed_df.create_or_replace_temp_view("temp_adc_parsed_phase3")
        mazooka_parsed_df.create_or_replace_temp_view("temp_mazooka_parsed_phase3")

        # Create new match score function based on updated matching requirements
        print("Creating new name similarity and match score functions...")

        # Split the function creation into separate SQL statements
        # First function: NAME_SIMILARITY_SCORE
        session.sql("""
        CREATE OR REPLACE FUNCTION NAME_SIMILARITY_SCORE(
            apra_first STRING, 
            apra_last STRING, 
            apra_has_initial BOOLEAN,
            mazooka_first STRING, 
            mazooka_last STRING,
            mazooka_has_initial BOOLEAN)
        RETURNS OBJECT
        LANGUAGE JAVASCRIPT
        AS
        $$
        function nameSimilarityScore(apraFirst, apraLast, apraHasInitial, mazookaFirst, mazookaLast, mazookaHasInitial) {
            // Convert null to empty strings
            const apra_first = apraFirst || "";
            const apra_last = apraLast || "";
            const mazooka_first = mazookaFirst || "";
            const mazooka_last = mazookaLast || "";

            let score = 0;
            let lastNameScore = 0;
            let firstNameScore = 0;

            // Required: Last names must match
            if (apra_last.trim() === "" || mazooka_last.trim() === "") {
                // If either last name is missing, no match is possible
                return {score: 0, last_name_score: 0, first_name_score: 0};
            }

            // Check for exact last name match (2 points)
            if (apra_last.trim() === mazooka_last.trim()) {
                lastNameScore = 2;
            } else {
                // Implement fuzzy match for last name (1.5 points if >= 0.93 similarity)
                // For simplicity, let's use a basic similarity metric based on string length ratio
                const maxLength = Math.max(apra_last.length, mazooka_last.length);
                const minLength = Math.min(apra_last.length, mazooka_last.length);
                const lengthRatio = minLength / maxLength;

                // Calculate common character count
                let commonChars = 0;
                for (let i = 0; i < apra_last.length; i++) {
                    if (mazooka_last.includes(apra_last[i])) {
                        commonChars++;
                    }
                }
                const charRatio = commonChars / maxLength;

                // Combined similarity
                const similarity = (lengthRatio + charRatio) / 2;

                if (similarity >= 0.93) {
                    lastNameScore = 1.5;
                } else {
                    // Last names don't match and aren't similar enough
                    return {score: 0, last_name_score: 0, first_name_score: 0};
                }
            }

            // First name matching
            if (apra_first.trim() !== "" && mazooka_first.trim() !== "") {
                // Check for exact first name match (1 point)
                if (apra_first.trim() === mazooka_first.trim()) {
                    firstNameScore = 1;
                } else {
                    // Check for fuzzy match (0.5 points if >= 0.93 similarity)
                    const maxLength = Math.max(apra_first.length, mazooka_first.length);
                    const minLength = Math.min(apra_first.length, mazooka_first.length);
                    const lengthRatio = minLength / maxLength;

                    // Calculate common character count
                    let commonChars = 0;
                    for (let i = 0; i < apra_first.length; i++) {
                        if (mazooka_first.includes(apra_first[i])) {
                            commonChars++;
                        }
                    }
                    const charRatio = commonChars / maxLength;

                    // Combined similarity
                    const similarity = (lengthRatio + charRatio) / 2;

                    if (similarity >= 0.93) {
                        firstNameScore = 0.5;
                    }
                    // Check for initial match (0.5 points)
                    else if ((apraHasInitial || mazookaHasInitial) &&
                            (apra_first.charAt(0) === mazooka_first.charAt(0))) {
                        firstNameScore = 0.5;
                    }
                }
            }
            // Check for initial match with full name
            else if (apra_first.trim() !== "" && apraHasInitial && 
                    mazooka_first.trim() !== "" && !mazookaHasInitial &&
                    apra_first.charAt(0) === mazooka_first.charAt(0)) {
                firstNameScore = 0.5;
            }
            else if (mazooka_first.trim() !== "" && mazookaHasInitial && 
                    apra_first.trim() !== "" && !apraHasInitial &&
                    mazooka_first.charAt(0) === apra_first.charAt(0)) {
                firstNameScore = 0.5;
            }

            // Calculate total score
            score = lastNameScore + firstNameScore;

            return {
                score: score,
                last_name_score: lastNameScore,
                first_name_score: firstNameScore
            };
        }

        return nameSimilarityScore(APRA_FIRST, APRA_LAST, APRA_HAS_INITIAL, MAZOOKA_FIRST, MAZOOKA_LAST, MAZOOKA_HAS_INITIAL);
        $$;
        """).collect()

        # Second function: CALCULATE_MATCH_SCORE
        session.sql("""
        CREATE OR REPLACE FUNCTION CALCULATE_MATCH_SCORE(
            apra_score FLOAT, 
            mazooka_score FLOAT, 
            similarity_obj OBJECT)
        RETURNS FLOAT
        LANGUAGE JAVASCRIPT
        AS
        $$
        function calculateMatchScore(apraScore, mazookaScore, similarityObj) {
            // If either composer score is 0 or similarity score is 0, return 0
            if (apraScore <= 0 || mazookaScore <= 0 || !similarityObj || similarityObj.score <= 0) {
                return 0.0;
            }

            // Calculate the normalized match score
            const similarityScore = similarityObj.score;

            // Calculate ratio of min/max scores (composition score)
            const minScore = Math.min(apraScore, mazookaScore);
            const maxScore = Math.max(apraScore, mazookaScore);
            const compositionRatio = minScore / maxScore;

            // Normalize similarity score to a 0-1 range (max possible similarity is 3.0)
            const normalizedSimilarity = Math.min(similarityScore / 3.0, 1.0);

            // Final match score is composition ratio, ensuring it's never greater than 1
            // (the existing match score calculation is already capped at 1.0)
            return Math.min(compositionRatio, 1.0);
        }

        return calculateMatchScore(APRA_SCORE, MAZOOKA_SCORE, SIMILARITY_OBJ);
        $$;
        """).collect()

        print("Match score functions created successfully")

        # Filter for valid ISWCs that exist in both datasets
        print("Finding common ISWCs between datasets...")

        valid_iswcs_sql = """
        WITH adc_iswcs AS (
            SELECT DISTINCT ISWC 
            FROM temp_adc_parsed_phase3 
            WHERE ISWC IS NOT NULL
        ),
        mazooka_iswcs AS (
            SELECT DISTINCT ISWC 
            FROM temp_mazooka_parsed_phase3 
            WHERE ISWC IS NOT NULL
        )
        SELECT a.ISWC
        FROM adc_iswcs a
        INNER JOIN mazooka_iswcs m
        ON a.ISWC = m.ISWC
        """

        valid_iswcs = session.sql(valid_iswcs_sql)
        valid_iswcs.create_or_replace_temp_view("temp_valid_iswcs_phase3")

        count_valid_iswcs = valid_iswcs.count()
        print(f"Found {count_valid_iswcs} ISWCs that exist in both datasets")

        # If no matching ISWCs, handle gracefully
        if count_valid_iswcs == 0:
            logger.warning("No matching ISWCs found between datasets. Creating empty result.")
            # Create an empty result dataframe with expected schema
            result_columns = [
                "ROW_NUM", "APRA_NAME", "APRA_NAME_SCORE", "MATCH_STATUS", "MAZOOKA_NAME",
                "MAZOOKA_NAME_SCORE", "NAME_MATCHED_SCORE", "WORK_ID", "TRACK_ID",
                "ISWC", "MATCH_PERCENT", "YN_COMPOSERS_TRUNC", "ADC_COMPOSER_ID"
            ]
            empty_df = session.create_dataframe([], schema=result_columns)

            # Save empty results to a Snowflake table if requested
            if save_to_tables:
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                final_table_name = f"COMPOSER_NAME_MATCHING_RESULTS"
                empty_df.write.mode("overwrite").save_as_table(final_table_name)
                print(f"Saved empty results to {final_table_name}")
            else:
                final_table_name = "No table created (example mode)"
                print("No matches found (no table created in example mode)")

            return empty_df, final_table_name

        # Generate potential matches with new scoring approach
        print("Generating potential matches and calculating scores using new formula...")

        potential_matches_sql = """
        SELECT 
            a.APRA_NAME,
            a.ADC_COMPOSER_ID,
            a.APRA_NAME_SCORE,
            m.MAZOOKA_NAME,
            m.MAZOOKA_NAME_SCORE,
            NAME_SIMILARITY_SCORE(
                a.APRA_FIRST_NAME, 
                a.APRA_LAST_NAME, 
                a.APRA_HAS_INITIAL,
                m.MAZOOKA_FIRST_NAME, 
                m.MAZOOKA_LAST_NAME,
                m.MAZOOKA_HAS_INITIAL
            ) AS NAME_SIMILARITY_OBJ,
            CALCULATE_MATCH_SCORE(
                a.APRA_NAME_SCORE, 
                m.MAZOOKA_NAME_SCORE, 
                NAME_SIMILARITY_SCORE(
                    a.APRA_FIRST_NAME, 
                    a.APRA_LAST_NAME, 
                    a.APRA_HAS_INITIAL,
                    m.MAZOOKA_FIRST_NAME, 
                    m.MAZOOKA_LAST_NAME,
                    m.MAZOOKA_HAS_INITIAL
                )
            ) AS NAME_MATCHED_SCORE,
            a.APRA_WORK_ID AS WORK_ID,
            m.TRACK_ID,
            a.ISWC,
            a.YN_COMPOSERS_TRUNC,
            NAME_SIMILARITY_SCORE(
                a.APRA_FIRST_NAME, 
                a.APRA_LAST_NAME, 
                a.APRA_HAS_INITIAL,
                m.MAZOOKA_FIRST_NAME, 
                m.MAZOOKA_LAST_NAME,
                m.MAZOOKA_HAS_INITIAL
            ):score::FLOAT AS SIMILARITY_SCORE
        FROM 
            temp_adc_parsed_phase3 a
        JOIN 
            temp_mazooka_parsed_phase3 m
        ON 
            a.ISWC = m.ISWC
        WHERE
            a.ISWC IN (SELECT ISWC FROM temp_valid_iswcs_phase3)
            AND NAME_SIMILARITY_SCORE(
                a.APRA_FIRST_NAME, 
                a.APRA_LAST_NAME, 
                a.APRA_HAS_INITIAL,
                m.MAZOOKA_FIRST_NAME, 
                m.MAZOOKA_LAST_NAME,
                m.MAZOOKA_HAS_INITIAL
            ):score::FLOAT > 0
        """

        potential_matches = session.sql(potential_matches_sql)
        potential_matches.create_or_replace_temp_view("temp_potential_matches_phase3")

        match_count = potential_matches.count()
        print(f"Generated {match_count} potential matches with positive scores")

        # Calculate match percentage based on name scores ratio
        print("Calculating match percentage using min/max ratio...")

        match_percentage_sql = """
        SELECT 
            p.*,
            CASE 
                WHEN p.APRA_NAME_SCORE > 0 AND p.MAZOOKA_NAME_SCORE > 0 THEN 
                    ROUND((LEAST(p.APRA_NAME_SCORE, p.MAZOOKA_NAME_SCORE) / 
                           GREATEST(p.APRA_NAME_SCORE, p.MAZOOKA_NAME_SCORE)) * 100)
                ELSE 0
            END AS MATCH_PERCENT
        FROM 
            temp_potential_matches_phase3 p
        WHERE 
            p.NAME_MATCHED_SCORE > 0
        ORDER BY 
            p.ISWC, p.NAME_MATCHED_SCORE DESC
        """

        result_df = session.sql(match_percentage_sql)

        formatted_output_sql = """
        WITH ranked_matches AS (
            SELECT
                *,
                ROW_NUMBER() OVER (PARTITION BY ISWC, WORK_ID, TRACK_ID ORDER BY NAME_MATCHED_SCORE DESC) AS RANK
            FROM
                ({0})
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY ISWC, WORK_ID, TRACK_ID, NAME_MATCHED_SCORE DESC) AS ROW_NUM,
            APRA_NAME, 
            APRA_NAME_SCORE, 
            'match' AS MATCH_STATUS, 
            MAZOOKA_NAME, 
            MAZOOKA_NAME_SCORE, 
            NAME_MATCHED_SCORE, 
            WORK_ID, 
            TRACK_ID, 
            ISWC, 
            MATCH_PERCENT, 
            YN_COMPOSERS_TRUNC,
            ADC_COMPOSER_ID
        FROM 
            ranked_matches
        ORDER BY
            ISWC, WORK_ID, TRACK_ID, NAME_MATCHED_SCORE DESC
        """.format(match_percentage_sql)

        result_df = session.sql(formatted_output_sql)

        # Debug final result
        result_count = result_df.count()
        print(f"Generated {result_count} matches in final result")

        # if result_count > 0:
        #     print("Sample result data:")
        #     sample_results = result_df.limit(5).collect()
        #     for row in sample_results:
        #         print(str(row))

        # Save final results to a Snowflake table if requested
        if save_to_tables:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            final_table_name = f"COMPOSER_NAME_MATCHING_RESULTS"
            # final_table_name = f"COMPOSER_NAME_MATCHING_RESULTS_{timestamp}"
            result_df.write.mode("overwrite").save_as_table(final_table_name)
            print(f"Successfully wrote {result_count} results to final table: {final_table_name}")
        else:
            final_table_name = "No table created (example mode)"
            print(f"Example mode: {result_count} results generated (no table created)")

        print("Name matching process complete!")

        return result_df, final_table_name
    except Exception as e:
        print(f"Error in phase3_matching: {str(e)}", exc_info=True)
        # Print the full traceback for better debugging
        import traceback
        print(traceback.format_exc())
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
            print(f"Dropping temporary table: {table}")
            session.sql(f"DROP TABLE IF EXISTS {table}").collect()

        print("All temporary tables have been dropped successfully")
    except Exception as e:
        print(f"Error while cleaning up temporary tables: {str(e)}")
        logger.warning("Continuing execution despite cleanup errors")


def main(session, use_example_data=False):
    """Main function to orchestrate the three-phase name matching process

    Args:
        session: Snowpark session
        use_example_data: If True, uses example dataset instead of querying Snowflake tables
    """
    print("Starting name matching process with three-phase approach...")

    # Configuration for saving to tables (only save when using real data)
    save_to_tables = not use_example_data

    try:
        # Load example data if requested
        example_data = None
        if use_example_data:
            print("=== USING EXAMPLE DATASET ===")
            example_data = create_example_dataset(session)

        # Execute Phase 1: Preprocessing and truncation identification
        print("=== PHASE 1: PREPROCESSING AND TRUNCATION IDENTIFICATION ===")
        phase1_results = phase1_preprocessing(session, use_example_data, example_data, save_to_tables)

        # Execute Phase 2: Name parsing and score generation
        print("\n=== PHASE 2: NAME PARSING AND SCORE GENERATION ===")
        phase2_results = phase2_name_parsing(session, use_example_data, phase1_results, save_to_tables)

        # Execute Phase 3: Match score generation and final output
        print("\n=== PHASE 3: MATCH SCORE GENERATION AND FINAL OUTPUT ===")
        final_results, final_table_name = phase3_matching(session, use_example_data, phase2_results, save_to_tables)

        # Clean up temporary tables if we created them
        if not use_example_data:
            print("\n=== CLEANING UP TEMPORARY TABLES ===")
            cleanup_temp_tables(session)

        print("\nAll phases completed successfully!")

        # Print results table for the example dataset
        if use_example_data:
            print("\n=== EXAMPLE DATASET RESULTS ===")

            pd_results = final_results.to_pandas()
            print(pd_results.to_string(index=False))
        else:
            print(f"Final results saved to table: {final_table_name}")

        return final_results
    except Exception as e:
        print("Error in main function")
        raise


# Run with the full dataset (will use and save to Snowflake tables)
final_results = main(session)

# Run with the example dataset
# final_results = main(session, use_example_data=True)
