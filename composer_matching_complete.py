# Import python packages
import pandas as pd
import re
import os
import time
from memory_profiler import profile
import logging
import datetime
import matplotlib.pyplot as plt
import numpy as np

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

# Define paths for data and output
DATA_DIR = "data"
OUTPUT_DIR = "output"

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global dictionary to store memory usage data for final summary
memory_usage_data = {
    "Phase 1": [],
    "Phase 2": [],
    "Phase 3": [],
}
current_phase = None


# Memory profiling wrapper that stores data for summary
def memory_profiler_wrapper(func):
    def wrapper(*args, **kwargs):
        global current_phase
        phase_name = None

        if func.__name__ == "phase1_preprocessing":
            phase_name = "Phase 1"
        elif func.__name__ == "phase2_name_parsing":
            phase_name = "Phase 2"
        elif func.__name__ == "phase3_matching":
            phase_name = "Phase 3"

        if phase_name:
            current_phase = phase_name
            start_mem = memory_usage_now()
            logger.info(f"Starting {phase_name} with baseline memory usage: {start_mem:.2f} MiB")

        result = func(*args, **kwargs)

        if phase_name:
            end_mem = memory_usage_now()
            peak_mem = max(memory_usage_data[phase_name]) if memory_usage_data[phase_name] else end_mem
            logger.info(f"Completed {phase_name}")
            logger.info(f"Memory Usage Summary for {phase_name}:")
            logger.info(f"  - Start Memory: {start_mem:.2f} MiB")
            logger.info(f"  - End Memory: {end_mem:.2f} MiB")
            logger.info(f"  - Peak Memory: {peak_mem:.2f} MiB")
            logger.info(f"  - Memory Change: {end_mem - start_mem:.2f} MiB")
            current_phase = None

        return result

    return wrapper


# Helper function to get current memory usage
def memory_usage_now():
    import psutil
    import os
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # Convert to MiB


# Memory tracker function to be called periodically
def track_memory_usage(message=None):
    global current_phase
    if current_phase:
        mem = memory_usage_now()
        memory_usage_data[current_phase].append(mem)
    if message:
        print(message)


# PHASE 1
@memory_profiler_wrapper
def clean_text(text):
    """Apply basic cleaning rules: uppercase and remove leading/trailing whitespace"""
    #track_memory_usage()
    if text is None or pd.isna(text):
        return ""
    return str(text).upper().strip()


#@profile
def split_composer_names_pandas(composer_string):
    """Split composers where multiple exist in one row"""
    #track_memory_usage()
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


#@memory_profiler_wrapper
def phase1_preprocessing():
    """Phase 1: Preprocessing and identifying truncated composers"""
    logger.info("Starting Phase 1: Preprocessing and truncation identification...")

    try:
        # Track memory at the start
        track_memory_usage("phase1 prep")

        # Load data from CSV files
        adc_composers = pd.read_csv(f"/Users/shruti/PycharmProjects/APRA_DEV/Data/ADC.csv")
        track_memory_usage()

        mazooka_composers = pd.read_csv(f"/Users/shruti/PycharmProjects/APRA_DEV/Data/MZK.csv")
        track_memory_usage()

        adc_works = pd.read_csv(f"/Users/shruti/PycharmProjects/APRA_DEV/Data/WRK.csv")
        track_memory_usage()

        # Get row counts for initial data
        adc_count = len(adc_composers)
        mazooka_count = len(mazooka_composers)
        logger.info(f"Loaded {adc_count} ADC composer rows and {mazooka_count} Mazooka composer rows")

        # Apply Rule 1: Convert all text columns to uppercase and trim
        for column in adc_composers.select_dtypes(include=['object']).columns:
            adc_composers[column] = adc_composers[column].apply(clean_text)
            #track_memory_usage()

        for column in mazooka_composers.select_dtypes(include=['object']).columns:
            mazooka_composers[column] = mazooka_composers[column].apply(clean_text)
            #track_memory_usage()

        # Create expanded datasets with one composer per row
        logger.info("Expanding composer names...")

        # For ADC data
        expanded_adc = []
        for idx, row in enumerate(adc_composers.iterrows()):
            _, row_data = row
            composers = split_composer_names_pandas(row_data['NAME'])
            if not composers:  # If no composers after splitting, use the original
                composers = [row_data['NAME']]

            for composer in composers:
                new_row = row_data.copy()
                new_row['NAME'] = composer
                expanded_adc.append(new_row)

            # Status update every 150000 rows
            if (idx + 1) % 150000 == 0:
                logger.info(f"Processed {idx + 1}/{len(adc_composers)} ADC rows")
                #track_memory_usage()

        expanded_adc_df = pd.DataFrame(expanded_adc)
        track_memory_usage()

        # For Mazooka data
        expanded_mazooka = []
        for idx, row in enumerate(mazooka_composers.iterrows()):
            _, row_data = row
            composers = split_composer_names_pandas(row_data['COMPOSER'])
            if not composers:  # If no composers after splitting, use the original
                composers = [row_data['COMPOSER']]

            for composer in composers:
                new_row = row_data.copy()
                new_row['COMPOSER'] = composer
                expanded_mazooka.append(new_row)

            # Status update every 150000 rows
            if (idx + 1) % 150000 == 0:
                logger.info(f"Processed {idx + 1}/{len(mazooka_composers)} Mazooka rows")
                #track_memory_usage()

        expanded_mazooka_df = pd.DataFrame(expanded_mazooka)
        track_memory_usage()

        logger.info(f"Expanded ADC data to {len(expanded_adc_df)} rows")
        logger.info(f"Expanded Mazooka data to {len(expanded_mazooka_df)} rows")

        # Count composers per work and per track
        adc_composer_count = expanded_adc_df.groupby('APRA_WORK_ID').size().reset_index(name='ADC_COMPOSERS_COUNT')
        #track_memory_usage()

        mazooka_composer_count = expanded_mazooka_df.groupby(['TRACK_ID', 'ISWC']).size().reset_index(
            name='MAZOOKA_COMPOSERS_COUNT')
        #track_memory_usage()

        # Merge work data with composer counts and add yn_perf_ownership from ADC_WORKS
        work_data = adc_works.merge(adc_composer_count, on='APRA_WORK_ID', how='left')
        #track_memory_usage()

        # First, we need to get the max MAZOOKA_COMPOSERS_COUNT for each ISWC
        mazooka_max_count = mazooka_composer_count.groupby('ISWC')['MAZOOKA_COMPOSERS_COUNT'].max().reset_index()
        #track_memory_usage()

        # Merge with work_data
        work_data = work_data.merge(mazooka_max_count, on='ISWC', how='left')
        #track_memory_usage()

        # Fill NaN values
        work_data['ADC_COMPOSERS_COUNT'] = work_data['ADC_COMPOSERS_COUNT'].fillna(0)
        work_data['MAZOOKA_COMPOSERS_COUNT'] = work_data['MAZOOKA_COMPOSERS_COUNT'].fillna(0)

        # Get composer_names (assuming it's in the COMPOSERS column, adjust as needed)
        if 'COMPOSERS' in work_data.columns:
            work_data['COMPOSER_NAME_LENGTH'] = work_data['COMPOSERS'].astype(str).str.len()
        else:
            # If COMPOSERS isn't available, we need to get it from another source
            # For now, just set a default value
            work_data['COMPOSER_NAME_LENGTH'] = 0

        # Apply the truncation rule
        work_data['YN_COMPOSERS_TRUNC'] = 'N'

        # Set to 'Y' when the criteria are met
        mask = ((work_data['YN_PERF_OWNERSHIP'] == 'N') &
                (work_data['COMPOSER_NAME_LENGTH'] >= 39) &
                (work_data['ADC_COMPOSERS_COUNT'] < work_data['MAZOOKA_COMPOSERS_COUNT']))

        work_data.loc[mask, 'YN_COMPOSERS_TRUNC'] = 'Y'
        #track_memory_usage()

        # Save intermediate tables to CSV
        expanded_adc_df.to_csv(f"{OUTPUT_DIR}/phase1_cleaned_adc_composers.csv", index=False)
        expanded_mazooka_df.to_csv(f"{OUTPUT_DIR}/phase1_cleaned_mazooka_composers.csv", index=False)
        work_data.to_csv(f"{OUTPUT_DIR}/phase1_work_data_with_flags.csv", index=False)
        track_memory_usage()

        logger.info("Phase 1 complete! Intermediate files created for Phase 2.")

        return {
            "cleaned_adc_composers": expanded_adc_df,
            "cleaned_mazooka_composers": expanded_mazooka_df,
            "work_data_with_flags": work_data
        }
    except Exception as e:
        logger.error(f"Error in phase1_preprocessing: {str(e)}", exc_info=True)
        raise


