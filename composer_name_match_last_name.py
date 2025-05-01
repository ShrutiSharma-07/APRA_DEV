from snowflake.snowpark.functions import col, lit, upper, trim, length, when, regexp_replace
import datetime
import logging


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
        {"ADC_COMPOSER_ID": 43774662, "APRA_WORK_ID": "GW01421945", "IPI": "123740", "NAME": "BEETHOVEN LUDWIG VAN",
         "ISWC": "T0700428046"},
        {"ADC_COMPOSER_ID": 43774663, "APRA_WORK_ID": "GW01421946", "IPI": "223741", "NAME": "ARMSTRONG LOUIS DANIEL",
         "ISWC": "T0700428047"},
        {"ADC_COMPOSER_ID": 43774664, "APRA_WORK_ID": "GW01421947", "IPI": "323742", "NAME": "LENNON JOHN WINSTON",
         "ISWC": "T0700428048"},
        {"ADC_COMPOSER_ID": 44100861, "APRA_WORK_ID": "GW02005365", "IPI": "445678", "NAME": "MARTIN HUGH",
         "ISWC": "T0700726620"}
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
         "IPI": "323742", "STATUS": "Active", "ISWC": "T0700428048"},
        {"COMPOSER_ID": "mz-comp-9", "TRACK_ID": "mz-2bfcf0aa02a2eb187fb02952d46203c8", "COMPOSER": "HUGH MARTIN",
         "IPI": "445678", "STATUS": "Active", "ISWC": "T0700726620"}
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
         "ISWC": "T0700428048", "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"},
        {"APRA_WORK_ID": "GW02005365", "TITLE": "EXAMPLE WORK 9", "COMPOSER_NAMES": "MARTIN HUGH",
         "ISWC": "T0700726620", "CD_TYPE": "1", "YN_PERF_OWNERSHIP": "N", "YN_PROCESSED": "Y", "YN_PASS": "Y"}
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
        print("Warning: Unable to split composer names, returning original dataframe")
        return df


# Phase 1
def phase1_preprocessing(session, use_example_data=False, data_sources=None, save_to_tables=True):
    # Phase 1: Preprocessing and identifying truncated composers using Snowpark

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
        print(f"Error in phase1_preprocessing: {str(e)}")
        raise


