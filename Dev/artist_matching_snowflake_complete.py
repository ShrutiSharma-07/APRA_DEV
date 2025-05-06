import re
import difflib
import editdistance
import pandas as pd


def clean_artist_name(name):
    """
    Cleans artist names by:
    1. Replacing special characters with spaces
    2. Removing articles (A, AN, THE) and common words like 'BAND', 'ORCHESTRA'
    3. Removing all non-alphanumeric characters
    4. Normalizing spaces
    5. Removing parenthetical content
    """
    if name is None or pd.isna(name):
        return ""

    # Convert to uppercase for consistent processing
    name = str(name).upper()

    # First, remove parenthetical content - this helps with cases like "LOCO DICE (AKA YASSINE BEN ACHOUR)"
    name = re.sub(r'\([^)]*\)', '', name)

    # Replace special characters with spaces to preserve word boundaries
    name_with_spaces = re.sub(r'[\'"`\-_&+\]\[]', ' ', name)

    # Remove remaining non-alphanumeric characters (except spaces)
    cleaned = re.sub(r'[^a-zA-Z0-9 ]', '', name_with_spaces)

    # Normalize spaces (convert multiple spaces to single space)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # If the result is just spaces, return the original name
    if cleaned == "":
        return name

    # Remove common words and phrases
    stop_words = [
        r'\bA\b', r'\bAN\b', r'\bTHE\b', r'\bBAND\b', r'\bFEAT\b', r'\bFEAT.\b', r'\bFT\b', r'\bFT.\b',
        r'\bAND\b', r'\bORCHESTRA\b', r'\bORCHES\b', r'\bQUARTET\b', r'\bWITH\b', r'\bHIS\b', r'\bHER\b'
    ]

    for word in stop_words:
        cleaned = re.sub(word, ' ', cleaned)

    # Normalize spaces again after removing words
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # If the result is empty after removing stop words, return the previous cleaned version
    if cleaned == "":
        return name_with_spaces.strip()

    return cleaned