# PHASE 2
#@profile
def parse_name_pandas(name):
    """Parse names into first and last name components - pandas version"""
    track_memory_usage()
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


#@profile
def calculate_name_points_pandas(name):
    """Calculate the maximum points for a name - pandas version"""
    track_memory_usage()
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


#@memory_profiler_wrapper
def phase2_name_parsing():
    """Phase 2: Parse names and generate scores"""
    logger.info("Starting Phase 2: Name parsing and score generation...")

    try:
        # Track memory at the start
        track_memory_usage()

        # Load intermediate files from Phase 1
        cleaned_adc_composers = pd.read_csv(f"{OUTPUT_DIR}/phase1_cleaned_adc_composers.csv")
        #track_memory_usage()

        cleaned_mazooka_composers = pd.read_csv(f"{OUTPUT_DIR}/phase1_cleaned_mazooka_composers.csv")
        #track_memory_usage()

        work_data_with_flags = pd.read_csv(f"{OUTPUT_DIR}/phase1_work_data_with_flags.csv")
        #track_memory_usage()

        logger.info("Loaded intermediate files from Phase 1")

        # Process ADC composer names
        logger.info("Processing ADC names...")
        adc_parsed_names = []
        for idx, row in enumerate(cleaned_adc_composers.iterrows()):
            _, row_data = row
            name = row_data['NAME']
            if pd.isna(name) or name == "":
                continue

            parsed = parse_name_pandas(name)
            points = calculate_name_points_pandas(name)

            adc_parsed_names.append({
                'APRA_WORK_ID': row_data['APRA_WORK_ID'],
                'ISWC': row_data['ISWC'],
                'APRA_NAME': name,
                'APRA_FIRST_NAME': parsed['first'],
                'APRA_LAST_NAME': parsed['last'],
                'APRA_NAME_SCORE': points
            })

            # Status update
            if (idx + 1) % 150000 == 0:
                logger.info(f"Processed {idx + 1}/{len(cleaned_adc_composers)} ADC names")
                track_memory_usage()

        adc_parsed_df = pd.DataFrame(adc_parsed_names)
        track_memory_usage()
        logger.info(f"Parsed {len(adc_parsed_df)} ADC names")

        # Process Mazooka composer names
        logger.info("Processing Mazooka names...")
        mazooka_parsed_names = []
        for idx, row in enumerate(cleaned_mazooka_composers.iterrows()):
            _, row_data = row
            name = row_data['COMPOSER']
            if pd.isna(name) or name == "":
                continue

            parsed = parse_name_pandas(name)
            points = calculate_name_points_pandas(name)

            mazooka_parsed_names.append({
                'TRACK_ID': row_data['TRACK_ID'],
                'ISWC': row_data['ISWC'],
                'MAZOOKA_NAME': name,
                'MAZOOKA_FIRST_NAME': parsed['first'],
                'MAZOOKA_LAST_NAME': parsed['last'],
                'MAZOOKA_NAME_SCORE': points
            })

            # Status update
            if (idx + 1) % 150000 == 0:
                logger.info(f"Processed {idx + 1}/{len(cleaned_mazooka_composers)} Mazooka names")
                track_memory_usage()

        mazooka_parsed_df = pd.DataFrame(mazooka_parsed_names)
        track_memory_usage()
        logger.info(f"Parsed {len(mazooka_parsed_df)} Mazooka names")

        # Join the adc_parsed_df with work_data_with_flags to add truncation flags
        adc_with_flags = adc_parsed_df.merge(
            work_data_with_flags[['APRA_WORK_ID', 'YN_COMPOSERS_TRUNC']],
            on='APRA_WORK_ID',
            how='left'
        )
        track_memory_usage()

        # Fill any missing values
        adc_with_flags['YN_COMPOSERS_TRUNC'] = adc_with_flags['YN_COMPOSERS_TRUNC'].fillna('N')

        # Save intermediate files for Phase 3
        adc_with_flags.to_csv(f"{OUTPUT_DIR}/phase2_adc_parsed_names.csv", index=False)
        mazooka_parsed_df.to_csv(f"{OUTPUT_DIR}/phase2_mazooka_parsed_names.csv", index=False)
        track_memory_usage()

        logger.info("Phase 2 complete! Intermediate files created for Phase 3.")

        return {
            "adc_parsed_table": adc_with_flags,
            "mazooka_parsed_table": mazooka_parsed_df
        }
    except Exception as e:
        logger.error(f"Error in phase2_name_parsing: {str(e)}", exc_info=True)
        raise


