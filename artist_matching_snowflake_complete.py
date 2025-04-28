import re
import difflib
import pandas as pd
import numpy as np
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit


# Function to clean artist names by removing non-alphanumeric characters
def clean_artist_name(name):
    if name is None or pd.isna(name):
        return ""
    # Remove non-alphanumeric characters (except spaces)
    cleaned = re.sub(r'[^a-zA-Z0-9 ]', '', str(name))
    # If the result is just spaces, return the original name
    if cleaned.strip() == "":
        return str(name)
    return cleaned.strip()


# Improved similarity function with more accurate scoring
def calculate_similarity(str1, str2):
    if not str1 or not str2 or pd.isna(str1) or pd.isna(str2):
        return 0

    str1 = str(str1).upper()
    str2 = str(str2).upper()

    # Use difflib's SequenceMatcher but with stricter scoring
    basic_score = difflib.SequenceMatcher(None, str1, str2).ratio()

    # Penalize significant length differences more severely
    len_ratio = min(len(str1), len(str2)) / max(len(str1), len(str2))
    if len_ratio < 0.7:  # If lengths differ by more than 30%
        basic_score *= len_ratio

    return round(basic_score, 2)


# Function to handle artist names with "/"
def match_with_slash_handling(adc_name, mazooka_name):
    # First try matching the full names
    full_match_score = calculate_similarity(adc_name, mazooka_name)

    # If the score is very high, return it immediately
    if full_match_score > 0.9:
        return full_match_score

    # If either name contains "/", try matching individual parts
    if "/" in str(adc_name) or "/" in str(mazooka_name):
        adc_parts = [part.strip() for part in str(adc_name).split("/")] if "/" in str(adc_name) else [adc_name]
        mazooka_parts = [part.strip() for part in str(mazooka_name).split("/")] if "/" in str(mazooka_name) else [
            mazooka_name]

        # Compare each part combination
        part_scores = []
        for adc_part in adc_parts:
            for mazooka_part in mazooka_parts:
                if len(adc_part) > 2 and len(mazooka_part) > 2:  # Only consider meaningful parts
                    part_score = calculate_similarity(adc_part, mazooka_part)
                    # Only consider high-quality part matches
                    if part_score > 0.75:
                        part_scores.append(part_score)

        # If we have valid part scores, return the best one
        if part_scores:
            return max(part_scores)

    return full_match_score


# Improved function to handle artist names with "&" or "and"
def handle_band_names(name1, name2):
    name1_upper = str(name1).upper()
    name2_upper = str(name2).upper()

    # Check for exact match first
    if name1_upper == name2_upper:
        return 1.0

    # Extract main artist from "ARTIST & THE BAND" or "ARTIST AND THE BAND" format
    name1_parts = re.split(r'\s+(&|\band\b)\s+', name1_upper)
    name2_parts = re.split(r'\s+(&|\band\b)\s+', name2_upper)

    # Get the main artist names (before "&" or "and")
    name1_main = name1_parts[0].strip() if name1_parts else name1_upper
    name2_main = name2_parts[0].strip() if name2_parts else name2_upper

    # Calculate scores
    full_score = calculate_similarity(name1_upper, name2_upper)

    # Only consider main name match if the main names are substantial
    main_score = 0
    if len(name1_main) > 3 and len(name2_main) > 3:
        main_score = calculate_similarity(name1_main, name2_main)
        # Boost main score only if it's very good
        if main_score > 0.9:
            main_score = max(0.85, main_score)  # At least 0.85 for good main name match

    # If one name has additional parts and main names match well, give good score
    if main_score > 0.9 and len(name1_parts) != len(name2_parts):
        return max(0.8, full_score)  # Substantial but not perfect match

    return max(full_score, main_score * 0.9)  # Slightly discount main name matches