def match_with_delimiter_handling(adc_name, mazooka_name, debug=False):
    """
    Improved matching algorithm with better handling of:
    1. Different artists with common suffixes (orchestra, band, etc.)
    2. Name reversals with minor spelling variations
    """
    if not adc_name or not mazooka_name:
        return 0

    # Store original names
    adc_original = str(adc_name).strip()
    mazooka_original = str(mazooka_name).strip()

    if debug:
        print(f"Comparing:\nADC: {adc_original}\nMZK: {mazooka_original}")

    # Handling common suffixes like "& HIS ORCHESTRA"
    common_suffixes = [
        " & HIS ORCHESTRA", " AND HIS ORCHESTRA",
        " & HER ORCHESTRA", " AND HER ORCHESTRA",
        " & THE ORCHESTRA", " AND THE ORCHESTRA",
        " & HIS BAND", " AND HIS BAND",
        " & THE BAND", " AND THE BAND",
        " ORCHESTRA", " BAND", " QUARTET"
    ]

    # Check if both names end with the same suffix
    for suffix in common_suffixes:
        suffix_upper = suffix.upper()
        adc_upper = adc_original.upper()
        mzk_upper = mazooka_original.upper()

        # Check if both names end with the same suffix
        if adc_upper.endswith(suffix_upper) and mzk_upper.endswith(suffix_upper):
            # Extract artist names without the suffix
            adc_artist = adc_upper[:-len(suffix_upper)].strip()
            mzk_artist = mzk_upper[:-len(suffix_upper)].strip()

            # If both artist names exist and are different
            if adc_artist and mzk_artist and adc_artist != mzk_artist:
                # Extract the first significant word from each name
                adc_words = [w for w in adc_artist.split() if len(w) > 2 and w not in ["THE", "AND", "WITH"]]
                mzk_words = [w for w in mzk_artist.split() if len(w) > 2 and w not in ["THE", "AND", "WITH"]]

                # If both have significant words and they don't share any
                if adc_words and mzk_words:
                    # Check if there's no overlap between the significant words
                    if not any(word in mzk_words for word in adc_words):
                        if debug: print(f"Different artists with common suffix '{suffix}'")
                        return 0  # No match - different artists with common suffix

    # Regular exact match check
    if adc_original.upper() == mazooka_original.upper():
        if debug: print("Exact match after basic normalization")
        return 1.0

    # Remove parenthetical content
    adc_no_parentheses = re.sub(r'\([^)]*\)', '', adc_original.upper()).strip()
    mazooka_no_parentheses = re.sub(r'\([^)]*\)', '', mazooka_original.upper()).strip()

    # If identical after removing parenthetical content
    if adc_no_parentheses == mazooka_no_parentheses and adc_no_parentheses:
        if debug: print("Exact match after removing parenthetical content")
        return 1.0

    # IMPROVED FIX 2: Better handling for name reversals and spelling variations
    # First, normalize names for article-independent, order-independent comparison
    def normalize_for_comparison(name):
        """Normalize name for comparison by handling articles and word order"""
        name = name.upper()
        # Remove articles
        for article in [" THE ", " A ", " AN "]:
            name = f" {name} "  # Add spaces for proper replacement
            name = name.replace(article, " ")
        name = name.strip()
        # Remove parentheses
        name = re.sub(r'\([^)]*\)', '', name)
        # Replace common characters with spaces
        name = re.sub(r'[\'"`\-_&+\]\[]', ' ', name)
        # Remove non-alphanumeric chars except spaces
        name = re.sub(r'[^A-Z0-9 ]', '', name)
        # Normalize spaces
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    # Get normalized versions of both names
    adc_norm = normalize_for_comparison(adc_original)
    mzk_norm = normalize_for_comparison(mazooka_original)

    # Split into words and sort for word-order-independent comparison
    adc_words = sorted([w for w in adc_norm.split() if w])
    mzk_words = sorted([w for w in mzk_norm.split() if w])

    # If words match exactly regardless of order
    if adc_words and mzk_words and adc_words == mzk_words:
        if debug: print("Exact word match regardless of order")
        return 1.0

    # Improved fuzzy matching for word-by-word similarity with spelling variations
    if len(adc_words) == len(mzk_words) and len(adc_words) > 0:
        # Find best matching pairs using Levenshtein distance

        total_similarity = 0
        matched_count = 0

        # Try to match each word in adc_words to a word in mzk_words
        used_indices = set()

        for adc_word in adc_words:
            best_similarity = 0
            best_idx = -1

            for i, mzk_word in enumerate(mzk_words):
                if i not in used_indices:
                    # Calculate normalized Levenshtein similarity
                    max_len = max(len(adc_word), len(mzk_word))
                    if max_len > 0:
                        distance = editdistance.distance(adc_word, mzk_word)
                        similarity = 1.0 - (distance / max_len)

                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_idx = i

            # If we found a good match (>0.8 similarity)
            if best_idx >= 0 and best_similarity > 0.8:
                total_similarity += best_similarity
                matched_count += 1
                used_indices.add(best_idx)

        # If all words matched with high average similarity
        if matched_count == len(adc_words):
            avg_similarity = total_similarity / matched_count

            # Scale the score based on the average similarity
            # For extremely high similarity (>0.95), score can be up to 0.99
            # For good similarity (>0.8), score ranges from 0.8 to 0.95
            if avg_similarity > 0.95:
                score = 0.95 + (avg_similarity - 0.95) * 0.8  # Max 0.99
                if debug: print(f"Very high word-by-word similarity: {score:.2f}")
                return score
            elif avg_similarity > 0.8:
                score = 0.8 + (avg_similarity - 0.8) * 0.75  # Range 0.8-0.95
                if debug: print(f"High word-by-word similarity: {score:.2f}")
                return score

    # Clean names
    adc_clean = clean_artist_name(adc_original.upper())
    mazooka_clean = clean_artist_name(mazooka_original.upper())

    # If identical after cleaning
    if adc_clean == mazooka_clean and adc_clean:
        if debug: print("Exact match after cleaning")
        return 1.0

    # Define delimiters
    delimiters = ['|', '/', '#', '\\', ',', ';', '\'', '"', '`', '-', '_', '&', '+', ']', '[']
    word_delimiters = [
        ' A ', ' AN ', ' THE ', ' AND ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ', ' BAND ', ' WITH ',
        ' QUARTET ', ' ORCHES ', ' ORCHESTRA ', ' HIS ', ' HER '
    ]

    # Check for delimiters
    adc_has_delimiters = any(d in adc_original.upper() for d in delimiters)
    mazooka_has_delimiters = any(d in mazooka_original.upper() for d in delimiters)
    adc_has_word_delimiters = any(wd in ' ' + adc_original.upper() + ' ' for wd in word_delimiters)
    mazooka_has_word_delimiters = any(wd in ' ' + mazooka_original.upper() + ' ' for wd in word_delimiters)

    # Track if this match is from a variant
    is_from_variant = False

    # Handle delimited names
    if adc_has_delimiters or adc_has_word_delimiters or mazooka_has_delimiters or mazooka_has_word_delimiters:
        # Normalize delimiters
        adc_normalized = ' ' + adc_original.upper() + ' '
        mazooka_normalized = ' ' + mazooka_original.upper() + ' '

        # Replace delimiters with pipe
        for d in delimiters:
            adc_normalized = adc_normalized.replace(d, '|')
            mazooka_normalized = mazooka_normalized.replace(d, '|')

        # Replace word delimiters
        for wd in word_delimiters:
            adc_normalized = adc_normalized.replace(wd, '|')
            mazooka_normalized = mazooka_normalized.replace(wd, '|')

        # Split and clean parts
        adc_parts = [clean_artist_name(part) for part in adc_normalized.split('|') if part.strip()]
        mazooka_parts = [clean_artist_name(part) for part in mazooka_normalized.split('|') if part.strip()]

        # Filter out empty parts
        adc_parts = [part for part in adc_parts if part]
        mazooka_parts = [part for part in mazooka_parts if part]

        if debug:
            print(f"ADC parts: {adc_parts}")
            print(f"MZK parts: {mazooka_parts}")

        # If sorted parts match exactly
        if adc_parts and mazooka_parts and sorted(adc_parts) == sorted(mazooka_parts):
            if debug: print("Sorted delimited parts match exactly")
            return 1.0

        # Check each part against other's parts
        for adc_part in adc_parts:
            for mzk_part in mazooka_parts:
                # If parts match exactly
                if adc_part == mzk_part:
                    if debug: print(f"Found exact matching part: '{adc_part}'")
                    # If this is a match on a part (not the whole)
                    if adc_part != adc_clean or mzk_part != mazooka_clean:
                        # Store the variant info in a global tracker or elsewhere as needed
                        # For now, we'll handle variants separately in determine_variant_status
                        pass
                    return 1.0

                # Check for word order variations in parts
                adc_part_words = sorted([w for w in adc_part.split() if w])
                mzk_part_words = sorted([w for w in mzk_part.split() if w])

                if adc_part_words and mzk_part_words and adc_part_words == mzk_part_words:
                    if debug: print(f"Found parts with same words in different order")
                    return 1.0

        # Check if one name is contained in other's parts
        for part in adc_parts:
            if part == mazooka_clean:
                if debug: print(f"MZK name found as exact part of ADC")
                return 1.0

        for part in mazooka_parts:
            if part == adc_clean:
                if debug: print(f"ADC name found as exact part of MZK")
                return 1.0

    # Check for subset relationship
    if adc_clean and mazooka_clean:
        adc_words = [w for w in adc_clean.split() if w]
        mazooka_words = [w for w in mazooka_clean.split() if w]

        # If one set of words is subset of the other
        if (set(adc_words).issubset(set(mazooka_words)) or
            set(mazooka_words).issubset(set(adc_words))):

            match_ratio = min(len(adc_words), len(mazooka_words)) / max(len(adc_words), len(mazooka_words))

            if match_ratio >= 0.5 and min(len(adc_words), len(mazooka_words)) >= 1:
                score = 0.8 + (match_ratio - 0.5) * 0.2
                if debug: print(f"Word subset match with score {score:.2f}")
                return score

    # Sequence similarity for remaining cases
    similarity = difflib.SequenceMatcher(None, adc_clean, mazooka_clean).ratio()

    if similarity > 0.7:
        adjusted = similarity * 0.9
        if debug: print(f"Sequence similarity: {similarity:.2f} adjusted to {adjusted:.2f}")
        return adjusted

    # Check for substring containment
    if adc_clean in mazooka_clean or mazooka_clean in adc_clean:
        longer = max(len(adc_clean), len(mazooka_clean))
        shorter = min(len(adc_clean), len(mazooka_clean))

        if shorter / longer >= 0.8:
            score = 0.7 + 0.2 * (shorter / longer)
            if debug: print(f"Substring match with score {score:.2f}")
            return score

    # Low similarity
    if similarity > 0.6:
        adjusted = similarity * 0.8
        if debug: print(f"Low similarity: {adjusted:.2f}")
        return adjusted

    # No match
    if debug: print("No significant match")
    return 0