# PHASE 3
#@profile
def calculate_match_score_internal_pandas(apra_parsed, staging_parsed):
    """Internal function to calculate match score with improved fuzzy matching"""
    score = 0

    # Last name matching (2 points for exact, 1.5 for similar)
    if apra_parsed["last"] and staging_parsed["last"]:
        if apra_parsed["last"] == staging_parsed["last"]:
            score += 2  # Exact last name match
        else:
            # Improved similarity check for last names
            apra_last = apra_parsed["last"]
            staging_last = staging_parsed["last"]

            # Handle prefixes like "van", "von", "de", etc.
            prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL", "DOS", "DA", "DU", "AL", "EL"]

            # Check if both names have the same prefix
            apra_prefix = ""
            staging_prefix = ""

            for prefix in prefixes:
                if apra_last.startswith(prefix + " "):
                    apra_prefix = prefix + " "
                    apra_last_no_prefix = apra_last[len(prefix) + 1:]
                    break

            for prefix in prefixes:
                if staging_last.startswith(prefix + " "):
                    staging_prefix = prefix + " "
                    staging_last_no_prefix = staging_last[len(prefix) + 1:]
                    break

            # If both have the same prefix, compare the rest and add bonus for prefix
            prefix_match = 0
            if apra_prefix and staging_prefix and apra_prefix == staging_prefix:
                prefix_match = 0.2
                comparison_a = apra_last_no_prefix
                comparison_b = staging_last_no_prefix
            else:
                comparison_a = apra_last
                comparison_b = staging_last

            # Calculate similarity - improved method
            # Use Levenshtein distance for more accurate fuzzy matching
            max_len = max(len(comparison_a), len(comparison_b))
            if max_len > 0:
                # Calculate similarity based on length difference and common characters
                len_diff = abs(len(comparison_a) - len(comparison_b)) / max_len

                # Count common characters in sequence (better than just set overlap)
                common_chars_count = 0
                for i in range(min(len(comparison_a), len(comparison_b))):
                    if comparison_a[i] == comparison_b[i]:
                        common_chars_count += 1

                # Calculate sequence similarity
                sequence_similarity = common_chars_count / max_len

                # Calculate character set similarity (for shuffled letters)
                char_set_a = set(comparison_a)
                char_set_b = set(comparison_b)
                common_chars = char_set_a & char_set_b
                set_similarity = len(common_chars) / max(len(char_set_a), len(char_set_b))

                # Combined similarity score - weighs sequence matching higher than set matching
                similarity = (0.7 * sequence_similarity + 0.3 * set_similarity) * (1 - 0.5 * len_diff)

                # Handle specific suffix differences like "MILLER" vs "MILL"
                if (comparison_a.startswith(comparison_b) or comparison_b.startswith(comparison_a)) and \
                        max(len(comparison_a), len(comparison_b)) >= 4:
                    similarity = max(similarity, 0.85)  # Boost score for prefix matches with substantial length

                # Apply score based on similarity threshold
                if similarity >= 0.9:
                    score += 1.5 + prefix_match
                elif similarity >= 0.8:
                    score += 1.2 + prefix_match
                elif similarity >= 0.7:
                    score += 1.0 + prefix_match

    # First name matching (1 point for exact, 0.5 for initial match)
    if apra_parsed["first"] and staging_parsed["first"]:
        if apra_parsed["first"] == staging_parsed["first"]:
            score += 1  # Exact first name match
        else:
            # Check for initial match
            apra_initial = apra_parsed["first"][0] if apra_parsed["first"] else ""
            staging_initial = staging_parsed["first"][0] if staging_parsed["first"] else ""

            if len(apra_parsed["first"]) == 1 and len(staging_parsed["first"]) == 1:
                # Both are initials
                if apra_initial == staging_initial:
                    score += 0.5
                else:
                    # Different initials are a strong indication of different people
                    return 0
            elif len(apra_parsed["first"]) == 1 and apra_initial == staging_initial:
                # One is initial, matches other's first letter
                score += 0.5
            elif len(staging_parsed["first"]) == 1 and staging_initial == apra_initial:
                # Other is initial, matches first's first letter
                score += 0.5
            else:
                # Better fuzzy matching for first names
                max_len = max(len(apra_parsed["first"]), len(staging_parsed["first"]))
                if max_len > 0:
                    # Similar approach as with last names
                    common_chars = set(apra_parsed["first"]) & set(staging_parsed["first"])
                    similarity = len(common_chars) / max_len

                    # Special case for name variants
                    if similarity >= 0.7:
                        # Check common nicknames/variants like "WILLIAM"/"BILL" or "ROBERT"/"BOB"
                        name_variants = {
                            "WILLIAM": ["BILL", "WILL", "WILLY"],
                            "ROBERT": ["ROB", "BOB", "BOBBY"],
                            "JAMES": ["JIM", "JIMMY"],
                            "MICHAEL": ["MIKE", "MICK"],
                            "ELIZABETH": ["LIZ", "BETH", "ELIZA"],
                            "CATHERINE": ["CATHY", "KATE"],
                            "RICHARD": ["RICK", "DICK", "RICH"],
                            # Add more as needed
                        }

                        # Check if either name is a known variant of the other
                        found_variant = False
                        for full_name, variants in name_variants.items():
                            if (apra_parsed["first"] == full_name and staging_parsed["first"] in variants) or \
                                    (staging_parsed["first"] == full_name and apra_parsed["first"] in variants):
                                found_variant = True
                                break

                        if found_variant:
                            score += 0.7  # Good score for known name variants
                        elif similarity >= 0.9:
                            score += 0.7  # High similarity
                        elif similarity >= 0.8:
                            score += 0.5  # Good similarity
                        else:
                            score += 0.3  # Some similarity

    # Handle suffixes like JR/SR
    suffixes = {"JR", "JNR", "JUNIOR", "SR", "SNR", "SENIOR"}
    apra_suffix = ""
    staging_suffix = ""

    # Extract suffixes from last name if present
    for suffix in suffixes:
        if apra_parsed["last"].endswith(" " + suffix):
            apra_suffix = suffix
        if staging_parsed["last"].endswith(" " + suffix):
            staging_suffix = suffix

    # Group similar suffixes
    jr_group = {"JR", "JNR", "JUNIOR"}
    sr_group = {"SR", "SNR", "SENIOR"}

    # If both have suffixes but they conflict (one is JR, one is SR), reduce score
    if apra_suffix and staging_suffix:
        if (apra_suffix in jr_group and staging_suffix in jr_group) or \
                (apra_suffix in sr_group and staging_suffix in sr_group):
            # Same suffix type - no penalty
            pass
        else:
            # Different suffix types (e.g., JR vs SR) - penalty
            score -= 1

    return max(0, score)  # Ensure score is non-negative