# New function to check for first/last name or initials match with stricter scoring
def check_name_parts_match(name1, name2):
    if not name1 or not name2:
        return 0

    name1 = str(name1).upper()
    name2 = str(name2).upper()

    # Split into words
    name1_parts = name1.split()
    name2_parts = name2.split()

    # If either name has no parts, return 0
    if not name1_parts or not name2_parts:
        return 0

    # Check for exact matches of any parts
    exact_matches = sum(1 for p1 in name1_parts if any(p1 == p2 for p2 in name2_parts))

    # Calculate percentage of exact matches, but be stricter
    match_percent = exact_matches / max(len(name1_parts), len(name2_parts))

    # Require at least 50% of words to match and penalize common single-word names
    if match_percent < 0.5 or (match_percent == 1.0 and len(name1_parts) == 1 and len(name1_parts[0]) < 5):
        match_percent *= 0.7  # Reduce score

    # Check for initials match - but only if names have multiple parts
    initials_score = 0
    if len(name1_parts) >= 2 and len(name2_parts) >= 2:
        name1_initials = ''.join(p[0] for p in name1_parts if p)
        name2_initials = ''.join(p[0] for p in name2_parts if p)

        if len(name1_initials) >= 2 and len(name2_initials) >= 2:
            initials_match = calculate_similarity(name1_initials, name2_initials)
            # Only consider high-quality initial matches
            initials_score = initials_match * 0.7 if initials_match > 0.8 else 0

    # Check first/last name match (if names have at least 2 parts)
    first_last_score = 0
    if len(name1_parts) >= 2 and len(name2_parts) >= 2:
        # First name match
        first_match = calculate_similarity(name1_parts[0], name2_parts[0])
        # Last name match
        last_match = calculate_similarity(name1_parts[-1], name2_parts[-1])

        # Only consider if both first and last have decent match
        if first_match > 0.7 and last_match > 0.7:
            first_last_score = (first_match + last_match) / 2
        else:
            first_last_score = 0  # Both need to match well

    # Return the best score but cap if match is not strong
    best_score = max(match_percent, initials_score, first_last_score)
    return min(best_score, 0.9) if best_score < 0.9 else best_score  # Cap at 0.9 unless perfect


# Improved function to handle prefix/suffix removal
def check_with_prefix_suffix_removal(name1, name2):
    prefixes = ["THE ", "DJ ", "MC ", "DR ", "MR ", "MS ", "MISS ", "MRS ", "SIR "]
    suffixes = [" BAND", " ORCHESTRA", " ENSEMBLE", " QUARTET", " TRIO", " DUO", " GROUP"]

    # Create versions with prefixes removed
    name1_no_prefix = str(name1).upper()
    name2_no_prefix = str(name2).upper()

    for prefix in prefixes:
        if name1_no_prefix.startswith(prefix):
            name1_no_prefix = name1_no_prefix[len(prefix):]
        if name2_no_prefix.startswith(prefix):
            name2_no_prefix = name2_no_prefix[len(prefix):]

    # Create versions with suffixes removed
    name1_no_suffix = name1_no_prefix
    name2_no_suffix = name2_no_prefix

    for suffix in suffixes:
        if name1_no_suffix.endswith(suffix):
            name1_no_suffix = name1_no_suffix[:-len(suffix)]
        if name2_no_suffix.endswith(suffix):
            name2_no_suffix = name2_no_suffix[:-len(suffix)]

    # Calculate scores
    original_score = calculate_similarity(str(name1).upper(), str(name2).upper())

    # Only consider prefix/suffix removal if it substantially improves match
    no_prefix_score = calculate_similarity(name1_no_prefix, name2_no_prefix)
    no_suffix_score = calculate_similarity(name1_no_suffix, name2_no_suffix)

    # Use modified score only if the improvement is significant and score is good
    if no_prefix_score > original_score + 0.2 and no_prefix_score > 0.8:
        return no_prefix_score
    elif no_suffix_score > original_score + 0.2 and no_suffix_score > 0.8:
        return no_suffix_score

    return original_score  # Default to original score