def match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6):
    """
    Improved artist matching with better handling of variants and edge cases.
    """
    print("Initiating artist name matching with ISWC indexing...")

    # Convert to pandas for processing
    adc_pandas = adc_df.to_pandas()
    mazooka_pandas = mazooka_df.to_pandas()

    # Clean artist names
    print("Cleaning artist names...")
    adc_pandas['CLEAN_NAME'] = adc_pandas['NAME'].apply(clean_artist_name)
    mazooka_pandas['CLEAN_ARTIST_NAME'] = mazooka_pandas['ARTIST_NAME'].apply(clean_artist_name)

    # Create expanded dataframes with split names
    print("Expanding delimited ADC artist names...")
    expanded_adc = expand_adc_delimited_names(adc_pandas)
    print(f"Expanded ADC dataset from {len(adc_pandas)} to {len(expanded_adc)} rows")

    print("Expanding delimited Mazooka artist names...")
    expanded_mazooka = expand_mazooka_delimited_names(mazooka_pandas)
    print(f"Expanded Mazooka dataset from {len(mazooka_pandas)} to {len(expanded_mazooka)} rows")

    # Group by ISWC for faster matching
    print("Creating ISWC indexes...")
    adc_by_iswc = {}
    mazooka_by_iswc = {}

    # Track original ADC rows
    original_adc_ids = set(adc_pandas['ADC_ARTIST_ID'])

    # Create indexes by ISWC
    for _, row in expanded_adc.iterrows():
        iswc = row.get('ISWC')
        if iswc and not pd.isna(iswc):
            if iswc not in adc_by_iswc:
                adc_by_iswc[iswc] = []
            adc_by_iswc[iswc].append(row)

    for _, row in expanded_mazooka.iterrows():
        iswc = row.get('ISWC')
        if iswc and not pd.isna(iswc):
            if iswc not in mazooka_by_iswc:
                mazooka_by_iswc[iswc] = []
            mazooka_by_iswc[iswc].append(row)

    # Find common ISWCs
    common_iswcs = set(adc_by_iswc.keys()).intersection(set(mazooka_by_iswc.keys()))
    print(f"Found {len(common_iswcs)} common ISWCs between datasets")

    # Track matches
    matched_combinations = set()
    results = []
    best_matches = {}  # {ADC_ARTIST_ID: (score, result_dict)}

    # Process each common ISWC
    total_iswcs = len(common_iswcs)
    for idx, iswc in enumerate(common_iswcs):
        if idx % 100 == 0:
            print(f"Processing ISWC {idx+1}/{total_iswcs} ({round((idx+1)/total_iswcs*100)}%)")

        adc_artists = adc_by_iswc[iswc]
        mazooka_artists = mazooka_by_iswc[iswc]

        # Find best matches within same ISWC
        for adc_row in adc_artists:
            adc_id = adc_row.get('ADC_ARTIST_ID')
            adc_name = adc_row['NAME']
            is_variant_adc = adc_row['IS_VARIANT_ADC']

            best_match = None
            best_score = 0

            # Try exact match first (case insensitive)
            for mz_row in mazooka_artists:
                mz_id = mz_row.get('RECORDINGS_ID')
                if (adc_id, mz_id) in matched_combinations:
                    continue

                mz_name = mz_row['ARTIST_NAME']

                if adc_name is not None and mz_name is not None and str(adc_name).upper() == str(mz_name).upper():
                    best_match = mz_row
                    best_score = 1.0
                    break

            # If no exact match, try with delimiter handling
            if best_score < 1.0:
                for mz_row in mazooka_artists:
                    mz_id = mz_row.get('RECORDINGS_ID')
                    if (adc_id, mz_id) in matched_combinations:
                        continue

                    mz_name = mz_row['ARTIST_NAME']

                    # Use the improved matching algorithm
                    score = match_with_delimiter_handling(adc_name, mz_name)

                    if score > best_score:
                        best_score = score
                        best_match = mz_row

            # If we found a good match
            if best_match is not None and best_score >= match_threshold:
                mz_id = best_match.get('RECORDINGS_ID')
                matched_combinations.add((adc_id, mz_id))

                # Get the original Mazooka and ADC records before splitting
                original_adc_rows = adc_pandas[adc_pandas['ADC_ARTIST_ID'] == adc_id]
                original_adc_row = original_adc_rows.iloc[0] if not original_adc_rows.empty else None

                original_mazooka_rows = mazooka_pandas[mazooka_pandas['RECORDINGS_ID'] == best_match.get('RECORDINGS_ID')]
                original_mzk_row = original_mazooka_rows.iloc[0] if not original_mazooka_rows.empty else None

                # Determine final variant status for both ADC and Mazooka
                original_adc_name = original_adc_row['NAME'] if original_adc_row is not None else adc_name
                original_mzk_name = original_mzk_row['ARTIST_NAME'] if original_mzk_row is not None else best_match['ARTIST_NAME']

                # Use the improved variant determination function with current variant statuses
                final_is_variant_adc, final_is_variant_mzk = determine_variant_status(
                    original_adc_name,
                    original_mzk_name,
                    best_score,
                    is_variant_adc,  # Pass the current variant status
                    best_match.get('IS_VARIANT_MZK', 'ORIGINAL')  # Pass the current variant status
                )

                # Additional check to ensure variant status is properly carried forward
                # If either the current row or the match is a variant, that status should be preserved
                if is_variant_adc == 'VARIANT':
                    final_is_variant_adc = 'VARIANT'

                is_variant_mzk = best_match.get('IS_VARIANT_MZK', 'ORIGINAL')
                if is_variant_mzk == 'VARIANT':
                    final_is_variant_mzk = 'VARIANT'

                # Check for delimiter-based matches
                adc_has_delimiters = any(d in str(original_adc_name) for d in ['|', '/', ',', '&', '-', 'FT', 'FEAT', 'WITH', 'AND'])
                mzk_has_delimiters = any(d in str(original_mzk_name) for d in ['|', '/', ',', '&', '-', 'FT', 'FEAT', 'WITH', 'AND'])

                # If names have delimiters and the match score is high, likely a variant match
                if adc_has_delimiters and best_score >= 0.8:
                    final_is_variant_adc = 'VARIANT'
                if mzk_has_delimiters and best_score >= 0.8:
                    final_is_variant_mzk = 'VARIANT'

                # Create the result dictionary
                result_dict = {
                    'ADC_ARTIST_ID': adc_id,
                    'APRA_WORK_ID': adc_row.get('APRA_WORK_ID', None),
                    'APRA_ARTIST_ID': adc_row.get('APRA_ARTIST_ID', None),
                    'ADC_ARTIST_NAME': original_adc_name,
                    'MAZOOKA_ARTIST_NAME': original_mzk_name,
                    'MATCH_SCORE': best_score,
                    'RECORDINGS_ID': best_match.get('RECORDINGS_ID', None),
                    'ISRC': best_match.get('ISRC', None),
                    'ISWC': iswc,
                    'IS_VARIANT_ADC': final_is_variant_adc,
                    'IS_VARIANT_MZK': final_is_variant_mzk
                }

                # If this is an original ADC entry, directly add it to results
                if is_variant_adc == 'ORIGINAL':
                    results.append(result_dict)
                # If it's a variant, only keep the best match for each original ADC artist
                elif adc_id in original_adc_ids:
                    if adc_id not in best_matches or best_score > best_matches[adc_id][0]:
                        best_matches[adc_id] = (best_score, result_dict)

    # Add the best variant matches to results
    for adc_id, (score, result_dict) in best_matches.items():
        if adc_id not in [r['ADC_ARTIST_ID'] for r in results if r['IS_VARIANT_ADC'] == 'ORIGINAL']:
            results.append(result_dict)

    # Process artists without ISWC matches
    print("Processing ADC artists without ISWC matches...")
    adc_without_iswc = []
    for _, row in adc_pandas.iterrows():
        iswc = row.get('ISWC')
        if not iswc or pd.isna(iswc) or iswc not in common_iswcs:
            adc_without_iswc.append(row)

    if adc_without_iswc:
        total_without_iswc = len(adc_without_iswc)
        print(f"Found {total_without_iswc} ADC artists without ISWC matches")

        batch_size = 500
        for i in range(0, total_without_iswc, batch_size):
            batch = adc_without_iswc[i:i+batch_size]

            for adc_row in batch:
                adc_id = adc_row.get('ADC_ARTIST_ID')
                adc_name = adc_row['NAME']

                best_match = None
                best_score = 0

                # Try with a sample of Mazooka records for efficiency
                sample_mazooka = expanded_mazooka.head(500)

                # Try exact match first
                for _, mz_row in sample_mazooka.iterrows():
                    mz_id = mz_row.get('RECORDINGS_ID')
                    if (adc_id, mz_id) in matched_combinations:
                        continue

                    mz_name = mz_row['ARTIST_NAME']

                    if adc_name is not None and mz_name is not None and str(adc_name).upper() == str(mz_name).upper():
                        best_match = mz_row
                        best_score = 1.0
                        break

                # If no exact match, try with delimiter handling
                if best_score < 1.0:
                    for _, mz_row in sample_mazooka.iterrows():
                        mz_id = mz_row.get('RECORDINGS_ID')
                        if (adc_id, mz_id) in matched_combinations:
                            continue

                        mz_name = mz_row['ARTIST_NAME']

                        # Use the improved matching algorithm
                        score = match_with_delimiter_handling(adc_name, mz_name)

                        if score > best_score:
                            best_score = score
                            best_match = mz_row

                # If we found a good match
                if best_match is not None and best_score >= match_threshold:
                    mz_id = best_match.get('RECORDINGS_ID')
                    matched_combinations.add((adc_id, mz_id))

                    # Get the original Mazooka record
                    original_mazooka_rows = mazooka_pandas[mazooka_pandas['RECORDINGS_ID'] == best_match.get('RECORDINGS_ID')]
                    original_mzk_row = original_mazooka_rows.iloc[0] if not original_mazooka_rows.empty else None
                    original_mzk_name = original_mzk_row['ARTIST_NAME'] if original_mzk_row is not None else best_match['ARTIST_NAME']

                    # Get the variant status from the expanded rows
                    is_variant_adc = best_match.get('IS_VARIANT_ADC', 'ORIGINAL')
                    is_variant_mzk = best_match.get('IS_VARIANT_MZK', 'ORIGINAL')

                    # Determine variant status
                    final_is_variant_adc, final_is_variant_mzk = determine_variant_status(
                        adc_name, original_mzk_name, best_score, is_variant_adc, is_variant_mzk
                    )

                    # Check for delimiter-based matches
                    adc_has_delimiters = any(d in str(adc_name) for d in ['|', '/', ',', '&', '-', 'FT', 'FEAT', 'WITH', 'AND'])
                    mzk_has_delimiters = any(d in str(original_mzk_name) for d in ['|', '/', ',', '&', '-', 'FT', 'FEAT', 'WITH', 'AND'])

                    # If names have delimiters and the match score is high, likely a variant match
                    if adc_has_delimiters and best_score >= 0.8:
                        final_is_variant_adc = 'VARIANT'
                    if mzk_has_delimiters and best_score >= 0.8:
                        final_is_variant_mzk = 'VARIANT'

                    results.append({
                        'ADC_ARTIST_ID': adc_id,
                        'APRA_WORK_ID': adc_row.get('APRA_WORK_ID', None),
                        'APRA_ARTIST_ID': adc_row.get('APRA_ARTIST_ID', None),
                        'ADC_ARTIST_NAME': adc_name,
                        'MAZOOKA_ARTIST_NAME': original_mzk_name,
                        'MATCH_SCORE': best_score,
                        'RECORDINGS_ID': best_match.get('RECORDINGS_ID', None),
                        'ISRC': best_match.get('ISRC', None),
                        'ISWC': best_match.get('ISWC', None),
                        'IS_VARIANT_ADC': final_is_variant_adc,
                        'IS_VARIANT_MZK': final_is_variant_mzk
                    })

            progress = min(100, round((i + len(batch)) / total_without_iswc * 100))
            print(f"Processed non-ISWC artists: {progress}%")

    # Create DataFrame from results
    if not results:
        print("No matches found that meet the threshold criteria.")
        results_df_pandas = pd.DataFrame(columns=[
            'ADC_ARTIST_ID', 'APRA_WORK_ID', 'APRA_ARTIST_ID', 'ADC_ARTIST_NAME',
            'MAZOOKA_ARTIST_NAME', 'MATCH_SCORE', 'RECORDINGS_ID', 'ISRC', 'ISWC',
            'IS_VARIANT_ADC', 'IS_VARIANT_MZK'
        ])
    else:
        results_df_pandas = pd.DataFrame(results)

    # Convert back to Snowpark DataFrame
    results_df = session.create_dataframe(results_df_pandas)

    return results_df