#@profile
def calculate_match_score_pandas(apra_first, apra_last, staging_first, staging_last):
    """Calculate match score between two names with improved name reversal handling"""
    if pd.isna(apra_first) or pd.isna(apra_last) or pd.isna(staging_first) or pd.isna(staging_last):
        return 0

    # Check if apra_first might actually be a last name and vice versa
    # Common indicators: length, presence of initials
    apra_first_could_be_last = len(apra_first) > 1 and len(apra_last) <= 2
    apra_last_could_be_first = len(apra_last) <= 2 and len(apra_first) > 1

    staging_first_could_be_last = len(staging_first) > 1 and len(staging_last) <= 2
    staging_last_could_be_first = len(staging_last) <= 2 and len(staging_first) > 1

    # Create parsed name objects - standard interpretation
    apra_parsed = {"first": apra_first, "last": apra_last}
    staging_parsed = {"first": staging_first, "last": staging_last}

    # Create parsed name objects - reversed interpretations
    apra_reversed = {"first": apra_last, "last": apra_first}
    staging_reversed = {"first": staging_last, "last": staging_first}

    # Calculate standard score
    standard_score = calculate_match_score_internal_pandas(apra_parsed, staging_parsed)

    # Calculate reversed scores with higher priority if indicators suggest reversal
    reversed_scores = [
        calculate_match_score_internal_pandas(apra_reversed, staging_parsed),
        calculate_match_score_internal_pandas(apra_parsed, staging_reversed),
        calculate_match_score_internal_pandas(apra_reversed, staging_reversed)
    ]

    # Boost specific reversal patterns
    if apra_first_could_be_last and staging_last_could_be_first:
        # e.g., "TAYLOR SWIFT" vs "SWIFT TAYLOR"
        reversed_scores[0] *= 1.1  # Small boost to encourage correct matching

    if apra_last_could_be_first and staging_first_could_be_last:
        reversed_scores[1] *= 1.1

    # Special case for "SMITH P" vs "P SMITH" type patterns
    if (len(apra_first) == 1 and len(staging_last) == 1) or \
            (len(apra_last) == 1 and len(staging_first) == 1):
        reversed_scores[2] *= 1.1

    # Return highest score
    return max([standard_score] + reversed_scores)