# Improved comprehensive match function that combines all methods with better validation
def comprehensive_match_score(adc_name, mazooka_name):
    if not adc_name or not mazooka_name or pd.isna(adc_name) or pd.isna(mazooka_name):
        return 0

    # Check for exact match (case insensitive)
    if str(adc_name).upper() == str(mazooka_name).upper():
        return 1.0

    # Check for "THE" prefix differences - if exact match after removing "THE", give high score
    adc_no_the = str(adc_name).upper()
    mazooka_no_the = str(mazooka_name).upper()

    if adc_no_the.startswith("THE "):
        adc_no_the = adc_no_the[4:]
    if mazooka_no_the.startswith("THE "):
        mazooka_no_the = mazooka_no_the[4:]

    if adc_no_the == mazooka_no_the and len(adc_no_the) > 4:
        return 0.95  # Very high but not perfect for "THE" differences

    # Apply all matching methods
    similarity_score = calculate_similarity(adc_name, mazooka_name)
    slash_score = match_with_slash_handling(adc_name, mazooka_name)
    band_score = handle_band_names(adc_name, mazooka_name)
    name_parts_score = check_name_parts_match(adc_name, mazooka_name)
    prefix_suffix_score = check_with_prefix_suffix_removal(adc_name, mazooka_name)

    # Check word count - if different, be more cautious
    adc_word_count = len(str(adc_name).split())
    mazooka_word_count = len(str(mazooka_name).split())

    word_count_difference = abs(adc_word_count - mazooka_word_count)

    # Penalize mismatched word counts unless another method gives high score
    if word_count_difference > 1:
        similarity_score *= (1 - 0.1 * min(word_count_difference, 3))

    # Special case: Check for common but unrelated short artist names
    short_match_penalty = 1.0
    if (len(str(adc_name)) <= 5 or len(str(mazooka_name)) <= 5) and similarity_score < 0.9:
        short_match_penalty = 0.7  # Penalize short name matches

    # Calculate final score with more stringent logic

    # 1. If any specialized method gives a very high score (>0.9), trust it
    high_scores = [s for s in [slash_score, band_score, name_parts_score, prefix_suffix_score] if s > 0.9]
    if high_scores:
        return max(high_scores)

    # 2. For names that are very different lengths, be suspicious of matches
    len_ratio = min(len(str(adc_name)), len(str(mazooka_name))) / max(len(str(adc_name)), len(str(mazooka_name)))

    # Strict length ratio check
    if len_ratio < 0.6:
        # For significant length differences, require higher score from specialized methods
        specialized_score = max(slash_score, band_score, name_parts_score, prefix_suffix_score)
        if specialized_score < 0.7:  # If no specialized method gives good score for different lengths
            return similarity_score * 0.7  # Heavily discount general similarity

    # 3. Check for minimum character match (to avoid "MIL" matching "MILES" to "MILITARY")
    min_length = min(len(str(adc_name)), len(str(mazooka_name)))

    # Require longer common substrings for longer names
    min_match_required = min(4, max(3, min_length // 3))

    # Find longest common substring
    def longest_common_substring(s1, s2):
        s1, s2 = str(s1).upper(), str(s2).upper()
        longest = ""
        for i in range(len(s1)):
            for length in range(1, len(s1) - i + 1):
                substring = s1[i:i + length]
                if substring in s2 and len(substring) > len(longest):
                    longest = substring
        return longest

    longest_common = longest_common_substring(str(adc_name), str(mazooka_name))

    # If longest common substring is too short, reduce score
    if len(longest_common.strip()) < min_match_required:
        similarity_score *= 0.5  # Significant reduction for minimal substring match

    # 4. Check for common words that might cause false positives
    common_words = ["THE", "BAND", "LIVE", "MUSIC", "SOUND", "BOYS", "GIRLS", "REMIX",
                    "ORCHESTRA", "ENSEMBLE", "QUINTET", "GROUP", "DJ", "MC"]

    adc_words = set(str(adc_name).upper().split())
    mazooka_words = set(str(mazooka_name).upper().split())

    # If the only overlap is common words, reduce score
    common_overlap = adc_words.intersection(mazooka_words).intersection(common_words)
    meaningful_overlap = adc_words.intersection(mazooka_words).difference(common_words)

    if common_overlap and not meaningful_overlap:
        similarity_score *= 0.4  # Heavy penalty for only matching common words

    # 5. Combine scores with a weighted approach, preferring specialized methods
    if similarity_score > 0.85:  # High basic similarity
        return similarity_score
    else:
        # Take the best score from specialized methods, but with stricter threshold
        specialized_score = max(slash_score, band_score, name_parts_score, prefix_suffix_score)

        # Average with basic similarity to prevent outliers
        combined_score = (specialized_score * 0.7 + similarity_score * 0.3) * short_match_penalty

        # Ensure score makes sense in context of the names
        final_score = min(combined_score, 0.95)  # Cap at 0.95 unless exact match

        # Apply final threshold to prevent low-quality matches
        return round(final_score, 2) if final_score >= 0.5 else similarity_score


# New optimized function to match artists with ISWC indexing
def match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6):
    print("Starting artist matching with ISWC indexing...")

    # Convert to pandas for processing
    adc_pandas = adc_df.to_pandas()
    mazooka_pandas = mazooka_df.to_pandas()

    # Clean artist names in pandas
    print("Cleaning artist names...")
    adc_pandas['CLEAN_NAME'] = adc_pandas['NAME'].apply(clean_artist_name)
    mazooka_pandas['CLEAN_ARTIST_NAME'] = mazooka_pandas['ARTIST_NAME'].apply(clean_artist_name)

    # Group by ISWC to create indexes for faster matching
    print("Creating ISWC indexes...")
    adc_by_iswc = {}
    mazooka_by_iswc = {}

    # Create ADC index by ISWC
    for _, row in adc_pandas.iterrows():
        iswc = row.get('ISWC')
        if iswc and not pd.isna(iswc):
            if iswc not in adc_by_iswc:
                adc_by_iswc[iswc] = []
            adc_by_iswc[iswc].append(row)

    # Create Mazooka index by ISWC
    for _, row in mazooka_pandas.iterrows():
        iswc = row.get('ISWC')
        if iswc and not pd.isna(iswc):
            if iswc not in mazooka_by_iswc:
                mazooka_by_iswc[iswc] = []
            mazooka_by_iswc[iswc].append(row)

    # List of all unique ISWCs that appear in both datasets
    common_iswcs = set(adc_by_iswc.keys()).intersection(set(mazooka_by_iswc.keys()))
    print(f"Found {len(common_iswcs)} common ISWCs between datasets")

    # Track matched Mazooka artists to prevent duplicates
    matched_mazooka_artists = set()
    results = []

    # Process each common ISWC
    total_iswcs = len(common_iswcs)
    for idx, iswc in enumerate(common_iswcs):
        if idx % 100 == 0:
            print(f"Processing ISWC {idx + 1}/{total_iswcs} ({round((idx + 1) / total_iswcs * 100)}%)")

        adc_artists = adc_by_iswc[iswc]
        mazooka_artists = mazooka_by_iswc[iswc]

        # For each ADC artist, find best Mazooka match within same ISWC
        for adc_row in adc_artists:
            adc_name = adc_row['CLEAN_NAME']
            adc_original_name = adc_row['NAME']
            best_match = None
            best_score = 0

            # First check for exact matches
            exact_matches = [m for m in mazooka_artists
                             if m['CLEAN_ARTIST_NAME'].upper() == adc_name.upper()
                             and m['ARTIST_NAME'] not in matched_mazooka_artists]

            if exact_matches:
                best_match = exact_matches[0]
                best_score = 1.0
            else:
                # Compare with all Mazooka artists for this ISWC
                for mazooka_row in mazooka_artists:
                    # Skip already matched artists
                    if mazooka_row['ARTIST_NAME'] in matched_mazooka_artists:
                        continue

                    mazooka_name = mazooka_row['CLEAN_ARTIST_NAME']

                    # Use comprehensive matching algorithm
                    score = comprehensive_match_score(adc_name, mazooka_name)

                    # Keep track of the best match
                    if score > best_score:
                        best_score = score
                        best_match = mazooka_row

            # If we found a match with a good score
            if best_match is not None and best_score >= match_threshold:
                matched_mazooka_artists.add(best_match['ARTIST_NAME'])

                results.append({
                    'ADC_ARTIST_ID': adc_row.get('ADC_ARTIST_ID', None),
                    'APRA_WORK_ID': adc_row.get('APRA_WORK_ID', None),
                    'APRA_ARTIST_ID': adc_row.get('APRA_ARTIST_ID', None),
                    'ADC_ARTIST_NAME': adc_original_name,
                    'MAZOOKA_ARTIST_NAME': best_match['ARTIST_NAME'].upper(),
                    'MATCH_SCORE': best_score,
                    'RECORDINGS_ID': best_match.get('RECORDINGS_ID', None),
                    'ISRC': best_match.get('ISRC', None),
                    'ISWC': iswc
                })

    # For ADC artists without ISWC matches, still try to match by name
    # First, collect ADC artists without ISWC matches
    adc_without_iswc = []
    for _, row in adc_pandas.iterrows():
        iswc = row.get('ISWC')
        if not iswc or pd.isna(iswc) or iswc not in common_iswcs:
            adc_without_iswc.append(row)

    # Now process these remaining artists in batches
    if adc_without_iswc:
        print(f"Processing {len(adc_without_iswc)} ADC artists without ISWC matches...")
        batch_size = 500
        for i in range(0, len(adc_without_iswc), batch_size):
            batch = adc_without_iswc[i:i + batch_size]

            for adc_row in batch:
                adc_name = adc_row['CLEAN_NAME']
                adc_original_name = adc_row['NAME']
                best_match = None
                best_score = 0

                # Filter potential matches by name characteristics for efficiency
                if len(adc_name) > 2:
                    adc_len = len(adc_name)
                    first_char = adc_name[0].upper() if adc_name else ''

                    # Filter by length and first character
                    potential_matches = [
                        m for m in mazooka_pandas.to_dict('records')
                        if m['ARTIST_NAME'] not in matched_mazooka_artists
                           and abs(len(m['CLEAN_ARTIST_NAME']) - adc_len) <= 5
                           and (not first_char or (
                                    m['CLEAN_ARTIST_NAME'] and m['CLEAN_ARTIST_NAME'][0].upper() == first_char))
                    ]

                    # Limit potential matches
                    potential_matches = potential_matches[:200] if len(potential_matches) > 200 else potential_matches
                else:
                    potential_matches = [
                                            m for m in mazooka_pandas.to_dict('records')
                                            if m['ARTIST_NAME'] not in matched_mazooka_artists
                                        ][:100]  # Limit for very short names

                # Find best match
                for mazooka_row in potential_matches:
                    mazooka_name = mazooka_row['CLEAN_ARTIST_NAME']
                    score = comprehensive_match_score(adc_name, mazooka_name)

                    if score > best_score:
                        best_score = score
                        best_match = mazooka_row

                # If we found a good match
                if best_match is not None and best_score >= match_threshold:
                    matched_mazooka_artists.add(best_match['ARTIST_NAME'])

                    results.append({
                        'ADC_ARTIST_ID': adc_row.get('ADC_ARTIST_ID', None),
                        'APRA_WORK_ID': adc_row.get('APRA_WORK_ID', None),
                        'APRA_ARTIST_ID': adc_row.get('APRA_ARTIST_ID', None),
                        'ADC_ARTIST_NAME': adc_original_name,
                        'MAZOOKA_ARTIST_NAME': best_match['ARTIST_NAME'].upper(),
                        'MATCH_SCORE': best_score,
                        'RECORDINGS_ID': best_match.get('RECORDINGS_ID', None),
                        'ISRC': best_match.get('ISRC', None),
                        'ISWC': best_match.get('ISWC', None)
                    })

            progress = min(100, round((i + len(batch)) / len(adc_without_iswc) * 100))
            print(f"Processed non-ISWC artists: {progress}%")

    # Create DataFrame from results
    if not results:
        print("No matches found that meet the threshold criteria.")
        results_df_pandas = pd.DataFrame(columns=[
            'ADC_ARTIST_ID', 'APRA_WORK_ID', 'APRA_ARTIST_ID', 'ADC_ARTIST_NAME',
            'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'RECORDINGS_ID', 'ISRC', 'ISWC'
        ])
    else:
        results_df_pandas = pd.DataFrame(results)

    # Convert back to Snowpark DataFrame
    results_df = session.create_dataframe(results_df_pandas)

    return results_df


# Function to run with example data
def run_with_examples(session):
    print("Running with example data...")

    # Create example DataFrames with actual ID columns to match your view definitions
    adc_examples = pd.DataFrame({
        'ADC_ARTIST_ID': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12', 'A13', 'A14',
                          'A15'],
        'APRA_WORK_ID': ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10', 'W11', 'W12', 'W13', 'W14',
                         'W15'],
        'APRA_ARTIST_ID': ['PA1', 'PA2', 'PA3', 'PA4', 'PA5', 'PA6', 'PA7', 'PA8', 'PA9', 'PA10', 'PA11', 'PA12',
                           'PA13', 'PA14', 'PA15'],
        'NAME': [
            'JESSICA MAUBOY',
            'MUNGO JERRY',
            'QUINCY JONES',
            'THE UPSETTERS',
            'COUNT BASIE / ROY ELDRIDGE',
            'COUNT BASEE',
            'SONNY STITT',
            'GUNS N\'ROSES',
            'BARBARO \'EL URBANO\' VARGAS',
            'RIVER YARRA',
            'KEELY SMITH',
            'MILITARY BAND',
            'MICHAL DWORZYNSKI',
            'FREDDIE HUBBARD',
            'COSHA'
        ],
        'TITLE': ['Song 1', 'Song 2', 'Song 3', 'Song 4', 'Song 5', 'Song 6', 'Song 7', 'Song 8', 'Song 9', 'Song 10',
                  'Song 11', 'Song 12', 'Song 13', 'Song 14', 'Song 15'],
        'ALBUM_NAME': ['Album 1', 'Album 2', 'Album 3', 'Album 4', 'Album 5', 'Album 6', 'Album 7', 'Album 8',
                       'Album 9', 'Album 10', 'Album 11', 'Album 12', 'Album 13', 'Album 14', 'Album 15'],
        'STATUS': ['Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active',
                   'Active', 'Active', 'Active', 'Active', 'Active']
    })

    mazooka_examples = pd.DataFrame({
        'RECORDINGS_ID': ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14',
                          'R15'],
        'TRACK_ID': ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12', 'T13', 'T14', 'T15'],
        'ISRC': ['ISRC1', 'ISRC2', 'ISRC3', 'ISRC4', 'ISRC5', 'ISRC6', 'ISRC7', 'ISRC8', 'ISRC9', 'ISRC10', 'ISRC11',
                 'ISRC12', 'ISRC13', 'ISRC14', 'ISRC15'],
        'ISWC': ['ISWC1', 'ISWC2', 'ISWC3', 'ISWC4', 'ISWC5', 'ISWC6', 'ISWC7', 'ISWC8', 'ISWC9', 'ISWC10', 'ISWC11',
                 'ISWC12', 'ISWC13', 'ISWC14', 'ISWC15'],
        'ARTIST_NAME': [
            'JESSICA MAUBOY',
            'MUNGO JERRY',
            'QUINCY JONES & THE BAND',
            'UPSETTERS',
            'COUNT BASIE / ROY ELDRIDGE',
            'COUNT BASIE',
            'SONSAX',
            'GUNSHIP / Martin Grech',
            'BARBARA LYNN',
            'RIVRS',
            'KEEP CALM...',
            'MILES BONNY',
            'MICHAEL ROSE',
            'FREDDY FENDER',
            'COSTUME'
        ]})
    # Convert pandas to Snowpark dataframes
    adc_df = session.create_dataframe(adc_examples)
    mazooka_df = session.create_dataframe(mazooka_examples)

    # Run matching on example data with appropriate threshold
    results_df = match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6)

    # Convert to pandas for analysis
    results_pandas = results_df.to_pandas()

    # Get distinct combinations of ADC artist name, ADC work ID, Mazooka artist name, Match score, and ISWC
    distinct_results = results_pandas.drop_duplicates(
        subset=['ADC_ARTIST_NAME', 'APRA_WORK_ID', 'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'ISWC']
    )

    # Calculate match quality statistics on distinct results
    if not distinct_results.empty:
        match_counts = distinct_results['MATCH_SCORE'].apply(lambda x: 'High (0.9-1.0)' if x >= 0.9 else
        ('Medium (0.7-0.9)' if x >= 0.7 else
         'Low (0.5-0.7)')).value_counts()

        print("\nMatching Results Summary:")
        print(f"Total distinct matches: {len(distinct_results)}")
        print(f"Match quality distribution:\n{match_counts}")

        # Display the distinct results
        result_columns = ['ADC_ARTIST_NAME', 'APRA_WORK_ID', 'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'ISWC']
        result_summary = distinct_results[result_columns].sort_values(by='MATCH_SCORE', ascending=False)
        print("\nSample of matching results (sorted by score):")
        print(result_summary)

        # Save distinct results to table
        output_table = "EXAMPLE_ARTIST_MATCHING_RESULTS_DISTINCT"
        distinct_results_df = session.create_dataframe(distinct_results)
        distinct_results_df.write.mode("overwrite").save_as_table(output_table)
        print(f"Distinct results saved to table {output_table}")
    else:
        print("No matches found that meet the threshold criteria.")

    return distinct_results if not distinct_results.empty else None


# Function to read from Snowflake tables
def read_snowflake_tables(session, adc_table, mazooka_table):
    print(f"Reading ADC artists from {adc_table}...")
    adc_df = session.table(adc_table)

    print(f"Reading Mazooka artists from {mazooka_table}...")
    mazooka_df = session.table(mazooka_table)

    # Ensure required columns exist
    required_adc_cols = ['NAME', 'ADC_ARTIST_ID', 'APRA_WORK_ID', 'APRA_ARTIST_ID', 'ISWC']
    required_mazooka_cols = ['ARTIST_NAME', 'RECORDINGS_ID', 'ISRC', 'ISWC']

    adc_cols = [col.upper() for col in adc_df.columns]
    mazooka_cols = [col.upper() for col in mazooka_df.columns]

    missing_adc_cols = [col for col in required_adc_cols if col not in adc_cols]
    missing_mazooka_cols = [col for col in required_mazooka_cols if col not in mazooka_cols]

    if missing_adc_cols:
        raise ValueError(f"ADC table missing required columns: {missing_adc_cols}")
    if missing_mazooka_cols:
        raise ValueError(f"Mazooka table missing required columns: {missing_mazooka_cols}")

    return adc_df, mazooka_df


def main():
    # Create Snowpark session
    session = Session.builder.getOrCreate()

    # Choose the running mode
    # exmpl data
    # mode = "example"

    # sample subset
    mode = "subset"

    # full dataset
    # mode = "full"

    if mode == "example":
        print("Running with EXAMPLE data...")
        run_with_examples(session)

    elif mode == "subset":
        print("Running with SUBSET of Snowflake data")
        adc_table = "EDW_APPS.MATCHING.ADC_ARTISTS_REMATCHED_ISWC_VW"  # Updated to use rematched views
        mazooka_table = "EDW_APPS.MATCHING.MAZOOKA_RECORDINGS_REMATCHED_ISWC_VW"  # Updated to use rematched views
        output_table = "EDW_APPS.MATCHING.ARTIST_MATCHING_RESULTS_SUBSET_DISTINCT"
        sample_percentage = 2

        # Read from Snowflake tables
        adc_df, mazooka_df = read_snowflake_tables(session, adc_table, mazooka_table)

        # Apply sampling
        print(f"Testing on {sample_percentage}% of the data...")
        adc_count = adc_df.count()
        adc_sample_size = int(adc_count * sample_percentage / 100)
        adc_df = adc_df.sample(n=min(adc_sample_size, adc_count))

        print(f"Data size: {adc_df.count()} ADC artists and {mazooka_df.count()} Mazooka artists")

        # Process matching with improved ISWC-based indexing method
        results_df = match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6)

        # Convert to pandas for analysis
        results_pandas = results_df.to_pandas()

        # Get distinct combinations of ADC artist name, ADC work ID, Mazooka artist name, Match score, and ISWC
        if not results_pandas.empty:
            distinct_results = results_pandas.drop_duplicates(
                subset=['ADC_ARTIST_NAME', 'APRA_WORK_ID', 'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'ISWC']
            )

            # Calculate match quality statistics on distinct results
            match_counts = distinct_results['MATCH_SCORE'].apply(lambda x: 'High (0.9-1.0)' if x >= 0.9 else
            ('Medium (0.7-0.9)' if x >= 0.7 else
             'Low (0.5-0.7)')).value_counts()

            print("\nMatching Results Summary:")
            print(f"Total distinct matches: {len(distinct_results)}")
            print(f"Match quality distribution:\n{match_counts}")

            # Save distinct results to Snowflake table
            distinct_results_df = session.create_dataframe(distinct_results)
            distinct_results_df.write.mode("overwrite").save_as_table(output_table)
            print(f"Distinct results saved to table {output_table}")

            # Display sample of distinct results
            result_columns = ['ADC_ARTIST_NAME', 'APRA_WORK_ID', 'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'ISWC']
            result_summary = distinct_results[result_columns].sort_values(by='MATCH_SCORE', ascending=False)
            print("Sample of distinct matching results (sorted by score):")
            print(result_summary.head(10))
        else:
            print("No matches found that meet the threshold criteria.")

    elif mode == "full":
        # Run with full dataset from Snowflake tables
        print("Running with FULL Snowflake dataset...")
        adc_table = "EDW_APPS.MATCHING.ADC_ARTISTS_REMATCHED_ISWC_VW"  # Updated to use rematched views
        mazooka_table = "EDW_APPS.MATCHING.MAZOOKA_RECORDINGS_REMATCHED_ISWC_VW"  # Updated to use rematched views
        output_table = "EDW_APPS.MATCHING.ARTIST_MATCHING_RESULTS_FULL_DISTINCT"

        # Read from Snowflake tables
        adc_df, mazooka_df = read_snowflake_tables(session, adc_table, mazooka_table)

        print(f"Processing the entire dataset...")
        print(f"Data size: {adc_df.count()} ADC artists and {mazooka_df.count()} Mazooka artists")

        # Process matching with improved ISWC-based indexing method
        results_df = match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6)

        # Convert to pandas for analysis
        results_pandas = results_df.to_pandas()

        # Get distinct combinations of ADC artist name, ADC work ID, Mazooka artist name, Match score, and ISWC
        if not results_pandas.empty:
            distinct_results = results_pandas.drop_duplicates(
                subset=['ADC_ARTIST_NAME', 'APRA_WORK_ID', 'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'ISWC']
            )

            # Calculate match quality statistics on distinct results
            match_counts = distinct_results['MATCH_SCORE'].apply(lambda x: 'High (0.9-1.0)' if x >= 0.9 else
            ('Medium (0.7-0.9)' if x >= 0.7 else
             'Low (0.5-0.7)')).value_counts()

            print("\nMatching Results Summary:")
            print(f"Total distinct matches: {len(distinct_results)}")
            print(f"Match quality distribution:\n{match_counts}")

            # Save distinct results to Snowflake table
            distinct_results_df = session.create_dataframe(distinct_results)
            distinct_results_df.write.mode("overwrite").save_as_table(output_table)
            print(f"Distinct results saved to table {output_table}")

            # Display sample of distinct results
            result_columns = ['ADC_ARTIST_NAME', 'APRA_WORK_ID', 'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'ISWC']
            result_summary = distinct_results[result_columns].sort_values(by='MATCH_SCORE', ascending=False)
            print("Sample of distinct matching results (sorted by score):")
            print(result_summary.head(10))
        else:
            print("No matches found that meet the threshold criteria.")
    else:
        print(f"Invalid mode: {mode}. Please use 'example', 'subset', or 'full'.")

    # Close the session
    session.close()


if __name__ == "__main__":
    main()