def expand_adc_delimited_names(adc_pandas_df):
    """
    Expands rows with delimited artist names into multiple rows,
    one for each part of the delimited name.
    """
    expanded_rows = []

    # Define ALL delimiters
    delimiters = ['|', '/', '#', '\\', ',', ';', '\'', '"', '`', '-', '_', '&', '+', ']', '[']
    word_delimiters = [
        ' A ', ' AN ', ' THE ', ' AND ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ', ' BAND ', ' WITH ',
        ' QUARTET ', ' ORCHES ', ' ORCHESTRA ', ' HIS ', ' HER '
    ]

    for _, row in adc_pandas_df.iterrows():
        artist_name = row['NAME']

        # First add the original name row
        new_row = row.copy()
        new_row['IS_VARIANT_ADC'] = 'ORIGINAL'
        expanded_rows.append(new_row)

        # Check if artist name contains delimiters
        has_char_delimiters = artist_name is not None and any(d in str(artist_name) for d in delimiters)
        has_word_delimiters = artist_name is not None and any(wd in ' ' + str(artist_name).upper() + ' ' for wd in word_delimiters)

        if has_char_delimiters or has_word_delimiters:
            # First handle character delimiters
            artist_name_norm = str(artist_name).upper()
            for d in delimiters:
                artist_name_norm = artist_name_norm.replace(d, '/')

            # Then handle word delimiters by replacing them with slashes
            for wd in word_delimiters:
                artist_name_norm = ' ' + artist_name_norm + ' '  # Add spaces to ensure proper replacement
                artist_name_norm = artist_name_norm.replace(wd, '/')
                artist_name_norm = artist_name_norm.strip()  # Remove the extra spaces

            # Split and clean parts
            parts = [part.strip() for part in artist_name_norm.split('/')]

            # For each part, create a new row with the part as NAME
            for part in parts:
                if part and part != artist_name and len(part) > 2:  # Only add meaningful parts
                    new_row = row.copy()
                    new_row['NAME'] = part
                    new_row['CLEAN_NAME'] = clean_artist_name(part)
                    new_row['IS_VARIANT_ADC'] = 'VARIANT'
                    expanded_rows.append(new_row)

    # Convert back to a DataFrame
    expanded_df = pd.DataFrame(expanded_rows)
    return expanded_df