#@profile
# @profile
def phase3_matching():
    """Phase 3: Generate match scores and final output - matches only"""
    logger.info("Starting Phase 3: Match score generation and final output (matches only)...")

    try:
        # Load intermediate files from Phase 2
        adc_parsed_df = pd.read_csv(f"{OUTPUT_DIR}/phase2_adc_parsed_names.csv")
        mazooka_parsed_df = pd.read_csv(f"{OUTPUT_DIR}/phase2_mazooka_parsed_names.csv")

        logger.info("Loaded intermediate files from Phase 2")

        # STRATEGY 1: Filter Early - Only process ISWCs that exist in both datasets
        valid_iswcs = set(adc_parsed_df[~adc_parsed_df['ISWC'].isna()]['ISWC'].unique()) & \
                      set(mazooka_parsed_df[~mazooka_parsed_df['ISWC'].isna()]['ISWC'].unique())
        logger.info(f"Found {len(valid_iswcs)} ISWCs that exist in both datasets")

        # Filter both dataframes
        adc_parsed_df = adc_parsed_df[adc_parsed_df['ISWC'].isin(valid_iswcs)]
        mazooka_parsed_df = mazooka_parsed_df[mazooka_parsed_df['ISWC'].isin(valid_iswcs)]

        logger.info(f"After filtering: {len(adc_parsed_df)} ADC records and {len(mazooka_parsed_df)} Mazooka records")

        # Group ADC composers by work_id and ISWC for batch processing
        adc_grouped = adc_parsed_df.groupby(['APRA_WORK_ID', 'ISWC'])
        all_work_iswcs = list(adc_grouped.groups.keys())
        logger.info(f"Found {len(all_work_iswcs)} unique work-ISWC combinations to process")

        # STRATEGY 2: Vectorized name matching function
        def calculate_match_scores_vectorized(apra_first_names, apra_last_names,
                                              mazooka_first_names, mazooka_last_names):
            """Calculate match scores in a vectorized way with improved fuzzy matching"""
            # Initialize scores matrix
            n_apra = len(apra_first_names)
            n_mazooka = len(mazooka_first_names)
            scores = np.zeros((n_apra, n_mazooka))

            # Convert names to arrays for vectorized operations
            apra_first = np.array(apra_first_names)
            apra_last = np.array(apra_last_names)
            mazooka_first = np.array(mazooka_first_names)
            mazooka_last = np.array(mazooka_last_names)

            # 1. Standard orientation matching
            # Last name exact matches (2 points)
            last_exact_matches = np.zeros((n_apra, n_mazooka))
            for i in range(n_apra):
                last_exact_matches[i, :] = (apra_last[i] == mazooka_last)
            scores += last_exact_matches * 2

            # First name exact matches (1 point)
            first_exact_matches = np.zeros((n_apra, n_mazooka))
            for i in range(n_apra):
                first_exact_matches[i, :] = (apra_first[i] == mazooka_first)
            scores += first_exact_matches * 1

            # Initial matches (0.5 points) - only applied when no exact match exists
            initial_matches = np.zeros((n_apra, n_mazooka))
            for i in range(n_apra):
                if len(apra_first[i]) > 0:
                    apra_initial = apra_first[i][0]
                    for j in range(n_mazooka):
                        if not first_exact_matches[i, j] and len(mazooka_first[j]) > 0:
                            mazooka_initial = mazooka_first[j][0]
                            if apra_initial == mazooka_initial:
                                initial_matches[i, j] = 1
            scores += (initial_matches * 0.5) * (1 - first_exact_matches)

            # 2. Fuzzy matching for last names
            for i in range(n_apra):
                for j in range(n_mazooka):
                    # Skip if we already have an exact match
                    if last_exact_matches[i, j]:
                        continue

                    apra_name = apra_last[i]
                    mazooka_name = mazooka_last[j]

                    # Skip empty names
                    if not apra_name or not mazooka_name:
                        continue

                    # Prefix handling
                    prefixes = ["VAN", "VON", "DE", "DER", "LA", "LE", "DI", "DEL"]
                    apra_prefix = ""
                    mazooka_prefix = ""

                    for prefix in prefixes:
                        if apra_name.startswith(prefix + " "):
                            apra_prefix = prefix
                            apra_name = apra_name[len(prefix) + 1:]
                            break

                    for prefix in prefixes:
                        if mazooka_name.startswith(prefix + " "):
                            mazooka_prefix = prefix
                            mazooka_name = mazooka_name[len(prefix) + 1:]
                            break

                    # Common prefix bonus
                    prefix_bonus = 0
                    if apra_prefix and mazooka_prefix and apra_prefix == mazooka_prefix:
                        prefix_bonus = 0.2

                    # Simple fuzzy matching (adapted for vectorized context)
                    if apra_name and mazooka_name:
                        # Check for substring relationship
                        if apra_name in mazooka_name or mazooka_name in apra_name:
                            substring_ratio = min(len(apra_name), len(mazooka_name)) / max(len(apra_name),
                                                                                           len(mazooka_name))
                            if substring_ratio >= 0.7:
                                scores[i, j] += 1.5 + prefix_bonus
                                continue

                        # Calculate similarity based on character overlap
                        common_chars = set(apra_name) & set(mazooka_name)
                        similarity = len(common_chars) / max(len(set(apra_name)), len(set(mazooka_name)))

                        if similarity >= 0.8:
                            scores[i, j] += 1.5 + prefix_bonus
                        elif similarity >= 0.7:
                            scores[i, j] += 1.0 + prefix_bonus

            # 3. Name reversal handling - MODIFIED SECTION
            # eg "SWIFT TAYLOR" vs "TAYLOR SWIFT" - Now gives full score of 3.0
            for i in range(n_apra):
                for j in range(n_mazooka):
                    # Skip if we already have a high standard match
                    if scores[i, j] >= 3.0:
                        continue

                    # Complete name reversal check - give full 3.0 points
                    if apra_first[i] and apra_last[i] and mazooka_first[j] and mazooka_last[j]:
                        # Check for exact reversal: first name matches last name AND last name matches first name
                        if apra_first[i] == mazooka_last[j] and apra_last[i] == mazooka_first[j]:
                            # Complete reversal - full score 3.0 (instead of 2.5)
                            scores[i, j] = 3.0
                        # Partial matches still get 1.5
                        elif apra_first[i] == mazooka_last[j]:
                            # Partial match - first name matches last name
                            scores[i, j] = max(scores[i, j], 1.5)
                        elif apra_last[i] == mazooka_first[j]:
                            # Partial match - last name matches first name
                            scores[i, j] = max(scores[i, j], 1.5)

            return scores

        # Initialize results list for all batches
        all_batch_results = []
        total_results_count = 0

        # STRATEGY 4: Batch Processing
        batch_size = 5000  # Process this many work-ISWC combinations per batch
        num_batches = (len(all_work_iswcs) + batch_size - 1) // batch_size

        for batch_idx in range(num_batches):
            batch_start = batch_idx * batch_size
            batch_end = min((batch_idx + 1) * batch_size, len(all_work_iswcs))
            current_batch = all_work_iswcs[batch_start:batch_end]

            logger.info(f"Processing batch {batch_idx + 1}/{num_batches}: {batch_start} to {batch_end}")

            batch_results = []
            processed_in_batch = 0

            for work_id, work_iswc in current_batch:
                # Skip if ISWC is NaN (shouldn't happen due to our filtering, but just in case)
                if pd.isna(work_iswc):
                    continue

                # Get ADC data for this work-ISWC
                adc_group = adc_grouped.get_group((work_id, work_iswc))

                # Find all matching Mazooka composers with the same ISWC
                matching_mazooka = mazooka_parsed_df[mazooka_parsed_df['ISWC'] == work_iswc]

                if len(matching_mazooka) > 0:
                    # Group by track ID
                    mazooka_grouped = matching_mazooka.groupby('TRACK_ID')

                    for track_id, mazooka_group in mazooka_grouped:
                        # Skip if either group is empty
                        if len(adc_group) == 0 or len(mazooka_group) == 0:
                            continue

                        # Check if this combination has too many potential matches
                        if len(adc_group) * len(mazooka_group) > 10000:  # Safety threshold
                            logger.warning(
                                f"Skipping work_id={work_id}, track_id={track_id} - too many combinations: {len(adc_group)}x{len(mazooka_group)}")
                            continue

                        # Get data for vectorized matching
                        apra_data = adc_group[['APRA_NAME', 'APRA_FIRST_NAME', 'APRA_LAST_NAME',
                                               'APRA_NAME_SCORE', 'YN_COMPOSERS_TRUNC']].to_dict('records')
                        mazooka_data = mazooka_group[['MAZOOKA_NAME', 'MAZOOKA_FIRST_NAME',
                                                      'MAZOOKA_LAST_NAME', 'MAZOOKA_NAME_SCORE']].to_dict('records')

                        # Calculate total available points
                        atap = sum(item['APRA_NAME_SCORE'] for item in apra_data)
                        stap = sum(item['MAZOOKA_NAME_SCORE'] for item in mazooka_data)
                        tap = max(atap, stap)

                        # Get the arrays for vectorized matching
                        apra_first_names = [item['APRA_FIRST_NAME'] if not pd.isna(item['APRA_FIRST_NAME']) else "" for
                                            item in apra_data]
                        apra_last_names = [item['APRA_LAST_NAME'] if not pd.isna(item['APRA_LAST_NAME']) else "" for
                                           item in apra_data]
                        mazooka_first_names = [
                            item['MAZOOKA_FIRST_NAME'] if not pd.isna(item['MAZOOKA_FIRST_NAME']) else "" for item in
                            mazooka_data]
                        mazooka_last_names = [
                            item['MAZOOKA_LAST_NAME'] if not pd.isna(item['MAZOOKA_LAST_NAME']) else "" for item in
                            mazooka_data]

                        # Calculate match scores using vectorized function
                        score_matrix = calculate_match_scores_vectorized(
                            apra_first_names,
                            apra_last_names,
                            mazooka_first_names,
                            mazooka_last_names
                        )

                        # Find matches greedily in order of score
                        matches = []
                        used_apra_indices = set()
                        used_mazooka_indices = set()
                        smp = 0  # Sum of matched points

                        # Create all possible matches with scores
                        all_possible_matches = []
                        for apra_idx in range(len(apra_data)):
                            for mazooka_idx in range(len(mazooka_data)):
                                score = score_matrix[apra_idx, mazooka_idx]
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

                        # Format results - ONLY include matched items
                        for i, apra_item in enumerate(apra_data):
                            if not apra_item['APRA_NAME'] or pd.isna(apra_item['APRA_NAME']) or apra_item['APRA_NAME'].strip() == "":
                                continue

                            # Only process composers that have a match
                            for match in matches:
                                if match["apra_idx"] == i:
                                    mazooka_idx = match["mazooka_idx"]
                                    score = match["score"]
                                    mazooka_item = mazooka_data[mazooka_idx]

                                    row = {
                                        "APRA_NAME": apra_item['APRA_NAME'],
                                        "APRA_NAME_SCORE": apra_item['APRA_NAME_SCORE'],
                                        "MATCH_STATUS": "match",
                                        "MAZOOKA_NAME": mazooka_item["MAZOOKA_NAME"],
                                        "MAZOOKA_NAME_SCORE": float(mazooka_item["MAZOOKA_NAME_SCORE"]),
                                        "NAME_MATCHED_SCORE": float(score),
                                        "WORK_ID": work_id,
                                        "TRACK_ID": track_id,
                                        "ISWC": work_iswc,
                                        "MATCH_PERCENT": match_percent,
                                        "YN_COMPOSERS_TRUNC": apra_item.get('YN_COMPOSERS_TRUNC', 'N')
                                    }

                                    batch_results.append(row)
                                    break
                            # Removed the else block that was adding unmatched composers

                processed_in_batch += 1

                # Status update within batch
                if processed_in_batch % 100 == 0:
                    logger.info(
                        f"  Processed {processed_in_batch} of {len(current_batch)} work-ISWC combinations in current batch")
                    logger.info(f"  Current batch result count: {len(batch_results)} rows")

            # End of batch - save intermediate results for this batch
            if batch_results:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                batch_df = pd.DataFrame(batch_results)
                batch_output_path = f"{OUTPUT_DIR}/phase3_batch_{batch_idx + 1}_of_{num_batches}_{timestamp}.csv"
                batch_df.to_csv(batch_output_path, index=False)

                # Add batch results to total count and free memory
                total_results_count += len(batch_results)
                all_batch_results.append(batch_output_path)

                logger.info(
                    f"Completed batch {batch_idx + 1}/{num_batches}: {len(batch_results)} rows written to {batch_output_path}")
                logger.info(f"Total results so far: {total_results_count} rows")

            # Clear memory before processing next batch
            del batch_results
            import gc
            gc.collect()

        # After all batches are processed, combine the results if needed
        logger.info(
            f"All batches completed. Total results: {total_results_count} rows across {len(all_batch_results)} batch files")

        # Skip if there are no batch results
        if not all_batch_results:
            logger.warning("No results were generated!")
            return pd.DataFrame()

        # START OF OUTPUT TABLE CREATION
        logger.info(f"======= OUTPUT TABLE CREATION MEMORY STATS =======")
        mem_before = memory_usage_now()
        logger.info(f"Memory before output DataFrame creation: {mem_before:.2f} MiB")

        # Combine all batch CSVs into a single result dataframe
        logger.info(f"Combining {len(all_batch_results)} batch files into final result")
        result_df = pd.concat([pd.read_csv(batch_file) for batch_file in all_batch_results], ignore_index=True)

        mem_after_df = memory_usage_now()
        logger.info(f"Memory after output DataFrame creation: {mem_after_df:.2f} MiB")
        logger.info(f"Memory change for DataFrame creation: {mem_after_df - mem_before:.2f} MiB")

        # Ensure all numeric columns have the right data type
        numeric_columns = ['APRA_NAME_SCORE', 'MAZOOKA_NAME_SCORE', 'NAME_MATCHED_SCORE', 'MATCH_PERCENT']
        for col in numeric_columns:
            # Convert to float, replacing any non-numeric values with 0.0
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce').fillna(0.0)

        mem_after_numeric = memory_usage_now()
        logger.info(f"Memory after numeric conversion: {mem_after_numeric:.2f} MiB")
        logger.info(f"Memory change for numeric conversion: {mem_after_numeric - mem_after_df:.2f} MiB")

        # Remove duplicates - since all rows are matches, we simply deduplicate
        logger.info("Removing duplicates...")
        mem_before_dedup = memory_usage_now()
        logger.info(f"Memory before deduplication: {mem_before_dedup:.2f} MiB")

        # All rows are matches, so we can simply deduplicate
        result_df = result_df.drop_duplicates(subset=['APRA_NAME', 'WORK_ID'], keep='first')

        mem_after_dedup = memory_usage_now()
        logger.info(f"Memory after deduplication: {mem_after_dedup:.2f} MiB")
        logger.info(f"Memory change for deduplication: {mem_after_dedup - mem_before_dedup:.2f} MiB")
        logger.info(f"After deduplication: {len(result_df)} rows")

        # Add row number
        result_df.insert(0, 'ROW_NUM', range(1, len(result_df) + 1))

        mem_after_rownum = memory_usage_now()
        logger.info(f"Memory after adding row numbers: {mem_after_rownum:.2f} MiB")
        logger.info(f"Memory change for adding row numbers: {mem_after_rownum - mem_after_dedup:.2f} MiB")

        # Save final results
        mem_before_save = memory_usage_now()
        logger.info(f"Memory before saving to CSV: {mem_before_save:.2f} MiB")

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        final_output_path = f"{OUTPUT_DIR}/composer_name_matching_results_matched_only_{timestamp}.csv"
        result_df.to_csv(final_output_path, index=False)

        mem_after_save = memory_usage_now()
        logger.info(f"Memory after saving to CSV: {mem_after_save:.2f} MiB")
        logger.info(f"Memory change for saving to CSV: {mem_after_save - mem_before_save:.2f} MiB")

        # Total memory change for output creation
        logger.info(f"TOTAL memory change for output creation: {mem_after_save - mem_before:.2f} MiB")
        logger.info(f"======= END OUTPUT TABLE CREATION MEMORY STATS =======")

        logger.info(f"Successfully wrote {len(result_df)} rows to final results file: {final_output_path}")
        logger.info("Name matching process complete! (Matches only)")

        return result_df
    except Exception as e:
        logger.error(f"Error in phase3_matching: {str(e)}", exc_info=True)
        raise


