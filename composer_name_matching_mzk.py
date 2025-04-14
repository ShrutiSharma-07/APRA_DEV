import pandas as pd
import numpy as np
import re
from fuzzywuzzy import fuzz


def clean_text(text):
    """Apply basic cleaning rules: uppercase and remove leading/trailing whitespace"""
    if pd.isna(text):
        return ""
    return str(text).upper().strip()


def split_composer_names(composer_string):
    """Split composers where multiple exist in one row (Rule 5)"""
    if pd.isna(composer_string) or composer_string == "":
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

    # Filter out unwanted names as per Rule 5b
    unwanted = ["TRAD", "TRADITIONAL", "ARR"]
    result = [c for c in result if c not in unwanted]

    return result


def parse_name(name):
    """
    Enhanced parser that handles various name formats including reversed names and initials
    """
    if pd.isna(name) or name == "":
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
    # This handles cases like "SWIFT T" where T is an initial
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
    is_special_lastname = False
    for i, part in enumerate(parts):
        if part in special_prefixes and i < len(parts) - 1:
            # Found a special prefix, assume format is "FIRST PREFIX LASTNAME" or just "PREFIX LASTNAME"
            if i == 0:  # If prefix is first word, assume no first name
                return {"first": "", "last": " ".join(parts)}
            else:  # Otherwise assume format is "FIRST PREFIX LASTNAME"
                return {"first": " ".join(parts[:i]), "last": " ".join(parts[i:])}

    # Default: standard format "FIRST LAST"
    return {"first": first_name_candidate, "last": last_name_candidate}


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


def calculate_match_score(apra_name, staging_name):
    """
    Enhanced matching that considers both name orders and handles both "FIRST LAST" and "LAST FIRST" formats
    """
    # Try standard parsing first
    apra_parsed = parse_name(apra_name)
    staging_parsed = parse_name(staging_name)

    # Try reversed parsing to handle reversed name order cases
    apra_parts = apra_name.split() if not pd.isna(apra_name) else []
    staging_parts = staging_name.split() if not pd.isna(staging_name) else []

    # For 2-part names, also try reversed interpretation
    apra_reversed = None
    staging_reversed = None

    if len(apra_parts) == 2:
        apra_reversed = {"first": apra_parts[1], "last": apra_parts[0]}

    if len(staging_parts) == 2:
        staging_reversed = {"first": staging_parts[1], "last": staging_parts[0]}

    # Calculate scores for standard and reversed interpretations
    standard_score = calculate_match_score_internal(apra_parsed, staging_parsed)

    # Try all combinations if we have reversed interpretations
    reversed_score1 = 0
    reversed_score2 = 0
    reversed_score3 = 0

    if apra_reversed and staging_parsed:
        reversed_score1 = calculate_match_score_internal(apra_reversed, staging_parsed)

    if apra_parsed and staging_reversed:
        reversed_score2 = calculate_match_score_internal(apra_parsed, staging_reversed)

    if apra_reversed and staging_reversed:
        reversed_score3 = calculate_match_score_internal(apra_reversed, staging_reversed)

    # Return the highest score from all interpretations
    return max(standard_score, reversed_score1, reversed_score2, reversed_score3)


def calculate_match_score_internal(apra_parsed, staging_parsed):
    """Internal function to calculate match score between two parsed names"""
    score = 0

    # Last name matching (2 points for exact, 1.5 for fuzzy)
    if apra_parsed["last"] and staging_parsed["last"]:
        if apra_parsed["last"] == staging_parsed["last"]:
            score += 2  # Exact last name match
        else:
            # Fuzzy last name match
            last_similarity = fuzz.ratio(apra_parsed["last"], staging_parsed["last"]) / 100
            if last_similarity >= 0.93:
                score += 1.5

    # First name matching (1 point for exact, 0.5 for fuzzy or initial match)
    if apra_parsed["first"] and staging_parsed["first"]:
        if apra_parsed["first"] == staging_parsed["first"]:
            score += 1  # Exact first name match
        else:
            # Check for initial match - first letter matches
            apra_initial = apra_parsed["first"][0] if apra_parsed["first"] else ""
            staging_initial = staging_parsed["first"][0] if staging_parsed["first"] else ""

            # Only match if initials are exactly the same or if one name doesn't have an initial
            if len(apra_parsed["first"]) == 1 and len(staging_parsed["first"]) == 1:
                # If both are initials, they must match exactly
                if apra_initial == staging_initial:
                    score += 0.5
                else:
                    # Different initials should result in no match
                    return 0
            elif len(apra_parsed["first"]) == 1 and apra_initial == staging_initial:
                score += 0.5  # Initial matches first letter of full name
            elif len(staging_parsed["first"]) == 1 and staging_initial == apra_initial:
                score += 0.5  # Initial matches first letter of full name
            # Otherwise check for fuzzy first name match
            else:
                first_similarity = fuzz.ratio(apra_parsed["first"], staging_parsed["first"]) / 100
                if first_similarity >= 0.93:
                    score += 0.5

    return score

