import re
import difflib
import pandas as pd
import numpy as np
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit, regexp_replace, upper, trim, when


def clean_artist_name(name):
    if name is None or pd.isna(name):
        return ""

    # First, preserve spaces around special characters by replacing them with spaces
    name_with_spaces = re.sub(r'[\'"`\-_&+]', ' ', str(name))

    # Then remove remaining non-alphanumeric characters (except spaces)
    cleaned = re.sub(r'[^a-zA-Z0-9 ]', '', name_with_spaces)

    # Normalize spaces (convert multiple spaces to single space)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # If the result is just spaces, return the original name
    if cleaned.strip() == "":
        return str(name)

    return cleaned.strip()


def match_with_delimiter_handling(adc_name, mazooka_name):
    if not adc_name or not mazooka_name:
        return 0

    # Store original names for logging (if needed)
    adc_original = str(adc_name).strip()
    mazooka_original = str(mazooka_name).strip()

    # Clean and normalize inputs - uppercase and trim
    adc_upper = adc_original.upper()
    mazooka_upper = mazooka_original.upper()

    # Define delimiters to check
    delimiters = ['|', '/', '#', '\\', ',', ';']

    # ENHANCED APPROACH: Check for exact matching parts regardless of delimiter and order
    adc_has_delimiters = any(d in adc_upper for d in delimiters)
    mazooka_has_delimiters = any(d in mazooka_upper for d in delimiters)

    # Word-level exact matching regardless of order
    # First, clean special characters from both names
    adc_spaced = re.sub(r'[\'"`\-_&+]+', ' ', adc_upper)
    mazooka_spaced = re.sub(r'[\'"`\-_&+]+', ' ', mazooka_upper)

    # Remove remaining non-alphanumeric characters
    adc_clean = re.sub(r'[^a-zA-Z0-9 ]', '', adc_spaced).strip()
    mazooka_clean = re.sub(r'[^a-zA-Z0-9 ]', '', mazooka_spaced).strip()

    # Normalize spaces
    adc_clean = re.sub(r'\s+', ' ', adc_clean)
    mazooka_clean = re.sub(r'\s+', ' ', mazooka_clean)

    # Split into words and sort
    adc_words = sorted([w for w in adc_clean.split() if w])
    mazooka_words = sorted([w for w in mazooka_clean.split() if w])

    # Check for exact word match (regardless of order)
    if adc_words == mazooka_words and len(adc_words) > 0:
        return 1.0  # Exact word match score

    # If either string has a delimiter, perform special handling
    if adc_has_delimiters or mazooka_has_delimiters:
        # Normalize all delimiters to '|' for both strings
        adc_normalized = adc_upper
        mazooka_normalized = mazooka_upper

        for d in delimiters:
            adc_normalized = adc_normalized.replace(d, '|')
            mazooka_normalized = mazooka_normalized.replace(d, '|')

        # Split by the normalized delimiter and strip each part
        adc_parts = [part.strip() for part in adc_normalized.split('|') if part.strip()]
        mazooka_parts = [part.strip() for part in mazooka_normalized.split('|') if part.strip()]

        # Sort the parts to ensure order doesn't matter
        adc_parts_sorted = sorted(adc_parts)
        mazooka_parts_sorted = sorted(mazooka_parts)

        # Check if the sorted parts are identical
        if adc_parts_sorted == mazooka_parts_sorted:
            return 1.0  # Perfect match if sorted parts are identical

        # Check if either string is a subset of the other's parts
        if all(part in mazooka_parts for part in adc_parts) or all(part in adc_parts for part in mazooka_parts):
            return 1.0  # Perfect match if one is a subset of the other

        # Check each part against the full other string or its parts
        if adc_has_delimiters:
            for part in adc_parts:
                # Check against full mazooka name
                if part == mazooka_upper:
                    return 1.0

                # Check against any mazooka part if mazooka also has delimiters
                if mazooka_has_delimiters and part in mazooka_parts:
                    return 1.0

                # NEW: Check part against mazooka name words
                part_words = sorted([w for w in re.sub(r'[^a-zA-Z0-9 ]', '',
                                                       re.sub(r'[\'"`\-_&+]+', ' ', part)).split() if w])
                if part_words == mazooka_words:
                    return 1.0

        if mazooka_has_delimiters:
            for part in mazooka_parts:
                # Check against full adc name
                if part == adc_upper:
                    return 1.0

                # NEW: Check part against adc name words
                part_words = sorted([w for w in re.sub(r'[^a-zA-Z0-9 ]', '',
                                                       re.sub(r'[\'"`\-_&+]+', ' ', part)).split() if w])
                if part_words == adc_words:
                    return 1.0

    # APPROACH 1: First try direct split and comparison before any cleaning
    if any(d in adc_upper for d in delimiters):
        normalized_adc = adc_upper
        for d in delimiters:
            normalized_adc = normalized_adc.replace(d, '|')

        # Split by the normalized delimiter and strip each part
        split_parts = [part.strip() for part in normalized_adc.split('|')]
        split_parts = [part for part in split_parts if part]  # Remove empty parts

        # Check each part directly against the Mazooka name
        for part in split_parts:
            if part.strip() == mazooka_upper:
                return 1.0  # EXIT EARLY with perfect score if any split part matches exactly

            # NEW: Check part words against mazooka words
            part_clean = re.sub(r'[^a-zA-Z0-9 ]', '', re.sub(r'[\'"`\-_&+]+', ' ', part)).strip()
            part_words = sorted([w for w in part_clean.split() if w])
            if part_words == mazooka_words:
                return 1.0

    # APPROACH 2: Standard processing
    # Replace common special characters with spaces first (preserves structure)
    adc_spaced = re.sub(r'[\'"`\-_&+]', ' ', adc_upper)
    mazooka_spaced = re.sub(r'[\'"`\-_&+]', ' ', mazooka_upper)

    # Then clean remaining non-alphanumeric characters
    adc_clean_spaced = re.sub(r'[^a-zA-Z0-9 ]', '', adc_spaced).strip()
    mazooka_clean_spaced = re.sub(r'[^a-zA-Z0-9 ]', '', mazooka_spaced).strip()

    # Normalize spaces (convert multiple spaces to single space)
    adc_clean_spaced = re.sub(r'\s+', ' ', adc_clean_spaced)
    mazooka_clean_spaced = re.sub(r'\s+', ' ', mazooka_clean_spaced)

    # Also try direct removal of special characters
    adc_clean_direct = re.sub(r'[^a-zA-Z0-9 ]', '', adc_upper).strip()
    mazooka_clean_direct = re.sub(r'[^a-zA-Z0-9 ]', '', mazooka_upper).strip()

    # Normalize spaces for direct method too
    adc_clean_direct = re.sub(r'\s+', ' ', adc_clean_direct)
    mazooka_clean_direct = re.sub(r'\s+', ' ', mazooka_clean_direct)

    # Check exact match using both cleaning approaches
    if adc_clean_direct == mazooka_clean_direct or adc_clean_spaced == mazooka_clean_spaced:
        return 1.0

    # IMPROVED: Check for name reversal - for both full names and individual words
    adc_words = adc_clean_direct.split()
    mazooka_words = mazooka_clean_direct.split()

    # NEW: Sorted word comparison (order doesn't matter)
    if sorted(adc_words) == sorted(mazooka_words) and len(adc_words) > 0:
        return 1.0  # Exact match if words are the same regardless of order

    # First check exact word reversal (e.g., "WILLIAMS ROBBIE" vs "ROBBIE WILLIAMS")
    if len(adc_words) > 1 and len(mazooka_words) > 1:
        adc_reversed = ' '.join(reversed(adc_words))
        if adc_reversed == mazooka_clean_direct:
            return 0.95  # Almost perfect score for exact name reversal (kept for compatibility)

    # Handle "THE" prefix removal for exact matching
    adc_no_the = adc_clean_direct[4:] if adc_clean_direct.startswith("THE ") else adc_clean_direct
    mazooka_no_the = mazooka_clean_direct[4:] if mazooka_clean_direct.startswith("THE ") else mazooka_clean_direct

    if adc_no_the == mazooka_no_the and len(adc_no_the) > 3:
        return 1.0  # Perfect score for matches after "THE" removal

    # Check for first/last name reversed matches - keep this for compatibility
    if len(adc_words) > 0 and len(mazooka_words) > 0:
        # Check if all words in both names match regardless of order
        if sorted(adc_words) == sorted(mazooka_words):
            return 0.95  # This line is now redundant with our new logic, but kept for compatibility

    # IMPROVED: Check for misspellings - calculate character-level similarity within words
    if len(adc_words) == len(mazooka_words):
        # For each corresponding word pair, calculate similarity
        total_similarity = 0
        word_match_count = 0

        # Try matching in original order
        for i in range(len(adc_words)):
            if i < len(mazooka_words):
                word_similarity = difflib.SequenceMatcher(None, adc_words[i], mazooka_words[i]).ratio()
                if word_similarity > 0.7:  # High threshold for word similarity
                    total_similarity += word_similarity
                    word_match_count += 1

        # If we matched all words with high average similarity
        if word_match_count == len(adc_words) and total_similarity / len(adc_words) > 0.8:
            return 0.9  # High score for misspelled but similar words

        # If order didn't work well, try reversed order for better matching
        if len(adc_words) == 2 and len(mazooka_words) == 2:  # Common case: First/Last name
            # Check for swapped words with misspellings
            reverse_similarity_1 = difflib.SequenceMatcher(None, adc_words[0], mazooka_words[1]).ratio()
            reverse_similarity_2 = difflib.SequenceMatcher(None, adc_words[1], mazooka_words[0]).ratio()

            # If both reversed words have high similarity
            if reverse_similarity_1 > 0.7 and reverse_similarity_2 > 0.7:
                avg_similarity = (reverse_similarity_1 + reverse_similarity_2) / 2
                # Scale 0.7-1.0 to 0.8-0.95
                scaled_score = 0.8 + (avg_similarity - 0.7) * 0.5  # Max would be 0.95
                return scaled_score

    # APPROACH 3: Advanced delimiter handling with clean data (ENHANCED)
    # Also try with cleaned versions of the parts
    if any(d in adc_upper for d in delimiters):
        normalized_adc = adc_upper
        for d in delimiters:
            normalized_adc = normalized_adc.replace(d, '|')

        # Split by the normalized delimiter and process each part
        split_parts = [part.strip() for part in normalized_adc.split('|')]
        split_parts = [part for part in split_parts if part]  # Remove empty parts

        # Clean each part for comparison
        for part in split_parts:
            # Clean the part just like we cleaned the full names
            part_spaced = re.sub(r'[\'"`\-_&+]', ' ', part)
            part_clean = re.sub(r'[^a-zA-Z0-9 ]', '', part_spaced).strip()
            part_clean = re.sub(r'\s+', ' ', part_clean)

            # Try comparing cleaned part with cleaned Mazooka name
            if part_clean == mazooka_clean_direct:
                return 1.0

            # Also try with "THE" removed
            part_no_the = part_clean[4:] if part_clean.startswith("THE ") else part_clean
            if part_no_the == mazooka_no_the and len(part_no_the) > 3:
                return 1.0

            # NEW: Check part words against mazooka words
            part_words = sorted([w for w in part_clean.split() if w])
            if part_words == sorted(mazooka_clean_direct.split()):
                return 1.0

    # APPROACH 4: Also try matching Mazooka name against each word-permutation of the split parts
    if any(d in adc_upper for d in delimiters):
        normalized_adc = adc_upper
        for d in delimiters:
            normalized_adc = normalized_adc.replace(d, '|')

        # Split and clean each part
        cleaned_parts = []
        for part in [p.strip() for p in normalized_adc.split('|') if p.strip()]:
            part_spaced = re.sub(r'[\'"`\-_&+]', ' ', part)
            part_clean = re.sub(r'[^a-zA-Z0-9 ]', '', part_spaced).strip()
            part_clean = re.sub(r'\s+', ' ', part_clean)
            if part_clean:
                cleaned_parts.append(part_clean)

        # Try all permutations (for handling cases like "ROY ELDRIDGE / COUNT BASIE" vs "BASIE COUNT")
        for part in cleaned_parts:
            part_words = part.split()
            if len(part_words) > 1:  # Only try permutations if there are multiple words
                # Try with words in reverse order
                reversed_part = ' '.join(reversed(part_words))
                if reversed_part == mazooka_clean_direct:
                    return 1.0

                # NEW: Try with sorted words comparison
                if sorted(part_words) == sorted(mazooka_clean_direct.split()):
                    return 1.0

    # APPROACH 5: Try with the cleaned COMBINED version
    # This combines all parts after cleaning into a single string
    if any(d in adc_upper for d in delimiters):
        normalized_adc = adc_upper
        for d in delimiters:
            normalized_adc = normalized_adc.replace(d, ' ')  # Replace ALL delimiters with spaces

        # Clean the combined string
        combined_clean = re.sub(r'[^a-zA-Z0-9 ]', '', normalized_adc).strip()
        combined_clean = re.sub(r'\s+', ' ', combined_clean)

        # Check if Mazooka name is an exact match to any part of the combined string
        if mazooka_clean_direct in combined_clean.split():
            return 1.0

        # Also check if mazooka name is a complete substring
        if mazooka_clean_direct in combined_clean:
            # If mazooka name is substantial portion of the combined string
            if len(mazooka_clean_direct) / len(combined_clean) > 0.7:
                return 1.0

        # NEW: Try matching with sorted word comparison
        combined_words = sorted([w for w in combined_clean.split() if w])
        mazooka_words = sorted([w for w in mazooka_clean_direct.split() if w])
        if combined_words == mazooka_words:
            return 1.0

    # Check for partial matches
    if adc_clean_spaced in mazooka_clean_spaced or mazooka_clean_spaced in adc_clean_spaced:
        # Calculate what percentage of the longer string is matched
        longer = max(len(adc_clean_spaced), len(mazooka_clean_spaced))
        shorter = min(len(adc_clean_spaced), len(mazooka_clean_spaced))

        if shorter / longer >= 0.7:  # If at least 70% of the longer string is matched
            return 0.9  # High score for substantial substring match
        else:
            # Calculate a proportional score
            match_ratio = shorter / longer
            # Ensure the score is between 0.5 and 0.7 for partial matches
            return 0.5 + (0.4 * match_ratio)

    # For other cases, use sequence matching for basic similarity
    similarity_score = difflib.SequenceMatcher(None, adc_clean_spaced, mazooka_clean_spaced).ratio()

    # Adjust to match examples like "QUINCY JONES" vs "QUINCY JONES & THE BAND"
    if similarity_score > 0.5:
        return round(similarity_score, 2)
    else:
        return 0