# Main function with sampling
# @profile
# def main_with_sampling(sample_percentage=33):
#     """
#     Main function that samples data before processing
#
#     Args:
#         sample_percentage: Percentage of data to sample (default: 33%)
#     """
#     logger.info(f"Starting name matching process with {sample_percentage}% data sample...")
#
#     try:
#         # Load the original tables
#         adc_composers = pd.read_csv(f"{DATA_DIR}/adc_composers.csv")
#         mazooka_composers = pd.read_csv(f"{DATA_DIR}/mazooka_composers.csv")
#         adc_works = pd.read_csv(f"{DATA_DIR}/adc_works.csv")
#
#         # Get original row counts
#         adc_count = len(adc_composers)
#         mazooka_count = len(mazooka_composers)
#         works_count = len(adc_works)
#
#         logger.info(
#             f"Original data: {adc_count} ADC composer rows, {mazooka_count} Mazooka composer rows, {works_count} ADC works rows")
#
#         # Sample the tables
#         sampled_adc_composers = adc_composers.sample(frac=sample_percentage / 100)
#         sampled_mazooka_composers = mazooka_composers.sample(frac=sample_percentage / 100)
#
#         # For works, we need to sample based on the sampled ADC composers to maintain referential integrity
#         sampled_apra_work_ids = sampled_adc_composers['APRA_WORK_ID'].unique()
#         sampled_adc_works = adc_works[adc_works['APRA_WORK_ID'].isin(sampled_apra_work_ids)]
#
#         # Get sampled row counts
#         sampled_adc_count = len(sampled_adc_composers)
#         sampled_mazooka_count = len(sampled_mazooka_composers)
#         sampled_works_count = len(sampled_adc_works)
#
#         logger.info(f"Sampled data: {sampled_adc_count} ADC composer rows ({sampled_adc_count / adc_count:.1%}), " +
#                     f"{sampled_mazooka_count} Mazooka composer rows ({sampled_mazooka_count / mazooka_count:.1%}), " +
#                     f"{sampled_works_count} ADC works rows ({sampled_works_count / works_count:.1%})")
#
#         # Save sampled data to temporary CSV files
#         sampled_adc_composers.to_csv(f"{DATA_DIR}/temp_sampled_adc_composers.csv", index=False)
#         sampled_mazooka_composers.to_csv(f"{DATA_DIR}/temp_sampled_mazooka_composers.csv", index=False)
#         sampled_adc_works.to_csv(f"{DATA_DIR}/temp_sampled_adc_works.csv", index=False)
#
#         # Modified phase1_preprocessing function to use sampled data
#         def modified_phase1_preprocessing():
#             """Modified Phase 1 function that uses sampled data"""
#             logger.info("Starting Phase 1 with sampled data: Preprocessing and truncation identification...")
#
#             # Load the sampled data
#             adc_composers = pd.read_csv(f"/Users/shruti/PycharmProjects/APRA_DEV/Data/ADC.csv")
#             mazooka_composers = pd.read_csv(f"/Users/shruti/PycharmProjects/APRA_DEV/Data/MZK.csv")
#             adc_works = pd.read_csv(f"{DATA_DIR}/temp_sampled_adc_works.csv")
#
#             # Get row counts for initial data
#             adc_count = len(adc_composers)
#             mazooka_count = len(mazooka_composers)
#             logger.info(
#                 f"Processing {adc_count} sampled ADC composer rows and {mazooka_count} sampled Mazooka composer rows")
#
#             # Apply Rule 1: Convert all text columns to uppercase and trim
#             for column in adc_composers.select_dtypes(include=['object']).columns:
#                 adc_composers[column] = adc_composers[column].apply(clean_text)
#
#             for column in mazooka_composers.select_dtypes(include=['object']).columns:
#                 mazooka_composers[column] = mazooka_composers[column].apply(clean_text)
#
#             # Create expanded datasets with one composer per row
#             logger.info("Expanding composer names...")
#
#             # For ADC data
#             expanded_adc = []
#             for idx, row in enumerate(adc_composers.iterrows()):
#                 _, row_data = row
#                 composers = split_composer_names_pandas(row_data['NAME'])
#                 if not composers:  # If no composers after splitting, use the original
#                     composers = [row_data['NAME']]
#
#                 for composer in composers:
#                     new_row = row_data.copy()
#                     new_row['NAME'] = composer
#                     expanded_adc.append(new_row)
#
#                 # Status update every 50000 rows (adjusted for sampled data)
#                 if (idx + 1) % 50000 == 0:
#                     logger.info(f"Processed {idx + 1}/{len(adc_composers)} ADC rows")
#
#             expanded_adc_df = pd.DataFrame(expanded_adc)
#
#             # For Mazooka data
#             expanded_mazooka = []
#             for idx, row in enumerate(mazooka_composers.iterrows()):
#                 _, row_data = row
#                 composers = split_composer_names_pandas(row_data['COMPOSER'])
#                 if not composers:  # If no composers after splitting, use the original
#                     composers = [row_data['COMPOSER']]
#
#                 for composer in composers:
#                     new_row = row_data.copy()
#                     new_row['COMPOSER'] = composer
#                     expanded_mazooka.append(new_row)
#
#                 # Status update every 50000 rows (adjusted for sampled data)
#                 if (idx + 1) % 50000 == 0:
#                     logger.info(f"Processed {idx + 1}/{len(mazooka_composers)} Mazooka rows")
#
#             expanded_mazooka_df = pd.DataFrame(expanded_mazooka)
#
#             logger.info(f"Expanded ADC data to {len(expanded_adc_df)} rows")
#             logger.info(f"Expanded Mazooka data to {len(expanded_mazooka_df)} rows")
#
#             # Count composers per work and per track
#             adc_composer_count = expanded_adc_df.groupby('APRA_WORK_ID').size().reset_index(name='ADC_COMPOSERS_COUNT')
#             mazooka_composer_count = expanded_mazooka_df.groupby(['TRACK_ID', 'ISWC']).size().reset_index(
#                 name='MAZOOKA_COMPOSERS_COUNT')
#
#             # Merge work data with composer counts
#             work_data = adc_works.merge(adc_composer_count, on='APRA_WORK_ID', how='left')
#
#             # Get max Mazooka composer count by ISWC
#             mazooka_max_count = mazooka_composer_count.groupby('ISWC')['MAZOOKA_COMPOSERS_COUNT'].max().reset_index()
#
#             # Merge with work_data
#             work_data = work_data.merge(mazooka_max_count, on='ISWC', how='left')
#
#             # Fill NaN values
#             work_data['ADC_COMPOSERS_COUNT'] = work_data['ADC_COMPOSERS_COUNT'].fillna(0)
#             work_data['MAZOOKA_COMPOSERS_COUNT'] = work_data['MAZOOKA_COMPOSERS_COUNT'].fillna(0)
#
#             # Get composer_names length
#             if 'COMPOSERS' in work_data.columns:
#                 work_data['COMPOSER_NAME_LENGTH'] = work_data['COMPOSERS'].astype(str).str.len()
#             else:
#                 work_data['COMPOSER_NAME_LENGTH'] = 0
#
#             # Apply the truncation rule
#             work_data['YN_COMPOSERS_TRUNC'] = 'N'
#
#             # Set to 'Y' when the criteria are met
#             mask = ((work_data['YN_PERF_OWNERSHIP'] == 'N') &
#                     (work_data['COMPOSER_NAME_LENGTH'] >= 39) &
#                     (work_data['ADC_COMPOSERS_COUNT'] < work_data['MAZOOKA_COMPOSERS_COUNT']))
#
#             work_data.loc[mask, 'YN_COMPOSERS_TRUNC'] = 'Y'
#
#             # Save intermediate files for the next phase
#             expanded_adc_df.to_csv(f"{OUTPUT_DIR}/phase1_cleaned_adc_composers.csv", index=False)
#             expanded_mazooka_df.to_csv(f"{OUTPUT_DIR}/phase1_cleaned_mazooka_composers.csv", index=False)
#             work_data.to_csv(f"{OUTPUT_DIR}/phase1_work_data_with_flags.csv", index=False)
#
#             logger.info("Phase 1 complete! Intermediate files created for Phase 2.")
#
#             return {
#                 "cleaned_adc_composers": expanded_adc_df,
#                 "cleaned_mazooka_composers": expanded_mazooka_df,
#                 "work_data_with_flags": work_data
#             }
#
#         # Run the modified phase 1 with sampled data
#         logger.info("\n=== PHASE 1: PREPROCESSING AND TRUNCATION IDENTIFICATION (WITH SAMPLING) ===")
#         phase1_results = modified_phase1_preprocessing()
#
#         # Phases 2 and 3 will automatically use the intermediate files created by phase 1
#         logger.info("\n=== PHASE 2: NAME PARSING AND SCORE GENERATION (WITH SAMPLING) ===")
#         phase2_results = phase2_name_parsing()
#
#         logger.info("\n=== PHASE 3: MATCH SCORE GENERATION AND FINAL OUTPUT (WITH SAMPLING) ===")
#         final_results = phase3_matching()
#
#         logger.info("\nAll phases completed successfully with sampled data!")
#
#         # Rename the final output file to indicate it's from sampled data
#         timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
#         final_output_path = f"{OUTPUT_DIR}/composer_name_matching_results_{timestamp}.csv"
#         sampled_output_path = f"{OUTPUT_DIR}/composer_name_matching_results_{sample_percentage}pct_{timestamp}.csv"
#
#         if os.path.exists(final_output_path):
#             os.rename(final_output_path, sampled_output_path)
#             logger.info(f"Final results saved to: {sampled_output_path}")
#
#         # Clean up temporary files
#         logger.info("Cleaning up temporary files...")
#         for temp_file in [
#             f"{DATA_DIR}/temp_sampled_adc_composers.csv",
#             f"{DATA_DIR}/temp_sampled_mazooka_composers.csv",
#             f"{DATA_DIR}/temp_sampled_adc_works.csv"
#         ]:
#             if os.path.exists(temp_file):
#                 os.remove(temp_file)
#
#         return final_results
#
#     except Exception as e:
#         logger.error(f"Error in main_with_sampling: {str(e)}", exc_info=True)
#         raise


def main():
    """Main function to orchestrate the three-phase name matching process"""
    logger.info("Starting name matching process with three-phase approach...")

    # Execute Phase 1: Preprocessing and truncation identification
    logger.info("=== PHASE 1: PREPROCESSING AND TRUNCATION IDENTIFICATION ===")
    phase1_results = phase1_preprocessing()

    # Execute Phase 2: Name parsing and score generation
    logger.info("\n=== PHASE 2: NAME PARSING AND SCORE GENERATION ===")
    phase2_results = phase2_name_parsing()

    # Execute Phase 3: Match score generation and final output
    logger.info("\n=== PHASE 3: MATCH SCORE GENERATION AND FINAL OUTPUT ===")
    final_results = phase3_matching()

    logger.info("\nAll phases completed successfully!")
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Final results saved to: {OUTPUT_DIR}/composer_name_matching_results_{timestamp}.csv")

    return final_results


if __name__ == "__main__":
    # Choose one of the following:

    # For full processing:
    result_df = main()

    # For processing with sampling:
    # result_df = main_with_sampling(33)  # For 33% sample

    # Display first few rows of the result
    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        print(result_df.head(10))
    else:
        logger.info("No results to display or results are not in DataFrame format")