def expand_mazooka_delimited_names(mazooka_pandas_df):
    """
    Expands rows with delimited artist names into multiple rows,
    one for each part of the delimited name.
    """
    expanded_rows = []

    # Define delimiters
    delimiters = ['|', '/', '#', '\\', ',', ';', '\'', '"', '`', '-', '_', '&', '+', ']', '[']
    word_delimiters = [
        ' A ', ' AN ', ' THE ', ' AND ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ', ' BAND ', ' WITH ',
        ' QUARTET ', ' ORCHES ', ' ORCHESTRA ', ' HIS ', ' HER '
    ]

    for _, row in mazooka_pandas_df.iterrows():
        artist_name = row['ARTIST_NAME']

        # First add the original name row
        new_row = row.copy()
        new_row['IS_VARIANT_MZK'] = 'ORIGINAL'
        expanded_rows.append(new_row)

        # Check if artist name contains delimiters
        has_char_delimiters = artist_name is not None and any(d in str(artist_name) for d in delimiters)
        has_word_delimiters = artist_name is not None and any(wd in ' ' + str(artist_name).upper() + ' ' for wd in word_delimiters)

        if has_char_delimiters or has_word_delimiters:
            # First handle character delimiters
            artist_name_norm = str(artist_name).upper()
            for d in delimiters:
                artist_name_norm = artist_name_norm.replace(d, '/')

            # Then handle word delimiters by replacing them with slashes
            for wd in word_delimiters:
                artist_name_norm = ' ' + artist_name_norm + ' '  # Add spaces to ensure proper replacement
                artist_name_norm = artist_name_norm.replace(wd, '/')
                artist_name_norm = artist_name_norm.strip()  # Remove the extra spaces

            # Split and clean parts
            parts = [part.strip() for part in artist_name_norm.split('/')]

            # For each part, create a new row with the part as ARTIST_NAME
            for part in parts:
                if part and part != artist_name and len(part) > 2:  # Only add meaningful parts
                    new_row = row.copy()
                    new_row['ARTIST_NAME'] = part
                    new_row['CLEAN_ARTIST_NAME'] = clean_artist_name(part)
                    new_row['IS_VARIANT_MZK'] = 'VARIANT'
                    expanded_rows.append(new_row)

    # Convert back to a DataFrame
    expanded_df = pd.DataFrame(expanded_rows)
    return expanded_df