# Function to expand delimited ADC names with tracking of which part matched
def expand_adc_delimited_names(adc_pandas_df):
    """
    Expands rows with delimited artist names into multiple rows,
    one for each part of the delimited name.
    """
    expanded_rows = []

    # Define delimiters
    delimiters = ['|', '/', '#', '\\', ',', ';']

    for _, row in adc_pandas_df.iterrows():
        artist_name = row['NAME']

        # First add the original name row
        new_row = row.copy()
        new_row['IS_VARIANT'] = 'ORIGINAL'
        new_row['VARIANT_PART'] = None  # Track which part matched (None for full original)
        expanded_rows.append(new_row)

        # Check if artist name contains delimiters
        if any(d in str(artist_name) for d in delimiters):
            # Normalize delimiters
            artist_name_norm = str(artist_name)
            for d in delimiters:
                artist_name_norm = artist_name_norm.replace(d, '/')

            # Split and clean parts
            parts = [part.strip() for part in artist_name_norm.split('/')]

            # For each part, create a new row with the part as NAME
            for part in parts:
                if part and part != artist_name:
                    new_row = row.copy()
                    new_row['NAME'] = part
                    new_row['CLEAN_NAME'] = clean_artist_name(part)
                    new_row['IS_VARIANT'] = 'VARIANT'
                    new_row['VARIANT_PART'] = part  # Track which part was used
                    expanded_rows.append(new_row)

    # Convert back to a DataFrame
    expanded_df = pd.DataFrame(expanded_rows)
    return expanded_df


