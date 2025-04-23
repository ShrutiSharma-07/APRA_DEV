import re
import pandas as pd
import snowflake.snowpark.functions as F
from snowflake.snowpark.functions import col, lit, regexp_replace, when, udf
from snowflake.snowpark.types import StringType, IntegerType, FloatType, StructType, StructField, VariantType


def clean_text(text):
    """Apply basic cleaning rules: uppercase and remove leading/trailing whitespace"""
    if text is None:
        return ""
    return str(text).upper().strip()


# UDF versions for use with Snowpark DataFrames
@udf(return_type=VariantType())
def split_composer_names(composer_string):
    """Split composers where multiple exist in one row"""
    if composer_string is None or composer_string == "":
        return []

    # Convert to uppercase and strip
    composer_string = str(composer_string).upper().strip()

    # Split by "/" as specified in Rule 5a
    composers = composer_string.split("/")
    composers = [c.strip() for c in composers]

    # Split by ";" for the provided example data
    result = []
    for comp in composers:
        if ";" in comp:
            result.extend([c.strip() for c in comp.split(";")])
        else:
            result.append(comp)

    # Filter out unwanted names
    unwanted = ["TRAD", "TRADITIONAL", "ARR"]
    result = [c for c in result if c not in unwanted]

    return result


@udf(return_type=VariantType())
def parse_name(name):
    """Parse names into first and last name components"""
    if name is None or name == "":
        return {"first": "", "last": ""}

    # Special suffixes that should be kept with last name
    suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"]

    # Special prefixes for multi-word last names
    special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"]

    # Clean and split the name
    name = str(name).strip()
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


@udf(return_type=FloatType())
def calculate_name_points(name):
    """Calculate the maximum points for a name"""
    parsed = parse_name(name)
    points = 0

    # Last name points
    if parsed["last"]:
        points += 2  # Maximum possible for last name

    # First name points
    if parsed["first"]:
        if len(parsed["first"]) == 1:  # Initial
            points += 0.5  # Maximum possible for initial
        else:
            points += 1  # Maximum possible for full first name

    return points


# Regular Python function versions for pandas operations
def split_composer_names_pandas(composer_string):
    """Split composers where multiple exist in one row"""
    if composer_string is None or pd.isna(composer_string) or composer_string == "":
        return []

    # Convert to uppercase and strip
    composer_string = str(composer_string).upper().strip()

    # Split by "/" as specified in Rule 5a
    composers = composer_string.split("/")
    composers = [c.strip() for c in composers]

    # Split by ";" for the provided example data
    result = []
    for comp in composers:
        if ";" in comp:
            result.extend([c.strip() for c in comp.split(";")])
        else:
            result.append(comp)

    # Filter out unwanted names
    unwanted = ["TRAD", "TRADITIONAL", "ARR"]
    result = [c for c in result if c not in unwanted]

    return result


def parse_name_pandas(name):
    """Parse names into first and last name components"""
    if name is None or pd.isna(name) or name == "":
        return {"first": "", "last": ""}

    # Special suffixes that should be kept with last name
    suffixes = ["SENIOR", "SNR", "SR", "JUNIOR", "JNR", "JR"]

    # Special prefixes for multi-word last names
    special_prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"]

    # Clean and split the name
    name = str(name).strip()
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


def calculate_name_points_pandas(name):
    """Calculate the maximum points for a name"""
    parsed = parse_name_pandas(name)
    points = 0

    # Last name points
    if parsed["last"]:
        points += 2  # Maximum possible for last name

    # First name points
    if parsed["first"]:
        if len(parsed["first"]) == 1:  # Initial
            points += 0.5  # Maximum possible for initial
        else:
            points += 1  # Maximum possible for full first name

    return points


def calculate_match_score_internal_pandas(apra_parsed, staging_parsed):
    """Internal function to calculate match score"""
    score = 0

    # Last name matching (2 points for exact, 1.5 for similar)
    if apra_parsed["last"] and staging_parsed["last"]:
        if apra_parsed["last"] == staging_parsed["last"]:
            score += 2  # Exact last name match
        else:
            # Use simplified similarity check since fuzzywuzzy isn't available in Snowpark
            # Count common characters
            common_chars = set(apra_parsed["last"]) & set(staging_parsed["last"])
            similarity = len(common_chars) / max(len(set(apra_parsed["last"])), len(set(staging_parsed["last"])))

            if similarity >= 0.9:
                score += 1.5

    # First name matching (1 point for exact, 0.5 for initial match)
    if apra_parsed["first"] and staging_parsed["first"]:
        if apra_parsed["first"] == staging_parsed["first"]:
            score += 1  # Exact first name match
        else:
            # Check for initial match
            apra_initial = apra_parsed["first"][0] if apra_parsed["first"] else ""
            staging_initial = staging_parsed["first"][0] if staging_parsed["first"] else ""

            if len(apra_parsed["first"]) == 1 and len(staging_parsed["first"]) == 1:
                if apra_initial == staging_initial:
                    score += 0.5
                else:
                    return 0  # Different initials
            elif len(apra_parsed["first"]) == 1 and apra_initial == staging_initial:
                score += 0.5
            elif len(staging_parsed["first"]) == 1 and staging_initial == apra_initial:
                score += 0.5
            else:
                # Simplified similarity check
                common_chars = set(apra_parsed["first"]) & set(staging_parsed["first"])
                similarity = len(common_chars) / max(len(set(apra_parsed["first"])), len(set(staging_parsed["first"])))

                if similarity >= 0.9:
                    score += 0.5

    return score