def determine_variant_status(adc_name, mazooka_name, match_score, adc_variant='ORIGINAL', mzk_variant='ORIGINAL'):
    """
    Determines if either match is a variant based on the match details.
    Returns a tuple of (IS_VARIANT_ADC, IS_VARIANT_MZK)

    Parameters:
    - adc_name: Original ADC artist name
    - mazooka_name: Original Mazooka artist name
    - match_score: The match score between the names
    - adc_variant: Initial variant status for ADC (from earlier processing)
    - mzk_variant: Initial variant status for Mazooka (from earlier processing)
    """
    if not adc_name or not mazooka_name:
        return ('ORIGINAL', 'ORIGINAL')

    # Start with provided variant status
    is_variant_adc = adc_variant
    is_variant_mzk = mzk_variant

    # Clean both names to get the core parts
    adc_clean = clean_artist_name(str(adc_name).upper())
    mazooka_clean = clean_artist_name(str(mazooka_name).upper())

    # Define delimiters
    delimiters = ['|', '/', '#', '\\', ',', ';', '\'', '"', '`', '-', '_', '&', '+', ']', '[']
    word_delimiters = [
        ' A ', ' AN ', ' THE ', ' AND ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ', ' BAND ', ' WITH ',
        ' QUARTET ', ' ORCHES ', ' ORCHESTRA ', ' HIS ', ' HER '
    ]

    # Check if names have delimiters
    adc_has_delimiters = any(d in str(adc_name).upper() for d in delimiters)
    adc_has_word_delimiters = any(wd in ' ' + str(adc_name).upper() + ' ' for wd in word_delimiters)

    mazooka_has_delimiters = any(d in str(mazooka_name).upper() for d in delimiters)
    mazooka_has_word_delimiters = any(wd in ' ' + str(mazooka_name).upper() + ' ' for wd in word_delimiters)

    # Check for parenthetical content
    adc_has_parentheses = '(' in str(adc_name) and ')' in str(adc_name)
    mazooka_has_parentheses = '(' in str(mazooka_name) and ')' in str(mazooka_name)

    # If exact match after cleaning and no delimiting in either, neither is a variant
    if adc_clean == mazooka_clean and not (adc_has_delimiters or adc_has_word_delimiters or
                                         mazooka_has_delimiters or mazooka_has_word_delimiters):
        return ('ORIGINAL', 'ORIGINAL')

    # If ADC name has delimiters or word delimiters, mark as VARIANT
    if adc_has_delimiters or adc_has_word_delimiters:
        adc_normalized = ' ' + str(adc_name).upper() + ' '

        # Replace standard delimiters
        for d in delimiters:
            adc_normalized = adc_normalized.replace(d, '|')

        # Replace word delimiters with pipe
        for wd in word_delimiters:
            adc_normalized = adc_normalized.replace(wd, '|')

        # Split by the normalized delimiter
        adc_parts = [clean_artist_name(part) for part in adc_normalized.split('|') if part.strip()]

        # If we have multiple parts and match score is high, mark as variant
        if len(adc_parts) > 1 and match_score >= 0.6:
            is_variant_adc = 'VARIANT'

        # Check if mazooka name matches any part but not the whole
        for part in adc_parts:
            if part == mazooka_clean and part != adc_clean:
                is_variant_adc = 'VARIANT'
                break

    # If Mazooka name has delimiters or word delimiters, mark as VARIANT
    if mazooka_has_delimiters or mazooka_has_word_delimiters:
        mazooka_normalized = ' ' + str(mazooka_name).upper() + ' '

        # Replace standard delimiters
        for d in delimiters:
            mazooka_normalized = mazooka_normalized.replace(d, '|')

        # Replace word delimiters with pipe
        for wd in word_delimiters:
            mazooka_normalized = mazooka_normalized.replace(wd, '|')

        # Split by the normalized delimiter
        mazooka_parts = [clean_artist_name(part) for part in mazooka_normalized.split('|') if part.strip()]

        # If we have multiple parts and match score is high, mark as variant
        if len(mazooka_parts) > 1 and match_score >= 0.6:
            is_variant_mzk = 'VARIANT'

        # Check if adc name matches any part but not the whole
        for part in mazooka_parts:
            if part == adc_clean and part != mazooka_clean:
                is_variant_mzk = 'VARIANT'
                break

    # Check if one is a subset of the other
    if match_score >= 0.6:  # Only consider for reasonable matches
        # Get words from each name
        adc_words = [w for w in adc_clean.split() if w]
        mazooka_words = [w for w in mazooka_clean.split() if w]

        # If ADC is a subset of Mazooka but not equal
        if (set(adc_words).issubset(set(mazooka_words)) and
            len(adc_words) < len(mazooka_words)):
            is_variant_mzk = 'VARIANT'

        # If Mazooka is a subset of ADC but not equal
        if (set(mazooka_words).issubset(set(adc_words)) and
            len(mazooka_words) < len(adc_words)):
            is_variant_adc = 'VARIANT'

    # Handle parenthetical content as a variant factor
    if adc_has_parentheses and not mazooka_has_parentheses:
        # If Mazooka name is equal to ADC name without parentheses
        adc_no_parentheses = re.sub(r'\([^)]*\)', '', str(adc_name)).strip()
        if adc_no_parentheses.upper() == str(mazooka_name).upper():
            is_variant_adc = 'VARIANT'

    if mazooka_has_parentheses and not adc_has_parentheses:
        # If ADC name is equal to Mazooka name without parentheses
        mazooka_no_parentheses = re.sub(r'\([^)]*\)', '', str(mazooka_name)).strip()
        if mazooka_no_parentheses.upper() == str(adc_name).upper():
            is_variant_mzk = 'VARIANT'

    return (is_variant_adc, is_variant_mzk)