# Main function to match artists with ISWC indexing - cleaned up version
def match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6):
    print("Initiating artist name matching with ISWC indexing...")

    # Convert to pandas for processing
    adc_pandas = adc_df.to_pandas()
    mazooka_pandas = mazooka_df.to_pandas()

    # Clean artist names in pandas
    print("Cleaning artist names...")
    adc_pandas['CLEAN_NAME'] = adc_pandas['NAME'].apply(clean_artist_name)
    mazooka_pandas['CLEAN_ARTIST_NAME'] = mazooka_pandas['ARTIST_NAME'].apply(clean_artist_name)

    # Create expanded ADC dataframe with split names
    print("Expanding delimited ADC artist names...")
    expanded_adc = expand_adc_delimited_names(adc_pandas)
    print(f"Expanded ADC dataset from {len(adc_pandas)} to {len(expanded_adc)} rows after splitting delimited names")

    # Group by ISWC to create indexes for faster matching
    print("Creating ISWC indexes...")
    adc_by_iswc = {}
    mazooka_by_iswc = {}

    # Also track original ADC rows (non-expanded)
    original_adc_ids = set(adc_pandas['ADC_ARTIST_ID'])

    # Create ADC index by ISWC using expanded dataset
    for _, row in expanded_adc.iterrows():
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

    # Track matched to prevent duplicates
    matched_combinations = set()
    results = []

    # Also track the best match for each ADC artist ID
    best_matches = {}  # {ADC_ARTIST_ID: (score, result_dict)}

    # Define delimiters once, not in each loop
    delimiters = ['|', '/', '#', '\\', ',', ';']

    # Process each common ISWC
    total_iswcs = len(common_iswcs)
    for idx, iswc in enumerate(common_iswcs):
        if idx % 100 == 0:
            print(f"Processing ISWC {idx + 1}/{total_iswcs} ({round((idx + 1) / total_iswcs * 100)}%)")

        adc_artists = adc_by_iswc[iswc]
        mazooka_artists = mazooka_by_iswc[iswc]

        # For each ADC artist, find best Mazooka match within same ISWC
        for adc_row in adc_artists:
            adc_id = adc_row.get('ADC_ARTIST_ID')
            adc_original_name = adc_row['NAME']
            is_variant = adc_row['IS_VARIANT']
            variant_part = adc_row.get('VARIANT_PART')

            best_match = None
            best_score = 0

            # Try exact match first
            for mz_row in mazooka_artists:
                # Check if this combination has already been matched
                mz_id = mz_row.get('RECORDINGS_ID')
                if (adc_id, mz_id) in matched_combinations:
                    continue

                mz_name = mz_row['ARTIST_NAME']

                # Try exact match first (case insensitive)
                if adc_original_name is not None and mz_name is not None and str(adc_original_name).upper() == str(
                        mz_name).upper():
                    best_match = mz_row
                    best_score = 1.0
                    break

            # If no exact match, try using match_with_delimiter_handling
            if best_score < 1.0:
                for mz_row in mazooka_artists:
                    mz_id = mz_row.get('RECORDINGS_ID')
                    if (adc_id, mz_id) in matched_combinations:
                        continue

                    mz_name = mz_row['ARTIST_NAME']

                    # Try matching with our enhanced delimiter handling
                    score = match_with_delimiter_handling(adc_original_name, mz_name)

                    if score > best_score:
                        best_score = score
                        best_match = mz_row

            # If we found a good match
            if best_match is not None and best_score >= match_threshold:
                mz_id = best_match.get('RECORDINGS_ID')
                matched_combinations.add((adc_id, mz_id))

                # IMPORTANT: Check if we should mark this as VARIANT
                # When the original name contains delimiters and we match on a split part
                final_is_variant = is_variant

                # Get the original complete row for this ADC ID before splitting
                original_adc_rows = adc_pandas[adc_pandas['ADC_ARTIST_ID'] == adc_id]
                original_row = original_adc_rows.iloc[0] if not original_adc_rows.empty else None

                if original_row is not None:
                    original_name = original_row['NAME']
                    original_has_delimiters = any(d in str(original_name) for d in delimiters)

                    # Check if this matched on a variant part (not the whole string)
                    if original_has_delimiters:
                        # Check if the matching Mazooka name is one of the parts of the original
                        # (but not the full original)
                        if str(best_match['ARTIST_NAME']).upper() != str(original_name).upper():
                            # Normalize the original name for better comparison
                            normalized = str(original_name).upper()
                            for d in delimiters:
                                normalized = normalized.replace(d, '/')

                            # Get all the parts of the original name
                            parts = [p.strip() for p in normalized.split('/')]

                            # If the matched Mazooka name is similar to one of the parts
                            for part in parts:
                                if part and difflib.SequenceMatcher(None, part, str(
                                        best_match['ARTIST_NAME']).upper()).ratio() > 0.8:
                                    final_is_variant = 'VARIANT'  # Mark as variant if matched on a part
                                    break

                result_dict = {
                    'ADC_ARTIST_ID': adc_id,
                    'APRA_WORK_ID': adc_row.get('APRA_WORK_ID', None),
                    'APRA_ARTIST_ID': adc_row.get('APRA_ARTIST_ID', None),
                    'ADC_ARTIST_NAME': original_row['NAME'] if original_row is not None else adc_original_name,
                    'MAZOOKA_ARTIST_NAME': best_match['ARTIST_NAME'].upper(),
                    'MATCH_SCORE': best_score,
                    'RECORDINGS_ID': best_match.get('RECORDINGS_ID', None),
                    'ISRC': best_match.get('ISRC', None),
                    'ISWC': iswc,
                    'IS_VARIANT': final_is_variant
                }

                # If this is an original ADC entry, directly add it to results
                if is_variant == 'ORIGINAL':
                    results.append(result_dict)
                # If it's a variant, only keep the best match for each original ADC artist
                elif adc_id in original_adc_ids:
                    if adc_id not in best_matches or best_score > best_matches[adc_id][0]:
                        best_matches[adc_id] = (best_score, result_dict)

    # Add the best variant matches to results
    for adc_id, (score, result_dict) in best_matches.items():
        if adc_id not in [r['ADC_ARTIST_ID'] for r in results if r['IS_VARIANT'] == 'ORIGINAL']:
            results.append(result_dict)

    # Process artists without ISWC matches
    adc_without_iswc = []
    for _, row in adc_pandas.iterrows():
        iswc = row.get('ISWC')
        if not iswc or pd.isna(iswc) or iswc not in common_iswcs:
            adc_without_iswc.append(row)

    # Process these artists separately (similar logic as above)
    if adc_without_iswc:
        print(f"Processing {len(adc_without_iswc)} ADC artists without ISWC matches...")
        batch_size = 500
        for i in range(0, len(adc_without_iswc), batch_size):
            batch = adc_without_iswc[i:i + batch_size]

            for adc_row in batch:
                adc_id = adc_row.get('ADC_ARTIST_ID')
                adc_original_name = adc_row['NAME']

                best_match = None
                best_score = 0

                # Try exact matches first
                for _, mz_row in mazooka_pandas.iterrows():
                    mz_id = mz_row.get('RECORDINGS_ID')
                    if (adc_id, mz_id) in matched_combinations:
                        continue

                    mz_name = mz_row['ARTIST_NAME']

                    # Check for exact match
                    if adc_original_name is not None and mz_name is not None and str(adc_original_name).upper() == str(
                            mz_name).upper():
                        best_match = mz_row
                        best_score = 1.0
                        break

                # If no exact match, try special handling for delimited strings
                if best_score < 1.0 and any(d in str(adc_original_name) for d in delimiters):
                    for _, mz_row in mazooka_pandas.head(500).iterrows():  # Limit to first 500 for efficiency
                        mz_id = mz_row.get('RECORDINGS_ID')
                        if (adc_id, mz_id) in matched_combinations:
                            continue

                        mz_name = mz_row['ARTIST_NAME']
                        score = match_with_delimiter_handling(adc_original_name, mz_name)

                        if score > best_score:
                            best_score = score
                            best_match = mz_row

                # If no match yet, try approximate matching with a subset of candidates
                if best_score < 1.0:
                    # Limit potential matches to improve performance
                    potential_matches = mazooka_pandas.iloc[:300].to_dict('records')  # Adjust size as needed

                    for mz_row in potential_matches:
                        mz_id = mz_row.get('RECORDINGS_ID')
                        if (adc_id, mz_id) in matched_combinations:
                            continue

                        mz_clean_name = mz_row['CLEAN_ARTIST_NAME']
                        cleaned_adc_name = adc_row['CLEAN_NAME']
                        score = match_with_delimiter_handling(cleaned_adc_name, mz_clean_name)

                        if score > best_score:
                            best_score = score
                            best_match = mz_row

                # If we found a good match
                if best_match is not None and best_score >= match_threshold:
                    mz_id = best_match.get('RECORDINGS_ID')
                    matched_combinations.add((adc_id, mz_id))

                    results.append({
                        'ADC_ARTIST_ID': adc_id,
                        'APRA_WORK_ID': adc_row.get('APRA_WORK_ID', None),
                        'APRA_ARTIST_ID': adc_row.get('APRA_ARTIST_ID', None),
                        'ADC_ARTIST_NAME': adc_original_name,
                        'MAZOOKA_ARTIST_NAME': best_match['ARTIST_NAME'].upper(),
                        'MATCH_SCORE': best_score,
                        'RECORDINGS_ID': best_match.get('RECORDINGS_ID', None),
                        'ISRC': best_match.get('ISRC', None),
                        'ISWC': best_match.get('ISWC', None),
                        'IS_VARIANT': 'ORIGINAL'
                    })

            progress = min(100, round((i + len(batch)) / len(adc_without_iswc) * 100))
            print(f"Processed non-ISWC artists: {progress}%")

    # Create DataFrame from results
    if not results:
        print("No matches found that meet the threshold criteria.")
        results_df_pandas = pd.DataFrame(columns=[
            'ADC_ARTIST_ID', 'APRA_WORK_ID', 'APRA_ARTIST_ID', 'ADC_ARTIST_NAME',
            'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'RECORDINGS_ID', 'ISRC', 'ISWC',
            'IS_VARIANT'
        ])
    else:
        results_df_pandas = pd.DataFrame(results)

    # Convert back to Snowpark DataFrame
    results_df = session.create_dataframe(results_df_pandas)

    return results_df