def calculate_match_score_pandas(apra_name, staging_name):
    """Calculate match score between two names"""
    if pd.isna(apra_name) or pd.isna(staging_name):
        return 0

    # Parse names
    apra_parsed = parse_name_pandas(apra_name)
    staging_parsed = parse_name_pandas(staging_name)

    # Try reversed parsing for 2-part names
    apra_parts = apra_name.split() if not pd.isna(apra_name) else []
    staging_parts = staging_name.split() if not pd.isna(staging_name) else []

    apra_reversed = None
    staging_reversed = None

    if len(apra_parts) == 2:
        apra_reversed = {"first": apra_parts[1], "last": apra_parts[0]}

    if len(staging_parts) == 2:
        staging_reversed = {"first": staging_parts[1], "last": staging_parts[0]}

    # Calculate standard score
    standard_score = calculate_match_score_internal_pandas(apra_parsed, staging_parsed)

    # Try all combinations if we have reversed interpretations
    reversed_score1 = 0
    reversed_score2 = 0
    reversed_score3 = 0

    if apra_reversed and staging_parsed:
        reversed_score1 = calculate_match_score_internal_pandas(apra_reversed, staging_parsed)

    if apra_parsed and staging_reversed:
        reversed_score2 = calculate_match_score_internal_pandas(apra_parsed, staging_reversed)

    if apra_reversed and staging_reversed:
        reversed_score3 = calculate_match_score_internal_pandas(apra_reversed, staging_reversed)

    # Return highest score
    return max(standard_score, reversed_score1, reversed_score2, reversed_score3)