def perform_matching(apra_names, staging_names):
    """Perform matching between APRA and staging names"""
    apra_points = [(name, calculate_name_points(name)) for name in apra_names]
    staging_points = [(name, calculate_name_points(name)) for name in staging_names]

    atap = sum(points for _, points in apra_points)
    stap = sum(points for _, points in staging_points)
    tap = max(atap, stap)

    matches = []
    used_apra_indices = set()
    used_staging_indices = set()
    smp = 0

    # First pass: Find best matches in descending order of match score
    all_possible_matches = []

    for staging_idx, (staging_name, _) in enumerate(staging_points):
        for apra_idx, (apra_name, _) in enumerate(apra_points):
            score = calculate_match_score(apra_name, staging_name)
            if score > 0:
                all_possible_matches.append({
                    "staging_idx": staging_idx,
                    "apra_idx": apra_idx,
                    "score": score
                })

    # Sort by score in descending order
    all_possible_matches.sort(key=lambda x: x["score"], reverse=True)

    # Make matches greedily starting from highest scores
    for match in all_possible_matches:
        staging_idx = match["staging_idx"]
        apra_idx = match["apra_idx"]
        score = match["score"]

        if staging_idx not in used_staging_indices and apra_idx not in used_apra_indices:
            matches.append(match)
            used_apra_indices.add(apra_idx)
            used_staging_indices.add(staging_idx)
            smp += score

    match_percent = int(round((smp / tap) * 100)) if tap > 0 else 0

    return {
        "apra_points": apra_points,
        "staging_points": staging_points,
        "atap": atap,
        "stap": stap,
        "tap": tap,
        "smp": smp,
        "match_percent": match_percent,
        "matches": matches
    }


def format_output_table(result, example_id):
    """Format the matching result as a detailed table"""
    apra_names = [name for name, _ in result["apra_points"]]
    staging_names = [name for name, _ in result["staging_points"]]

    # Calculate the maximum length needed for all columns
    max_length = max(
        len(apra_names) + 3,  # APRA names + total count + ATAP + empty line
        len(staging_names) + 3  # Staging names + total count + STAP + empty line
    )

    # Initialize the table
    table = {
        "Example": [example_id] * max_length,
        "APRA name": [""] * max_length,
        "Matching with": [""] * max_length,
        "Staging name": [""] * max_length,
        "Staging matched points": [""] * max_length,
        "SDCtracks total match percent": [""] * max_length
    }

    # Format APRA names with points
    for i, (name, points) in enumerate(result["apra_points"]):
        table["APRA name"][i] = f"{i + 1}. {name} ({points})"

    # Add APRA totals
    next_idx = len(apra_names)
    table["APRA name"][next_idx] = "total count = " + str(len(apra_names))
    table["APRA name"][next_idx + 1] = f"ATAP = {result['atap']} points"

    # Format staging names with points
    for i, (name, points) in enumerate(result["staging_points"]):
        table["Staging name"][i] = f"{i + 1}. {name} ({points})"

    # Add staging totals
    staging_next_idx = len(staging_names)
    table["Staging name"][staging_next_idx] = "total count = " + str(len(staging_names))
    table["Staging name"][staging_next_idx + 1] = f"STAP = {result['stap']}"

    # Create mapping from staging index to matching apra index and score
    staging_to_apra = {}
    for match in result["matches"]:
        staging_idx = match["staging_idx"]
        apra_idx = match["apra_idx"]
        score = match["score"]
        staging_to_apra[staging_idx] = (apra_idx, score)

    # Create mapping from apra index to matching staging index
    apra_to_staging = {}
    for match in result["matches"]:
        staging_idx = match["staging_idx"]
        apra_idx = match["apra_idx"]
        apra_to_staging[apra_idx] = staging_idx

    # Fill in the Matching with column
    for i in range(len(apra_names)):
        if i in apra_to_staging:
            table["Matching with"][i] = f"match (Stg {apra_to_staging[i] + 1})"
        else:
            table["Matching with"][i] = "no match"

    # Fill in the Staging matched points column with the correct scores
    for staging_idx, (apra_idx, score) in staging_to_apra.items():
        table["Staging matched points"][staging_idx] = score

    # Add SMP and TAP information
    table["Staging matched points"][max_length - 1] = f"SMP = {result['smp']} points"
    table["SDCtracks total match percent"][max_length - 2] = f"TAP = {result['tap']}"
    table["SDCtracks total match percent"][
        max_length - 1] = f"{result['smp']}/{result['tap']} = **{result['match_percent']}**%"

    return pd.DataFrame(table)