# ENHANCED VERSION - Helper Functions for Phase 2
def create_enhanced_parse_name_function(session):
    """Create the enhanced name parsing function that handles different formats"""
    session.sql("""
    CREATE OR REPLACE FUNCTION ENHANCED_PARSE_NAME_SQL(name STRING)
    RETURNS OBJECT
    LANGUAGE JAVASCRIPT
    AS
    $$
    function enhancedParseNameJS(name) {
        if (!name || name === "") {
            return {first: "", last: "", middle: "", suffix: "", is_initial: false};
        }

        // Remove content in brackets first
        name = name.replace(/\\(.*?\\)/g, "");

        // Special suffixes and prefixes
        const suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"];
        const special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"];

        // Clean and split the name
        name = name.trim().toUpperCase();
        let parts = name.split(/\\s+/);

        // Handle name with no spaces
        if (parts.length === 1) {
            return {first: "", last: parts[0], middle: "", suffix: "", is_initial: false};
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
            return {first: "", last: parts[0], middle: "", suffix: suffix, is_initial: false};
        }

        // Check for special multi-word last names (e.g., "VAN BEETHOVEN")
        for (let i = 0; i < parts.length - 1; i++) {
            if (special_prefixes.includes(parts[i])) {
                // Found a special prefix - handle according to position
                if (i === 0) {
                    // If prefix is first word, assume format: PREFIX LASTNAME [FIRSTNAME]
                    if (parts.length > 2) {
                        // We have PREFIX LASTNAME FIRSTNAME format
                        const lastName = parts.slice(0, 2).join(" ");
                        const firstName = parts[2];
                        const middleName = parts.slice(3).join(" ");
                        const isInitial = firstName && firstName.length === 1;

                        return {
                            first: firstName,
                            last: lastName,
                            middle: middleName,
                            suffix: suffix,
                            is_initial: isInitial
                        };
                    } else {
                        // We just have PREFIX LASTNAME
                        return {
                            first: "",
                            last: parts.join(" "),
                            middle: "",
                            suffix: suffix,
                            is_initial: false
                        };
                    }
                } else {
                    // Otherwise assume format is "FIRSTNAME PREFIX LASTNAME"
                    const firstName = parts.slice(0, i).join(" ");
                    const lastName = parts.slice(i).join(" ");
                    const isInitial = firstName.length === 1;

                    return {
                        first: firstName,
                        last: lastName,
                        middle: "",
                        suffix: suffix,
                        is_initial: isInitial
                    };
                }
            }
        }

        // Parse based on number of parts (after removing suffix)
        if (parts.length === 2) {
            // Two-word name: this is where we need to be more flexible
            // We'll return the different possible interpretations
            const std_format = {
                first: parts[0],
                last: parts[1],
                middle: "",
                suffix: suffix,
                is_initial: parts[0].length === 1
            };

            const alt_format = {
                first: parts[1],
                last: parts[0],
                middle: "",
                suffix: suffix,
                is_initial: parts[1].length === 1
            };

            // Return both formats for checking
            return {
                first: std_format.first,
                last: std_format.last,
                middle: "",
                suffix: suffix,
                is_initial: std_format.is_initial,
                alt_first: alt_format.first,
                alt_last: alt_format.last,
                alt_is_initial: alt_format.is_initial
            };
        } 
        else if (parts.length >= 3) {
            // Multi-word name: Need to handle both formats
            // ADC format: LASTNAME FIRSTNAME MIDDLENAME
            // Mazooka format: FIRSTNAME MIDDLENAME LASTNAME

            // Standard format (assume Mazooka style: First Middle Last)
            const std_format = {
                first: parts[0],
                middle: parts.slice(1, parts.length - 1).join(" "),
                last: parts[parts.length - 1]
            };

            // Alternative format (assume ADC style: Last First Middle)
            const alt_format = {
                first: parts[1],
                middle: parts.slice(2).join(" "),
                last: parts[0]
            };

            return {
                first: std_format.first,
                last: std_format.last,
                middle: std_format.middle,
                suffix: suffix,
                is_initial: std_format.first.length === 1,
                alt_first: alt_format.first,
                alt_last: alt_format.last,
                alt_is_initial: alt_format.first.length === 1
            };
        }

        // Default fallback (should not reach here with the above logic)
        return {
            first: parts[0], 
            last: parts.slice(1).join(" "),
            middle: "",
            suffix: suffix, 
            is_initial: parts[0].length === 1
        };
    }

    return enhancedParseNameJS(NAME);
    $$
    """).collect()


def create_enhanced_calculate_name_score_function(session):
    """Create the enhanced name scoring function"""
    session.sql("""
    CREATE OR REPLACE FUNCTION ENHANCED_CALCULATE_NAME_SCORE_SQL(name_obj OBJECT)
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

        return score;
    }

    return calculateNameScore(NAME_OBJ);
    $$
    """).collect()