def run_with_examples(session):
    print("Creating example data for testing...")

    # Create more intentional examples with better matched test cases
    adc_examples = pd.DataFrame({
        'ADC_ARTIST_ID': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10'],
        'APRA_WORK_ID': ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10'],
        'ISWC': ['ISWC1', 'ISWC2', 'ISWC3', 'ISWC4', 'ISWC5', 'ISWC6', 'ISWC7', 'ISWC8', 'ISWC9', 'ISWC10'],
        'APRA_ARTIST_ID': ['PA1', 'PA2', 'PA3', 'PA4', 'PA5', 'PA6', 'PA7', 'PA8', 'PA9', 'PA10'],
        'NAME': [
            'ROBBIE WILLIAMS / TAKE THAT',
            'JAMES TAYLOR|ALISON KRAUSS',
            'QUINCY JONES',
            'THE UPSETTERS',
            'COUNT BASIE / ROY ELDRIDGE',
            'COUNT BASEE',
            'TAKE THAT',
            'GUNS N\'ROSES',
            'MUNGO JERRY',
            'WILLIAMS ROBIIE'
        ]
    })

    mazooka_examples = pd.DataFrame({
        'RECORDINGS_ID': ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10'],
        'ISRC': ['ISRC1', 'ISRC2', 'ISRC3', 'ISRC4', 'ISRC5', 'ISRC6', 'ISRC7', 'ISRC8', 'ISRC9', 'ISRC10'],
        'ISWC': ['ISWC1', 'ISWC2', 'ISWC3', 'ISWC4', 'ISWC5', 'ISWC6', 'ISWC7', 'ISWC8', 'ISWC9', 'ISWC10'],
        'ARTIST_NAME': [
            'ROBBIE WILLIAMS',
            'ALISON KRAUSS / JAMES TAYLOR',
            'QUINCY JONES & THE BAND',
            'UPSETTERS',
            'ROY ELDRIDGE',
            'COUNT BASIE',
            'TAKE THAT',
            'GUNS N ROSES',
            'JERRY MUNGO',
            'ROBBIE WILLIAMS'
        ]
    })

    # Debug print the test data
    print("\nADC test data:")
    for i, row in adc_examples.iterrows():
        print(f"{row['ADC_ARTIST_ID']}: {row['NAME']} (ISWC: {row['ISWC']})")

    print("\nMazooka test data:")
    for i, row in mazooka_examples.iterrows():
        print(f"{row['RECORDINGS_ID']}: {row['ARTIST_NAME']} (ISWC: {row['ISWC']})")

    # Convert pandas to Snowpark dataframes
    adc_df = session.create_dataframe(adc_examples)
    mazooka_df = session.create_dataframe(mazooka_examples)

    print("\nRunning matching algorithm on test data...")

    # Run matching on example data with appropriate threshold
    # Use a lower threshold to ensure we capture more matches for demonstration purposes
    results_df = match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.5)

    # Convert to pandas for analysis and debugging
    results_pandas = results_df.to_pandas()

    print(f"\nRaw results count: {len(results_pandas)}")

    # For debugging: Print ALL raw results before deduplication
    print("\nRaw matching results:")
    for i, row in results_pandas.iterrows():
        print(
            f"ADC: {row['ADC_ARTIST_NAME']} → Mazooka: {row['MAZOOKA_ARTIST_NAME']} (Score: {row['MATCH_SCORE']:.2f}, Variant: {row['IS_VARIANT']})")

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

        # Ensure all required columns are present with correct types
        expected_columns = {
            'ADC_ARTIST_ID': 'VARCHAR(16777216)',
            'APRA_WORK_ID': 'VARCHAR(16777216)',
            'APRA_ARTIST_ID': 'VARCHAR(16777216)',
            'ADC_ARTIST_NAME': 'VARCHAR(16777216)',
            'MAZOOKA_ARTIST_NAME': 'VARCHAR(16777216)',
            'MATCH_SCORE': 'FLOAT',
            'RECORDINGS_ID': 'VARCHAR(16777216)',
            'ISRC': 'VARCHAR(16777216)',
            'ISWC': 'VARCHAR(16777216)',
            'IS_VARIANT': 'VARCHAR(16777216)'
        }

        # Check if any columns are missing and add them with NULL values
        for col in expected_columns:
            if col not in distinct_results.columns:
                distinct_results[col] = None

        # Save distinct results to table with specified column types
        output_table = "EXAMPLE_ARTIST_MATCHING_RESULTS"
        distinct_results_df = session.create_dataframe(distinct_results)

        # Create or replace table with explicit column types
        table_definition = ", ".join([f"{col} {dtype}" for col, dtype in expected_columns.items()])
        session.sql(f"CREATE OR REPLACE TABLE {output_table} ({table_definition})").collect()

        # Insert data into the table
        distinct_results_df.write.mode("append").save_as_table(output_table)
        print(f"\nDistinct results saved to table {output_table}")

        # Display all distinct results for the example data (small enough dataset)
        result_columns = ['ADC_ARTIST_NAME', 'APRA_WORK_ID', 'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'ISWC', 'IS_VARIANT']
        result_summary = distinct_results[result_columns].sort_values(by=['MATCH_SCORE', 'ADC_ARTIST_NAME'],
                                                                      ascending=[False, True])
        print("\nAll distinct matching results (sorted by score):")
        print(result_summary)

        # Print specific information about variant matches
        variants = distinct_results[distinct_results['IS_VARIANT'] == 'VARIANT']
        if not variants.empty:
            print("\nVariant matches (from expanded/split artists):")
            print(variants[result_columns])
        else:
            print("\nNo variant matches found. The delimiter expansion may not be working correctly.")

        # Check for expected matches that are missing
        expected_matches = [
            ("JAMES TAYLOR|ALISON KRAUSS", "ALISON KRAUSS / JAMES TAYLOR"),
            ("MUNGO JERRY", "JERRY MUNGO"),
            ("WILLIAMS ROBBIE", "ROBBIE WILLIAMS"),
            ("COUNT BASIE / ROY ELDRIDGE", "ROY ELDRIDGE")
        ]

        print("\nChecking for expected key matches:")
        for adc_name, mazooka_name in expected_matches:
            match = distinct_results[(distinct_results['ADC_ARTIST_NAME'] == adc_name) &
                                     (distinct_results['MAZOOKA_ARTIST_NAME'] == mazooka_name)]
            if len(match) > 0:
                print(f"✅ Found match: {adc_name} → {mazooka_name} (Score: {match['MATCH_SCORE'].values[0]:.2f})")
            else:
                variant_match = distinct_results[
                    (distinct_results['ADC_ARTIST_NAME'].str.contains(adc_name, regex=False)) &
                    (distinct_results['MAZOOKA_ARTIST_NAME'] == mazooka_name)]
                if len(variant_match) > 0:
                    print(
                        f"⚠️ Found variant match: {variant_match['ADC_ARTIST_NAME'].values[0]} → {mazooka_name} (Score: {variant_match['MATCH_SCORE'].values[0]:.2f})")
                else:
                    print(f"❌ Missing expected match: {adc_name} → {mazooka_name}")

    else:
        print("No matches found that meet the threshold criteria.")

    # Return results for further analysis if needed
    return results_pandas


def read_snowflake_tables(session, adc_table, mazooka_table):
    adc_df = session.table(adc_table)
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
    session = Session.builder.getOrCreate()

    # mode = "example"
    mode = "subset"
    # mode = "full"

    if mode == "example":
        print("Running with EXAMPLE data...")
        run_with_examples(session)

    elif mode == "subset":
        sample_percentage = 10
        print("Running with SUBSET of Snowflake data")
        adc_table = "EDW_APPS.MATCHING.ADC_ARTISTS_REMATCHED_ISWC_VW"
        mazooka_table = "EDW_APPS.MATCHING.MAZOOKA_RECORDINGS_REMATCHED_ISWC_VW"
        output_table = f"EDW_APPS.MATCHING.ARTIST_MATCHING_RESULTS_{sample_percentage}_PERC_SUBSET"

        # Read from Snowflake tables
        adc_df, mazooka_df = read_snowflake_tables(session, adc_table, mazooka_table)

        # Apply sampling
        print(f"Working with {sample_percentage}% of ADC data...")
        adc_count = adc_df.count()
        adc_sample_size = int(adc_count * sample_percentage / 100)
        adc_df = adc_df.sample(n=min(adc_sample_size, adc_count))

        print(f"Data size: {adc_df.count()} ADC artists and {mazooka_df.count()} Mazooka artists")

        # Process matching with improved method
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

            # Ensure all required columns are present with correct types
            expected_columns = {
                'ADC_ARTIST_ID': 'VARCHAR(16777216)',
                'APRA_WORK_ID': 'VARCHAR(16777216)',
                'APRA_ARTIST_ID': 'VARCHAR(16777216)',
                'ADC_ARTIST_NAME': 'VARCHAR(16777216)',
                'MAZOOKA_ARTIST_NAME': 'VARCHAR(16777216)',
                'MATCH_SCORE': 'FLOAT',
                'RECORDINGS_ID': 'VARCHAR(16777216)',
                'ISRC': 'VARCHAR(16777216)',
                'ISWC': 'VARCHAR(16777216)',
                'IS_VARIANT': 'VARCHAR(16777216)'
            }

            # Check if any columns are missing and add them with NULL values
            for col in expected_columns:
                if col not in distinct_results.columns:
                    distinct_results[col] = None

            # Save distinct results to table with specified column types
            distinct_results_df = session.create_dataframe(distinct_results)

            # Create or replace table with explicit column types
            table_definition = ", ".join([f"{col} {dtype}" for col, dtype in expected_columns.items()])
            session.sql(f"CREATE OR REPLACE TABLE {output_table} ({table_definition})").collect()

            # Insert data into the table
            distinct_results_df.write.mode("append").save_as_table(output_table)
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

        # Process matching with improved method
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

            # Ensure all required columns are present with correct types
            expected_columns = {
                'ADC_ARTIST_ID': 'VARCHAR(16777216)',
                'APRA_WORK_ID': 'VARCHAR(16777216)',
                'APRA_ARTIST_ID': 'VARCHAR(16777216)',
                'ADC_ARTIST_NAME': 'VARCHAR(16777216)',
                'MAZOOKA_ARTIST_NAME': 'VARCHAR(16777216)',
                'MATCH_SCORE': 'FLOAT',
                'RECORDINGS_ID': 'VARCHAR(16777216)',
                'ISRC': 'VARCHAR(16777216)',
                'ISWC': 'VARCHAR(16777216)',
                'IS_VARIANT': 'VARCHAR(16777216)'
            }

            # Check if any columns are missing and add them with NULL values
            for col in expected_columns:
                if col not in distinct_results.columns:
                    distinct_results[col] = None

            # Save distinct results to table with specified column types
            distinct_results_df = session.create_dataframe(distinct_results)

            # Create or replace table with explicit column types
            table_definition = ", ".join([f"{col} {dtype}" for col, dtype in expected_columns.items()])
            session.sql(f"CREATE OR REPLACE TABLE {output_table} ({table_definition})").collect()

            # Insert data into the table
            distinct_results_df.write.mode("append").save_as_table(output_table)
            print(f"Distinct results saved to table {output_table} with specified column types")

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