def main():

    # Choose the mode to run in
    mode = "subset"  # Options: "example", "subset", "full"

    if mode == "example":
        print("Running with example data...")

        adc_examples = pd.DataFrame({
            'ADC_ARTIST_ID': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10',
                              'P1', 'P2', 'P3', 'P4', 'P5'],
            'APRA_WORK_ID': ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10',
                             'PW1', 'PW2', 'PW3', 'PW4', 'PW5'],
            'ISWC': ['ISWC1', 'ISWC2', 'ISWC3', 'ISWC4', 'ISWC5', 'ISWC6', 'ISWC7', 'ISWC8', 'ISWC9', 'ISWC10',
                     'P_ISWC1', 'P_ISWC2', 'P_ISWC3', 'P_ISWC4', 'P_ISWC5'],
            'APRA_ARTIST_ID': ['PA1', 'PA2', 'PA3', 'PA4', 'PA5', 'PA6', 'PA7', 'PA8', 'PA9', 'PA10',
                               'PPA1', 'PPA2', 'PPA3', 'PPA4', 'PPA5'],
            'NAME': [
                # Regular examples
                'ROBBIE WILLIAMS',
                'JAMES TAYLOR|ALISON KRAUSS',
                'QUINCY JONES & THE BAND',
                'THE UPSETTERS',
                'COUNT BASIE / ROY ELDRIDGE',
                'COUNT BASEE',
                'TAKE THAT',
                'GUNS N\'ROSES',
                'MUNGO JERRY',
                'LOCO DICE (AKA YASSINE BEN ACHOUR)',

                # Problem cases
                'THE 90\'S GENERATION',
                'TORNADOES THE',
                'JUDY GARLAND',
                'ACE HOOD (ANTOINE MCCOLISTER)',
                'DIZZY GILLESPIE & HIS ORCHESTRA'
            ]
        })

        mazooka_examples = pd.DataFrame({
            'RECORDINGS_ID': ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10',
                              'PR1', 'PR2', 'PR3', 'PR4', 'PR5'],
            'ISRC': ['ISRC1', 'ISRC2', 'ISRC3', 'ISRC4', 'ISRC5', 'ISRC6', 'ISRC7', 'ISRC8', 'ISRC9', 'ISRC10',
                      'P_ISRC1', 'P_ISRC2', 'P_ISRC3', 'P_ISRC4', 'P_ISRC5'],
            'ISWC': ['ISWC1', 'ISWC2', 'ISWC3', 'ISWC4', 'ISWC5', 'ISWC6', 'ISWC7', 'ISWC8', 'ISWC9', 'ISWC10',
                     'P_ISWC1', 'P_ISWC2', 'P_ISWC3', 'P_ISWC4', 'P_ISWC5'],
            'ARTIST_NAME': [
                # Regular examples
                'WILLIAMS ROBBIE',
                'ALISON KRAUSS / JAMES TAYLOR',
                'QUINCY JONES',
                'UPSETTERS',
                'ROY ELDRIDGE AND COUNT BASIE',
                'COUNT BASIE',
                'TAKE THAT FEAT JONAS',
                'GUNS N ROSES',
                'JERRY MUNGO',
                'LOCO DICE',

                # Problem cases
                'IT\'S A COVER UP, DAVID, TYSON, WARD',
                'THE TORNADOS',
                'JAY AND THE AMERICANS',
                'ACE HOOD',
                'PAUL WESTON & HIS ORCHESTRA'
            ]
        })

        # Convert to Snowpark DataFrames
        adc_df = session.create_dataframe(adc_examples)
        mazooka_df = session.create_dataframe(mazooka_examples)

        # Run the matching algorithm
        print("Running matching algorithm with improved code...")
        results_df = match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6)

        # Convert to pandas for display
        results_pandas = results_df.to_pandas()

        # Display results in table format
        if not results_pandas.empty:
            # Sort by score in descending order to show best matches first
            results_sorted = results_pandas.sort_values(by='MATCH_SCORE', ascending=False)

            # Format the results as a table
            print("\nMatching Results (sorted by match score):")
            print("{:<10} {:<12} {:<30} {:<30} {:<10} {:<15} {:<15}".format(
                "ADC_ID", "APRA_WORK_ID", "ADC_ARTIST_NAME", "MAZOOKA_ARTIST_NAME",
                "SCORE", "IS_VARIANT_ADC", "IS_VARIANT_MZK"))
            print("-" * 120)

            for _, row in results_sorted.iterrows():
                print("{:<10} {:<12} {:<30} {:<30} {:<10.2f} {:<15} {:<15}".format(
                    row['ADC_ARTIST_ID'],
                    str(row['APRA_WORK_ID'])[:12],
                    str(row['ADC_ARTIST_NAME'])[:30],
                    str(row['MAZOOKA_ARTIST_NAME'])[:30],
                    row['MATCH_SCORE'],
                    row['IS_VARIANT_ADC'],
                    row['IS_VARIANT_MZK']))
        else:
            print("No matches found.")

    elif mode == "subset":
        # Implementation for subset mode
        sample_percentage = 1
        print(f"Running with {sample_percentage}% of Snowflake data")
        adc_table = "EDW_APPS.MATCHING.ADC_ARTISTS_MATCHED_ISWC_VW"
        mazooka_table = "EDW_APPS.MATCHING.MAZOOKA_RECORDINGS_MATCHED_ISWC_VW"
        output_table = f"EDW_APPS.MATCHING.ARTIST_MATCHING_RESULTS_{sample_percentage}_PERC_SUBSET"

        # Read from Snowflake tables
        adc_df = session.table(adc_table)
        mazooka_df = session.table(mazooka_table)

        # Apply sampling
        adc_count = adc_df.count()
        adc_sample_size = int(adc_count * sample_percentage / 100)
        adc_df = adc_df.sample(n=min(adc_sample_size, adc_count))

        print(f"Data size: {adc_df.count()} ADC artists and {mazooka_df.count()} Mazooka artists")

        # Process matching with improved method
        results_df = match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6)

        # Save results to Snowflake
        results_df.write.mode("overwrite").save_as_table(output_table)
        print(f"Results saved to {output_table}")

    elif mode == "full":
        # Run with full dataset
        print("Running with FULL Snowflake dataset...")
        adc_table = "EDW_APPS.MATCHING.ADC_ARTISTS_MATCHED_ISWC_VW"
        mazooka_table = "EDW_APPS.MATCHING.MAZOOKA_RECORDINGS_MATCHED_ISWC_VW"
        output_table = "EDW_APPS.MATCHING.ARTIST_MATCHING_RESULTS_FULL"

        # Read from Snowflake tables
        adc_df = session.table(adc_table)
        mazooka_df = session.table(mazooka_table)

        print(f"Processing the entire dataset...")
        print(f"Data size: {adc_df.count()} ADC artists and {mazooka_df.count()} Mazooka artists")

        # Process matching
        results_df = match_artists_with_iswc_indexing(session, adc_df, mazooka_df, match_threshold=0.6)

        # Save results to Snowflake
        results_df.write.mode("overwrite").save_as_table(output_table)
        print(f"Results saved to {output_table}")

    # Close the session
    session.close()


if __name__ == "__main__":
    main()