def main(session):
    """Main function to process the name matching logic in Snowpark"""
    print("Starting name matching process...")

    # Load the ADC composers and Mazooka composers tables
    adc_composers = session.table("EDW_APPS.MATCHING.ADC_COMPOSERS_MATCHED_ISWC_VW")
    mazooka_composers = session.table("EDW_APPS.MATCHING.MAZOOKA_COMPOSERS_MATCHED_ISWC_VW")

    print("Tables loaded successfully")

    # Print sample data and schema for verification
    print("ADC Composers schema:")
    adc_composers.printSchema()
    print("\nMazooka Composers schema:")
    mazooka_composers.printSchema()

    # Apply Rule 1: Convert all text columns to uppercase
    adc_composers = adc_composers.select([
        when(col(c).is_not_null(), F.upper(F.trim(col(c)))).otherwise(None).alias(c)
        if adc_composers.schema[c].datatype == StringType() else col(c)
        for c in adc_composers.columns
    ])

    mazooka_composers = mazooka_composers.select([
        when(col(c).is_not_null(), F.upper(F.trim(col(c)))).otherwise(None).alias(c)
        if mazooka_composers.schema[c].datatype == StringType() else col(c)
        for c in mazooka_composers.columns
    ])

    # The expanded data would be better handled in pandas for complex operations
    # Convert to pandas, then process and convert back
    print("Converting to pandas for detailed processing...")
    adc_df = adc_composers.toPandas()
    mazooka_df = mazooka_composers.toPandas()

    # Create expanded datasets with one composer per row
    print("Expanding composer names...")

    # For ADC data
    expanded_adc = []
    for _, row in adc_df.iterrows():
        composers = split_composer_names_pandas(row['NAME'])
        if not composers:  # If no composers after splitting, use the original
            composers = [row['NAME']]

        for composer in composers:
            new_row = row.copy()
            new_row['NAME'] = composer
            expanded_adc.append(new_row)

    expanded_adc_df = pd.DataFrame(expanded_adc)

    # For Mazooka data
    expanded_mazooka = []
    for _, row in mazooka_df.iterrows():
        composers = split_composer_names_pandas(row['COMPOSER'])  # Use pandas version here
        if not composers:  # If no composers after splitting, use the original
            composers = [row['COMPOSER']]

        for composer in composers:
            new_row = row.copy()
            new_row['COMPOSER'] = composer
            expanded_mazooka.append(new_row)

    expanded_mazooka_df = pd.DataFrame(expanded_mazooka)

    print(f"Expanded ADC data to {len(expanded_adc_df)} rows")
    print(f"Expanded Mazooka data to {len(expanded_mazooka_df)} rows")

    # Perform matching between APRA and Mazooka composers
    print("Performing name matching...")
    results = []

    # Group ADC composers by work_id and ISWC
    adc_grouped = expanded_adc_df.groupby(['APRA_WORK_ID', 'ISWC'])

    # Process each work-ISWC combination
    for (work_id, work_iswc), adc_group in adc_grouped:
        # Skip if ISWC is NaN
        if pd.isna(work_iswc):
            continue

        # Find all matching Mazooka composers with the same ISWC
        matching_mazooka = expanded_mazooka_df[expanded_mazooka_df['ISWC'] == work_iswc]

        if len(matching_mazooka) > 0:
            # Group by track ID
            mazooka_grouped = matching_mazooka.groupby('TRACK_ID')

            for track_id, mazooka_group in mazooka_grouped:
                # Get composer names
                apra_names = adc_group['NAME'].tolist()
                mazooka_names = mazooka_group['COMPOSER'].tolist()

                # Calculate points for each name
                apra_points = [(name, calculate_name_points_pandas(name)) for name in apra_names]
                mazooka_points = [(name, calculate_name_points_pandas(name)) for name in mazooka_names]

                # Calculate total available points
                atap = sum(points for _, points in apra_points)
                stap = sum(points for _, points in mazooka_points)
                tap = max(atap, stap)

                # Find matches
                matches = []
                used_apra_indices = set()
                used_mazooka_indices = set()
                smp = 0

                # Find all possible matches
                all_possible_matches = []

                for mazooka_idx, (mazooka_name, _) in enumerate(mazooka_points):
                    for apra_idx, (apra_name, _) in enumerate(apra_points):
                        score = calculate_match_score_pandas(apra_name, mazooka_name)
                        if score > 0:
                            all_possible_matches.append({
                                "mazooka_idx": mazooka_idx,
                                "apra_idx": apra_idx,
                                "score": score
                            })

                # Sort by score descending
                all_possible_matches.sort(key=lambda x: x["score"], reverse=True)

                # Make matches greedily
                for match in all_possible_matches:
                    mazooka_idx = match["mazooka_idx"]
                    apra_idx = match["apra_idx"]
                    score = match["score"]

                    if mazooka_idx not in used_mazooka_indices and apra_idx not in used_apra_indices:
                        matches.append(match)
                        used_apra_indices.add(apra_idx)
                        used_mazooka_indices.add(mazooka_idx)
                        smp += score

                # Calculate match percentage
                match_percent = int(round((smp / tap) * 100)) if tap > 0 else 0

                # Format results
                for i, (name, points) in enumerate(apra_points):
                    if not name.strip():
                        continue

                    row = {
                        "APRA_NAME": name,
                        "APRA_NAME_SCORE": points,
                        "MATCH_STATUS": "no match",
                        "MAZOOKA_NAME": "",
                        "MAZOOKA_NAME_SCORE": "",
                        "NAME_MATCHED_SCORE": "",
                        "WORK_ID": work_id,
                        "TRACK_ID": track_id,
                        "ISWC": work_iswc,
                        "MATCH_PERCENT": match_percent
                    }

                    # Add matching info if this name has a match
                    for match in matches:
                        if match["apra_idx"] == i:
                            mazooka_idx = match["mazooka_idx"]
                            score = match["score"]
                            mazooka_name, mazooka_score = mazooka_points[mazooka_idx]

                            row["MATCH_STATUS"] = "match"
                            row["MAZOOKA_NAME"] = mazooka_name
                            row["MAZOOKA_NAME_SCORE"] = mazooka_score
                            row["NAME_MATCHED_SCORE"] = score
                            break

                    results.append(row)

    # Create DataFrame from results
    print(f"Creating final results with {len(results)} rows")
    result_df = pd.DataFrame(results)

    # Remove duplicates, prioritizing matches
    result_df['has_match'] = result_df['MATCH_STATUS'] == 'match'
    result_df = result_df.sort_values('has_match', ascending=False)
    result_df = result_df.drop_duplicates(subset=['APRA_NAME', 'WORK_ID'], keep='first')
    result_df = result_df.drop(columns=['has_match'])

    # Add row number
    result_df.insert(0, 'ROW_NUM', range(1, len(result_df) + 1))

    # Convert back to Snowpark DataFrame
    print("Converting results back to Snowpark DataFrame")
    result_snowpark_df = session.create_dataframe(result_df)

    # Write results to table
    print("Writing results to table")
    result_snowpark_df.write.mode("overwrite").save_as_table("EDW_APPS.MATCHING.COMPOSER_NAME_MATCHING_RESULTS")

    # Create view
    print("Creating view")
    session.sql(
        "CREATE OR REPLACE VIEW EDW_APPS.MATCHING.COMPOSER_NAME_MATCHING_RESULTS_VW AS SELECT * FROM EDW_APPS.MATCHING.COMPOSER_NAME_MATCHING_RESULTS").collect()

    print("Name matching process complete!")
    return result_snowpark_df


# Execute the main function
result_df = main(session)

# Display results
result_df.limit(10).show()