def main():
    # Process example 1 from the instructions
    example1_apra = [
        "SMITH JOHN",
        "JOHNSON JACK",
        "SMITH K",
        "JACKSON",
        "SWIFT TAYLOR"
    ]

    example1_staging = [
        "T SWIFT",
        "JACKSON MICHAEL",
        "SMITH P",
        "SMITH",
        "JOHNSON J",
        "KEANE",
        "BRUNO MARS"
    ]

    # Process example 2 from the instructions
    example2_apra = [
        "SMITH",
        "JOHNSON",
        "SMITHK",
        "JACKSON",
        "SWIFT",
        "KEANE",
        "MARS"
    ]

    example2_staging = [
        "T SWIFT",
        "JACKSON MICHAEL",
        "SMITH P",
        "SMITH",
        "JOHNSON J"
    ]

    # Process example 3 from the instructions
    example3_apra = [
        "SMITH P",
        "JOHNSON J",
        "SMITHK",
        "JACKSON M",
        "SWIFT TAYLOR",
        "KEANE A",
        "MARS BRUNO"
    ]

    example3_staging = [
        "TAYLOR SWIFT",
        "JACKSON MICHAEL",
        "SMITH P",
        "SMITH K",
        "JOHNSON J",
        "KEANE",
        "MARS BRUNO"
    ]

    # Match the examples
    example1_result = perform_matching(example1_apra, example1_staging)
    example2_result = perform_matching(example2_apra, example2_staging)
    example3_result = perform_matching(example3_apra, example3_staging)

    # Format as tables
    example1_table = format_output_table(example1_result, 1)
    example2_table = format_output_table(example2_result, 2)
    example3_table = format_output_table(example3_result, 3)

    # Combine all examples
    all_examples = pd.concat([example1_table, example2_table, example3_table], ignore_index=True)

    print("Example 1:")
    print(example1_table)
    print("\nExample 2:")
    print(example2_table)
    print("\nExample 3:")
    print(example3_table)

    # If using real CSV data files, uncomment and adjust the paths below
    try:
        adc_composers = pd.read_csv(r"C:\Users\Shruti Sharma\Desktop\ADC_Composers.csv", dtype=str)
        muzooka_composers = pd.read_csv(r"C:\Users\Shruti Sharma\Desktop\APRA Data Cleanup\muzooka_composers.csv",
                                        dtype=str)

        adc_data = pd.DataFrame(adc_composers)
        mazooka_data = pd.DataFrame(muzooka_composers)

        # Clean and process the data
        # Apply Rule 1: Upper case all characters
        for col in adc_data.columns:
            if adc_data[col].dtype == object:
                adc_data[col] = adc_data[col].apply(clean_text)

        for col in mazooka_data.columns:
            if mazooka_data[col].dtype == object:
                mazooka_data[col] = mazooka_data[col].apply(clean_text)

        # Create expanded datasets with one composer per row (Rule 5)
        # For ADC data
        expanded_adc = []
        for _, row in adc_data.iterrows():
            composers = split_composer_names(row['name'])
            if not composers:  # If no composers after splitting, use the original
                composers = [row['name']]

            for composer in composers:
                new_row = row.copy()
                new_row['name'] = composer
                expanded_adc.append(new_row)

        expanded_adc_df = pd.DataFrame(expanded_adc)

        # For Mazooka data
        expanded_mazooka = []
        for _, row in mazooka_data.iterrows():
            composers = split_composer_names(row['Composer'])
            if not composers:  # If no composers after splitting, use the original
                composers = [row['Composer']]

            for composer in composers:
                new_row = row.copy()
                new_row['Composer'] = composer
                expanded_mazooka.append(new_row)

        expanded_mazooka_df = pd.DataFrame(expanded_mazooka)

        # Process each work-track combination
        real_data_results = []

        # Group ADC composers by work_id
        adc_grouped = expanded_adc_df.groupby('apra_work_id')

        # For each ADC work_id
        for work_id, adc_group in adc_grouped:
            apra_composers = adc_group['name'].tolist()

            # Group Mazooka composers by track_id
            mazooka_grouped = expanded_mazooka_df.groupby('Muzooka Track ID')

            # For each Mazooka track_id
            for track_id, mazooka_group in mazooka_grouped:
                mazooka_composers = mazooka_group['Composer'].tolist()

                # Perform matching
                result = perform_matching(apra_composers, mazooka_composers)

                # Format as table
                table = format_output_table(result, f"Work {work_id} - Track {track_id}")

                real_data_results.append(table)

        # Combine all real data results
        if real_data_results:
            real_data_table = pd.concat(real_data_results, ignore_index=True)

            # Save all results
            all_examples.to_csv("example_matching_results.csv", index=False)
            real_data_table.to_csv("real_data_matching_results.csv", index=False)

            print("Example matching results saved to example_matching_results.csv")
            print("Real data matching results saved to real_data_matching_results.csv")
        else:
            all_examples.to_csv("matching_results.csv", index=False)
            print("Example matching results saved to matching_results.csv")
    except Exception as e:
        print(f"Error processing CSV files: {e}")
        # Just save the example results
        all_examples.to_csv("matching_results.csv", index=False)
        print("Example matching results saved to matching_results.csv")


if __name__ == "__main__":
    main()