def create_enhanced_similarity_function(session):
    """Create the enhanced name similarity function that handles different formats"""
    session.sql("""
    CREATE OR REPLACE FUNCTION ENHANCED_NAME_SIMILARITY_SCORE(
        adc_name STRING,
        mazooka_name STRING,
        apra_score FLOAT,
        mazooka_score FLOAT)
    RETURNS OBJECT
    LANGUAGE JAVASCRIPT
    AS
    $$
    function calculateStringSimilarity(s1, s2) {
        if (!s1 || !s2) return 0;
        if (s1 === s2) return 1.0;

        // Convert to uppercase for comparison
        const str1 = s1.toUpperCase().trim();
        const str2 = s2.toUpperCase().trim();

        if (str1 === str2) return 1.0;
        if (str1 === "" || str2 === "") return 0.0;

        // Calculate Levenshtein distance for similarity
        const len1 = str1.length;
        const len2 = str2.length;

        // Create the distance matrix
        const matrix = Array(len1 + 1).fill().map(() => Array(len2 + 1).fill(0));

        // Initialize first row and column
        for (let i = 0; i <= len1; i++) matrix[i][0] = i;
        for (let j = 0; j <= len2; j++) matrix[0][j] = j;

        // Fill the matrix
        for (let i = 1; i <= len1; i++) {
            for (let j = 1; j <= len2; j++) {
                const cost = str1[i-1] === str2[j-1] ? 0 : 1;
                matrix[i][j] = Math.min(
                    matrix[i-1][j] + 1,      // deletion
                    matrix[i][j-1] + 1,      // insertion
                    matrix[i-1][j-1] + cost  // substitution
                );
            }
        }

        // Get the distance and calculate similarity
        const distance = matrix[len1][len2];
        const maxLen = Math.max(len1, len2);

        return 1 - (distance / maxLen);
    }

    function parseNameComponents(name) {
        if (!name || typeof name !== 'string') {
            return { firstName: "", lastName: "", middleName: "", suffix: "", isInitial: false };
        }

        // Clean name - remove brackets and trim
        name = name.replace(/\\(.*?\\)/g, "").trim().toUpperCase();
        if (!name) {
            return { firstName: "", lastName: "", middleName: "", suffix: "", isInitial: false };
        }

        // Define special parts
        const suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"];
        const specialPrefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"];

        // Split by spaces
        let parts = name.split(/\\s+/);
        if (parts.length === 0) {
            return { firstName: "", lastName: "", middleName: "", suffix: "", isInitial: false };
        }

        // Single word name - treat as last name
        if (parts.length === 1) {
            return { firstName: "", lastName: parts[0], middleName: "", suffix: "", isInitial: false };
        }

        // Extract any suffix
        let suffix = "";
        for (const suffixTerm of suffixes) {
            const suffixIndex = parts.findIndex(part => part === suffixTerm);
            if (suffixIndex !== -1) {
                suffix = parts[suffixIndex];
                parts.splice(suffixIndex, 1);
                break;
            }
        }

        // Check for special cases with prefixes
        for (let i = 0; i < parts.length - 1; i++) {
            if (specialPrefixes.includes(parts[i])) {
                // Found a special prefix - handle with care
                if (i === 0 && parts.length >= 2) {
                    // Format is likely "VAN BEETHOVEN" (prefix + last name)
                    const compoundLastName = parts.slice(0, 2).join(" ");

                    // If only 2 parts, it's just a compound last name
                    if (parts.length === 2) {
                        return {
                            firstName: "",
                            lastName: compoundLastName,
                            middleName: "",
                            suffix,
                            isInitial: false
                        };
                    }

                    // Format is likely "VAN BEETHOVEN LUDWIG" (prefix + last name + first name)
                    const firstName = parts[2];
                    const middleName = parts.slice(3).join(" ");
                    const isInitial = firstName.length === 1;

                    return {
                        firstName,
                        lastName: compoundLastName,
                        middleName,
                        suffix,
                        isInitial
                    };
                }
            }
        }

        // Handle standard formats
        // Common case 1: "LASTNAME FIRSTNAME" (ADC style)
        const adcFormat = {
            lastName: parts[0],
            firstName: parts.length > 1 ? parts[1] : "",
            middleName: parts.length > 2 ? parts.slice(2).join(" ") : "",
            isInitial: parts.length > 1 && parts[1].length === 1
        };

        // Common case 2: "FIRSTNAME LASTNAME" (Mazooka style)
        const mazookaFormat = {
            firstName: parts[0],
            lastName: parts.length > 1 ? parts[parts.length - 1] : "",
            middleName: parts.length > 2 ? parts.slice(1, parts.length - 1).join(" ") : "",
            isInitial: parts[0].length === 1
        };

        // Try to determine which format is more likely
        // If the first part contains a prefix like "VAN", it's likely a last name
        if (specialPrefixes.includes(parts[0])) {
            return adcFormat;
        }

        // If the last part contains a prefix, then we probably have FIRSTNAME PREFIX LASTNAME
        if (parts.length > 2 && specialPrefixes.includes(parts[parts.length - 2])) {
            const compoundLastName = parts.slice(parts.length - 2).join(" ");
            return {
                firstName: parts[0],
                lastName: compoundLastName,
                middleName: parts.length > 3 ? parts.slice(1, parts.length - 2).join(" ") : "",
                suffix,
                isInitial: parts[0].length === 1
            };
        }

        // For standard cases, default to ADC format
        return adcFormat;
    }

    // Generate variants of a last name by removing special prefixes
    function generateVariantsWithoutPrefixes(lastName) {
        if (!lastName) return [""];

        const specialPrefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"];
        const variants = [lastName];

        // Check if the last name starts with any prefix
        const parts = lastName.split(/\\s+/);
        if (parts.length >= 2 && specialPrefixes.includes(parts[0])) {
            // Add variant without the prefix
            variants.push(parts.slice(1).join(" "));
        }

        return variants;
    }

    function enhancedNameSimilarityScore(adcName, mazookaName, adcScore, mazookaScore) {
        try {
            // Parse the names into components
            const adcComponents = parseNameComponents(adcName);
            const mazookaComponents = parseNameComponents(mazookaName);

            // Rule 1: For names with special prefixes like "VAN", try matching with and without
            const adcLastNamesToTry = generateVariantsWithoutPrefixes(adcComponents.lastName);
            const mazookaLastNamesToTry = generateVariantsWithoutPrefixes(mazookaComponents.lastName);

            // Calculate Total Achievable Points (TAP)
            const adcTAP = adcScore || 3;
            const mazookaTAP = mazookaScore || 3;
            const TAP = Math.max(adcTAP, mazookaTAP);

            // Initialize scores
            let bestLastNameScore = 0;
            let bestFirstNameScore = 0;
            let bestInitialScore = 0;

            // Try all last name variant combinations
            for (const adcLastName of adcLastNamesToTry) {
                for (const mazookaLastName of mazookaLastNamesToTry) {
                    // Check for last name match
                    let lastNameScore = 0;

                    if (adcLastName && mazookaLastName) {
                        if (adcLastName.toUpperCase() === mazookaLastName.toUpperCase()) {
                            lastNameScore = 2; // Exact match
                        } else {
                            // Check for fuzzy match
                            const similarity = calculateStringSimilarity(adcLastName, mazookaLastName);
                            if (similarity >= 0.93) {
                                lastNameScore = 1.5; // Fuzzy match
                            }
                        }
                    }

                    if (lastNameScore > bestLastNameScore) {
                        bestLastNameScore = lastNameScore;
                    }
                }
            }

            // Rule 2: If no last name match, return score of 0
            if (bestLastNameScore === 0) {
                return {
                    smp: 0,
                    tap: TAP,
                    atap: adcTAP,
                    stap: mazookaTAP,
                    last_name_score: 0,
                    first_name_score: 0,
                    initial_score: 0,
                    score: 0
                };
            }

            // Check first name match - only if we have a last name match
            if (adcComponents.firstName && mazookaComponents.firstName) {
                if (adcComponents.firstName.toUpperCase() === mazookaComponents.firstName.toUpperCase()) {
                    bestFirstNameScore = 1; // Exact match
                } else {
                    // Check for fuzzy match
                    const similarity = calculateStringSimilarity(adcComponents.firstName, mazookaComponents.firstName);
                    if (similarity >= 0.93) {
                        bestFirstNameScore = 0.5; // Fuzzy match
                    }
                }
            }

            // Rule 3 & 4: Check for initial match only if we have a last name match
            // Initial must match first letter of first name
            if (bestFirstNameScore === 0 && bestLastNameScore > 0) {
                if (adcComponents.isInitial && mazookaComponents.firstName) {
                    // ADC has initial, check if it matches first letter of Mazooka first name
                    if (adcComponents.firstName.charAt(0).toUpperCase() === 
                        mazookaComponents.firstName.charAt(0).toUpperCase()) {
                        bestInitialScore = 0.5;
                    }
                } 
                else if (mazookaComponents.isInitial && adcComponents.firstName) {
                    // Mazooka has initial, check if it matches first letter of ADC first name
                    if (mazookaComponents.firstName.charAt(0).toUpperCase() === 
                        adcComponents.firstName.charAt(0).toUpperCase()) {
                        bestInitialScore = 0.5;
                    }
                }
            }

            // Calculate SMP (Sum of Matched Points)
            const SMP = bestLastNameScore + bestFirstNameScore + bestInitialScore;

            // Calculate final score
            const score = SMP / TAP;

            return {
                smp: SMP,
                tap: TAP,
                atap: adcTAP,
                stap: mazookaTAP,
                last_name_score: bestLastNameScore,
                first_name_score: bestFirstNameScore,
                initial_score: bestInitialScore,
                score: score
            };
        } catch (e) {
            // Fallback to a safe default if any errors occur
            return {
                smp: 0,
                tap: Math.max(adcScore || 3, mazookaScore || 3),
                atap: adcScore || 3,
                stap: mazookaScore || 3,
                last_name_score: 0,
                first_name_score: 0,
                initial_score: 0,
                score: 0
            };
        }
    }

    // Execute with the provided names and scores
    return enhancedNameSimilarityScore(ADC_NAME, MAZOOKA_NAME, APRA_SCORE, MAZOOKA_SCORE);
    $$
    """).collect()


# ENHANCED VERSION - Phase 2 with improved parsing
def phase2_enhanced_name_parsing(session, use_example_data=False, phase1_results=None, save_to_tables=True):
    # Phase 2: Parse names into first and last name components with enhanced approach

    print("Starting Phase 2: Enhanced name parsing with flexible format handling...")

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

        # Create the enhanced functions
        create_enhanced_parse_name_function(session)
        create_enhanced_calculate_name_score_function(session)

        adc_parsed_sql = """
        SELECT 
            a.APRA_WORK_ID,
            a.ISWC,
            a.NAME as APRA_NAME,
            a.ADC_COMPOSER_ID,
            ENHANCED_CALCULATE_NAME_SCORE_SQL(ENHANCED_PARSE_NAME_SQL(a.NAME)) as APRA_NAME_SCORE,
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
        print(f"Parsed {adc_count} ADC composer names with enhanced parser")

        # Process Mazooka names with enhanced UDFs
        print("Parsing Mazooka composer names with enhanced parser...")

        mazooka_parsed_sql = """
        SELECT 
            m.TRACK_ID,
            m.ISWC,
            m.COMPOSER as MAZOOKA_NAME,
            ENHANCED_CALCULATE_NAME_SCORE_SQL(ENHANCED_PARSE_NAME_SQL(m.COMPOSER)) as MAZOOKA_NAME_SCORE
        FROM 
            temp_mazooka_composers_phase2 m
        """

        mazooka_parsed_df = session.sql(mazooka_parsed_sql)
        mazooka_count = mazooka_parsed_df.count()
        print(f"Parsed {mazooka_count} Mazooka composer names with enhanced parser")

        # Save intermediate results to Snowflake tables if requested
        if save_to_tables:
            adc_parsed_df.write.mode("overwrite").save_as_table("PHASE2_ADC_ENHANCED_PARSED_NAMES")
            mazooka_parsed_df.write.mode("overwrite").save_as_table("PHASE2_MAZOOKA_ENHANCED_PARSED_NAMES")
            print("Phase 2 complete! Enhanced parsed name tables saved for Phase 3.")
        else:
            print("Phase 2 complete! (Tables not saved in example mode)")

        return {
            "adc_parsed_df": adc_parsed_df,
            "mazooka_parsed_df": mazooka_parsed_df
        }
    except Exception as e:
        print(f"Error in phase2_enhanced_name_parsing: {str(e)}")
        # Print the full traceback for better debugging
        import traceback
        print(traceback.format_exc())
        raise


# Phase 3 with improved matching
def phase3_enhanced_matching(session, use_example_data=False, phase2_results=None, save_to_tables=True):
    print("Starting Phase 3: Enhanced match score generation with flexible format handling...")

    try:
        # Either use the data from Phase 2 or load from Snowflake tables
        if use_example_data and phase2_results:
            print("Using example dataset from Phase 2 for Phase 3")
            adc_parsed_df = phase2_results["adc_parsed_df"]
            mazooka_parsed_df = phase2_results["mazooka_parsed_df"]
        else:
            adc_parsed_df = session.table("PHASE2_ADC_ENHANCED_PARSED_NAMES")
            mazooka_parsed_df = session.table("PHASE2_MAZOOKA_ENHANCED_PARSED_NAMES")

        print("Loaded enhanced parsed name data for matching")

        adc_count = adc_parsed_df.count()
        mazooka_count = mazooka_parsed_df.count()
        print(f"Found {adc_count} ADC records and {mazooka_count} Mazooka records")

        # Create temporary views for the dataframes with unique names for phase 3
        adc_parsed_df.create_or_replace_temp_view("temp_adc_enhanced_parsed_phase3")
        mazooka_parsed_df.create_or_replace_temp_view("temp_mazooka_enhanced_parsed_phase3")

        print("Creating enhanced name similarity function...")
        create_enhanced_similarity_function(session)

        print("Enhanced similarity UDF created successfully")

        # Filter for valid ISWCs that exist in both datasets
        print("Finding common ISWCs between datasets...")

        valid_iswcs_sql = """
        WITH adc_iswcs AS (
            SELECT DISTINCT ISWC 
            FROM temp_adc_enhanced_parsed_phase3 
            WHERE ISWC IS NOT NULL
        ),
        mazooka_iswcs AS (
            SELECT DISTINCT ISWC 
            FROM temp_mazooka_enhanced_parsed_phase3 
            WHERE ISWC IS NOT NULL
        )
        SELECT a.ISWC
        FROM adc_iswcs a
        INNER JOIN mazooka_iswcs m
        ON a.ISWC = m.ISWC
        """

        valid_iswcs = session.sql(valid_iswcs_sql)
        valid_iswcs.create_or_replace_temp_view("temp_valid_iswcs_enhanced_phase3")

        count_valid_iswcs = valid_iswcs.count()
        print(f"Found {count_valid_iswcs} ISWCs that exist in both datasets")

        # If no matching ISWCs, handle gracefully
        if count_valid_iswcs == 0:
            print("Warning: No matching ISWCs found between datasets. Creating empty result.")
            # Create an empty result dataframe with expected schema
            result_columns = [
                "APRA_NAME", "ATAP", "MAZOOKA_NAME", "STAP", "MATCH_SCORE",
                "SMP", "TAP", "WORK_ID", "TRACK_ID",
                "ISWC", "ADC_COMPOSER_ID", "YN_COMPOSERS_TRUNC", "MATCH_STATUS"  # Added MATCH_STATUS
            ]
            empty_df = session.create_dataframe([], schema=result_columns)

            # Save empty results to a Snowflake table if requested
            if save_to_tables:
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                final_table_name = f"ENHANCED_COMPOSER_NAME_MATCHING_RESULTS_{timestamp}"
                empty_df.write.mode("overwrite").save_as_table(final_table_name)
                print(f"Saved empty results to {final_table_name}")
            else:
                final_table_name = "No table created (example mode)"
                print("No matches found (no table created in example mode)")

            return empty_df, final_table_name

        # Generate potential matches with enhanced scoring approach
        print("Generating potential matches using enhanced name matching algorithm...")

        potential_matches_sql = """
        SELECT 
            a.APRA_NAME,
            a.ADC_COMPOSER_ID,
            a.APRA_NAME_SCORE as ATAP,
            m.MAZOOKA_NAME,
            m.MAZOOKA_NAME_SCORE as STAP,
            GREATEST(a.APRA_NAME_SCORE, m.MAZOOKA_NAME_SCORE) as TAP,
            ENHANCED_NAME_SIMILARITY_SCORE(
                a.APRA_NAME, 
                m.MAZOOKA_NAME,
                a.APRA_NAME_SCORE,
                m.MAZOOKA_NAME_SCORE
            ) AS NAME_SIMILARITY_OBJ,
            ENHANCED_NAME_SIMILARITY_SCORE(
                a.APRA_NAME, 
                m.MAZOOKA_NAME,
                a.APRA_NAME_SCORE,
                m.MAZOOKA_NAME_SCORE
            ):smp::FLOAT AS SMP,
            ENHANCED_NAME_SIMILARITY_SCORE(
                a.APRA_NAME, 
                m.MAZOOKA_NAME,
                a.APRA_NAME_SCORE,
                m.MAZOOKA_NAME_SCORE
            ):score::FLOAT AS MATCH_SCORE,
            a.APRA_WORK_ID AS WORK_ID,
            m.TRACK_ID,
            a.ISWC,
            a.YN_COMPOSERS_TRUNC
        FROM 
            temp_adc_enhanced_parsed_phase3 a
        JOIN 
            temp_mazooka_enhanced_parsed_phase3 m
        ON 
            a.ISWC = m.ISWC
        WHERE
            a.ISWC IN (SELECT ISWC FROM temp_valid_iswcs_enhanced_phase3)
        """

        potential_matches = session.sql(potential_matches_sql)
        potential_matches.create_or_replace_temp_view("temp_potential_matches_enhanced_phase3")

        total_potential_matches = potential_matches.count()
        print(f"Generated {total_potential_matches} total potential matches with enhanced algorithm")

        # Count only matches with score > 0
        positive_matches_sql = """
        SELECT COUNT(*) AS positive_match_count
        FROM temp_potential_matches_enhanced_phase3
        WHERE MATCH_SCORE > 0
        """
        positive_match_count = session.sql(positive_matches_sql).collect()[0]["POSITIVE_MATCH_COUNT"]
        print(f"Of these, {positive_match_count} matches have a score > 0")

        # MODIFIED: Format the final output with the specific columns requested
        # Only include rows where MATCH_SCORE > 0 and add MATCH_STATUS column
        print("Creating final output with enhanced matching results...")

        formatted_output_sql = """
        SELECT DISTINCT
            APRA_NAME, 
            ATAP, 
            MAZOOKA_NAME, 
            STAP, 
            MATCH_SCORE, 
            SMP,
            TAP,
            WORK_ID, 
            TRACK_ID, 
            ISWC, 
            ADC_COMPOSER_ID,
            YN_COMPOSERS_TRUNC,
            'match' AS MATCH_STATUS
        FROM 
            temp_potential_matches_enhanced_phase3
        WHERE 
            MATCH_SCORE >= 0.5  -- Only include matches with higher-quality scores
            AND ENHANCED_NAME_SIMILARITY_SCORE(
                APRA_NAME, 
                MAZOOKA_NAME,
                ATAP,
                STAP
            ):last_name_score > 0  -- Ensure last names match
        ORDER BY
            ISWC, WORK_ID, TRACK_ID, MATCH_SCORE DESC
        """

        result_df = session.sql(formatted_output_sql)

        # Debug final result
        result_count = result_df.count()
        print(f"Final output contains {result_count} distinct matches with score > 0")

        # Save final results to a Snowflake table if requested
        if save_to_tables:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            final_table_name = f"ENHANCED_COMPOSER_NAME_MATCHING_RESULTS_{timestamp}"
            result_df.write.mode("overwrite").save_as_table(final_table_name)
            print(f"Successfully wrote {result_count} results to final table: {final_table_name}")
        else:
            final_table_name = "No table created (example mode)"
            print(f"Example mode: {result_count} results generated (no table created)")

        print("Enhanced name matching process complete!")

        return result_df, final_table_name
    except Exception as e:
        print(f"Error in phase3_enhanced_matching: {str(e)}")
        # Print the full traceback for better debugging
        import traceback
        print(traceback.format_exc())
        raise


def cleanup_temp_tables(session, enhanced=False):
    """Delete all temporary tables created during the process"""
    try:
        # List of temporary tables to drop
        temp_tables = [
            "PHASE1_CLEANED_ADC_COMPOSERS",
            "PHASE1_CLEANED_MAZOOKA_COMPOSERS",
            "PHASE1_WORK_DATA_WITH_FLAGS"
        ]

        if enhanced:
            temp_tables.extend([
                "PHASE2_ADC_ENHANCED_PARSED_NAMES",
                "PHASE2_MAZOOKA_ENHANCED_PARSED_NAMES"
            ])
        else:
            temp_tables.extend([
                "PHASE2_ADC_PARSED_NAMES",
                "PHASE2_MAZOOKA_PARSED_NAMES"
            ])

        # Drop each table
        for table in temp_tables:
            print(f"Dropping temporary table: {table}")
            session.sql(f"DROP TABLE IF EXISTS {table}").collect()

        print("All temporary tables have been dropped successfully")
    except Exception as e:
        print(f"Error while cleaning up temporary tables: {str(e)}")
        print("Continuing execution despite cleanup errors")


def main_enhanced(session, use_example_data=False):
    """Main function that uses the enhanced name matching approach"""

    print("Initiating enhanced name matching process...")

    save_to_tables = not use_example_data

    try:
        # Load example data if requested
        example_data = None
        if use_example_data:
            print("=== USING EXAMPLE DATASET ===")
            example_data = create_example_dataset(session)

        print("=== PHASE 1: PREPROCESSING AND TRUNCATION IDENTIFICATION ===")
        phase1_results = phase1_preprocessing(session, use_example_data, example_data, save_to_tables)

        print("\n=== PHASE 2: ENHANCED NAME PARSING WITH FLEXIBLE FORMAT HANDLING ===")
        phase2_results = phase2_enhanced_name_parsing(session, use_example_data, phase1_results, save_to_tables)

        print("\n=== PHASE 3: ENHANCED MATCH SCORE GENERATION WITH FLEXIBLE FORMAT HANDLING ===")
        final_results, final_table_name = phase3_enhanced_matching(session, use_example_data, phase2_results,
                                                                   save_to_tables)

        # Clean up temporary tables
        if not use_example_data:
            print("\n=== CLEANING UP TEMPORARY TABLES ===")
            cleanup_temp_tables(session, enhanced=True)

        print("\nEnhanced name matching process completed successfully!")

        if use_example_data:
            print("\n=== EXAMPLE DATASET RESULTS ===")

            pd_results = final_results.to_pandas()
            print(pd_results.to_string(index=False))
        else:
            print(f"Final results saved to table: {final_table_name}")

        return final_results
    except Exception as e:
        print(f"Error in main_enhanced function: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise


# Execute the enhanced name matching process
final_results = main_enhanced(session)

# For testing with example data:
# final_results = main_enhanced(session, use_example_data=True)