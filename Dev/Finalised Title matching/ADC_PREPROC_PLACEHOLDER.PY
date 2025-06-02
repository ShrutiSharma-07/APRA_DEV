#ADC COMPOSER PREPROCESS SCRIPT - OPTIMIZED VERSION

import re
import pandas as pd
from snowflake.snowpark.functions import upper, col
import numpy as np

def clean_composer_name(name):
    
    if name is None or pd.isna(name):
        return ""
    
    try:
        # Convert to uppercase for consistent processing
        name = str(name).upper()
        
        # Create a copy of the name without apostrophes for cleaning
        name_no_apostrophes = re.sub(r'[\'"-]', '', name)  
        
        # Added hyphen to the special characters list
        name_with_spaces = re.sub(r'["`_&+\]\[]', '', name_no_apostrophes)  # Removed the hyphen from this pattern
        name_with_spaces = name_with_spaces.replace('-', ' ') 
        name_with_spaces = name_with_spaces.replace('"', '') 
        
        # Remove remaining non-alphanumeric characters (except spaces)
        cleaned = re.sub(r'[^a-zA-Z0-9 ]', '', name_with_spaces)
        
        # Normalize spaces (convert multiple spaces to single space)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # If the result is just spaces, return the original name
        if cleaned == "":
            return name
        
        # Updated stop_words list with additional normalizations
        stop_words = [r'\bA\b', r'\bAN\b', r'\bTHE\b']
            
        for word in stop_words:
            cleaned = re.sub(word, ' ', cleaned)
        
        # Normalize spaces again after removing stop words
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # If the result is empty after removing stop words, return the previous cleaned version
        if cleaned == "":
            return name_with_spaces.strip()
        
        return cleaned
    except:
        # If any error occurs, return empty string
        return ""


def normalize_special_chars_optimized(text):
    """
    Optimized version with word transpositions commented out for speed
    """
    if not text:
        return ""
        
    try:
        text = str(text).upper()
        
        # Remove leading brackets and braces
        text = re.sub(r'^[\[\(\{]', '', text)
        
        # Replace apostrophes, hyphens and similar characters with empty string
        text = re.sub(r'[\'"`\-]', '', text)
        
        # Replace accented characters with their basic equivalents
        chars_map = {
            'Ø': 'O', 'Ö': 'O', 'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O',
            'Ä': 'A', 'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A',
            'Ë': 'E', 'É': 'E', 'È': 'E', 'Ê': 'E',
            'Ü': 'U', 'Ú': 'U', 'Ù': 'U', 'Û': 'U',
            'Ï': 'I', 'Í': 'I', 'Ì': 'I', 'Î': 'I',
            'Ñ': 'N', 'Ç': 'C'
        }
        for special, basic in chars_map.items():
            text = text.replace(special, basic)
        
        # COMMENTED OUT FOR SPEED - Word transpositions (large dictionary lookup)
        # This is the biggest performance bottleneck - 200+ regex substitutions
        # """
        # word_translations = { **{f'\\b{abbr}\\b': full for abbr, full in [
        #     ('ABBIE', 'ABIGAIL'), ('ABBY', 'ABIGAIL'), ('ABE', 'ABRAHAM'),
        #     # ... (all the word translations)
        # ]}
        # }
        
        # # Apply all word translations
        # for original, replacement in word_translations.items():
        #     text = re.sub(original, replacement, text)
        # """
            
        return text
    except:
        # If any error occurs, return empty string
        return ""


def balance_brackets(text):
    
    if not text:
        return ""
    
    # Define bracket pairs
    bracket_pairs = {
        '(': ')',
        '[': ']',
        '{': '}'
    }
    
    # Set of all opening and closing brackets
    opening_brackets = set(bracket_pairs.keys())
    closing_brackets = set(bracket_pairs.values())
    
    # Stack to track open brackets
    stack = []
    
    # Create a list from the string to make character-by-character modifications
    result = list(text)
    
    # First pass: handle missing closing brackets and extra closing brackets
    i = 0
    while i < len(result):
        char = result[i]
        
        if char in opening_brackets:
            # Found an opening bracket, push to stack
            stack.append((char, i))
        elif char in closing_brackets:
            # Found a closing bracket
            if not stack:
                # Extra closing bracket with no matching opening bracket
                # Remove it
                result[i] = ''
                i += 1
                continue
            else:
                # Check if the closing bracket matches the last opening bracket
                last_open, _ = stack[-1]
                expected_close = bracket_pairs[last_open]
                
                if char == expected_close:
                    # Correct closing bracket, pop from stack
                    stack.pop()
                else:
                    # Wrong type of closing bracket
                    # Replace with the correct closing bracket
                    result[i] = expected_close
                    stack.pop()
        
        i += 1
    
    # After processing, add any missing closing brackets
    while stack:
        open_bracket, open_pos = stack.pop()
        # Add the corresponding closing bracket at the end of the string
        result.append(bracket_pairs[open_bracket])
    
    # Convert result list back to string
    return ''.join(result)


def split_composer_name(name):
    
    if not name:
        return []
    
    # Safely convert to string and uppercase
    try:
        original_name = str(name).upper() if name is not None else ""
        # Remove apostrophes and question marks right away
        name_normalized = original_name.replace("'", "").replace("?", "")
        
        # Balance brackets in the normalized name
        name_normalized = balance_brackets(name_normalized)
    except:
        # If any conversion error, return empty list
        return []
    
    all_parts = []
    
    # First, extract content in brackets
    bracket_contents = []
    # Handle different types of brackets
    bracket_pairs = [
        ('(', ')'),  # parentheses
        ('[', ']'),  # square brackets
        ('{', '}')   # curly brackets
    ]
    
    # Make a copy of the name for bracket processing
    working_name = name_normalized
    
    # Define word delimiters for use throughout the function
    word_delimiters = [
        ' FT ', ' FT. ', ' FEAT ', ' FEAT. ', ' WITH ',' AND ', 
        ' VS ', ' VS. ', ' FEATURING ', ' EN ',
        ' AKA ', ' A.K.A. ', ' AKA. '
    ]
    
    # Add composer-specific delimiters
    composer_delimiters = [
        ' COMPOSER ', ' MUSIC BY ', ' LYRICS BY ', ' WORDS BY ', ' ARRANGEMENT BY ',
        ' CO WRITER ', ' CO COMPOSER ', ' ORIGINALLY BY ', ' WRITTEN BY '
    ]
    word_delimiters.extend(composer_delimiters)
    
    # First extract all bracket contents
    for open_bracket, close_bracket in bracket_pairs:
        # Find all instances of content in this bracket type
        start_pos = working_name.find(open_bracket)
        while start_pos != -1:
            # Find matching closing bracket
            end_pos = working_name.find(close_bracket, start_pos + 1)
            if end_pos != -1:  # Only extract if there's a matching closing bracket
                # Extract the content without the brackets
                bracket_content = working_name[start_pos + 1:end_pos].strip()
                if bracket_content:
                    bracket_contents.append(bracket_content)
                
                # Replace the bracketed content without adding spaces - use empty string
                working_name = working_name[:start_pos] + working_name[end_pos + 1:]
            else:
                # No matching closing bracket, move to next possible opening bracket
                start_pos = working_name.find(open_bracket, start_pos + 1)
                continue
                
            # Look for next bracketed content
            start_pos = working_name.find(open_bracket)
    
    # Normalize the main part (without brackets)
    main_part = working_name.strip()
    main_parts = []  # Initialize main_parts as an empty list
    
    # Flag to determine if we found explicit delimiters in the name
    has_explicit_delimiters = False
    
    if main_part:
        # Process main part with delimiters
        # Define character delimiters
        delimiters = ['|', '/', '#', '\\', ',', ';', '`', '_', '&', '+']
        
        # Add spaces for word boundary detection
        main_with_boundaries = ' ' + main_part + ' '
        
        # Check if any delimiters are present in the name
        for d in delimiters:
            if d in main_with_boundaries:
                has_explicit_delimiters = True
                break
        
        if not has_explicit_delimiters:
            for wd in word_delimiters:
                if wd in ' ' + main_with_boundaries + ' ':
                    has_explicit_delimiters = True
                    break
        
        # Replace all delimiters with a standard one
        for d in delimiters:
            main_with_boundaries = main_with_boundaries.replace(d, '|')
        
        # Replace word delimiters
        for wd in word_delimiters:
            if wd in main_with_boundaries:
                main_with_boundaries = main_with_boundaries.replace(wd, '|')
        
        # Split and add to parts
        main_parts = [part.strip() for part in main_with_boundaries.split('|') if part.strip()]
        for part in main_parts:
            clean_part = normalize_special_chars_optimized(part)  # Using optimized version
            if clean_part and len(clean_part) > 1:
                all_parts.append(clean_part)
    
    # Process each bracket content with improved handling for "WITH" and other delimiters
    for content in bracket_contents:
        # First check if content starts with a delimiter word
        delimiter_word_at_start = None
        for delimiter_word in ['WITH', 'FEAT', 'FEAT.', 'FT', 'FT.', 'AND', 'FEATURING', 
                              'COMPOSER', 'MUSIC BY', 'LYRICS BY', 'WRITTEN BY']:
            # Need to check with word boundaries (space after it)
            if content.startswith(delimiter_word + ' '):
                delimiter_word_at_start = delimiter_word
                break
        
        if delimiter_word_at_start:
            # Content starts with a delimiter - remove it and process the rest
            rest_of_content = content[len(delimiter_word_at_start):].strip()
            
            # Check for additional delimiters in the rest of content
            has_more_delimiters = False
            
            # Check for character delimiters
            for d in ['|', '/', ',', '&', '+', '-']:
                if d in rest_of_content:
                    has_more_delimiters = True
                    break
            
            # Check for word delimiters
            if not has_more_delimiters:
                for wd in [' AND ', ' WITH ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ']:
                    if wd in f" {rest_of_content} ":
                        has_more_delimiters = True
                        break
            
            if has_more_delimiters:
                # Replace delimiters with standard one
                cleaned = rest_of_content
                for d in ['|', '/', ',', '&', '+', '-']:
                    cleaned = cleaned.replace(d, '|')
                
                # Replace word delimiters
                for wd in [' AND ', ' WITH ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ']:
                    if wd in f" {cleaned} ":
                        cleaned = cleaned.replace(wd.strip(), '|')
                
                # Split and add parts
                for part in cleaned.split('|'):
                    part = part.strip()
                    if part:
                        clean_part = normalize_special_chars_optimized(part)  # Using optimized version
                        if clean_part and len(clean_part) > 1:
                            all_parts.append(clean_part)
            else:
                # No more delimiters - add the whole rest of content
                clean_part = normalize_special_chars_optimized(rest_of_content)  # Using optimized version
                if clean_part and len(clean_part) > 1:
                    all_parts.append(clean_part)
        else:
            # No delimiter at start, check if content contains delimiters
            has_delimiter = False
            
            # Check character delimiters
            for d in ['|', '/', ',', '&', '+', '-']:
                if d in content:
                    has_delimiter = True
                    break
            
            # Check word delimiters
            if not has_delimiter:
                for wd in [' AND ', ' WITH ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ']:
                    if wd in f" {content} ":
                        has_delimiter = True
                        break
            
            if has_delimiter:
                # Content has delimiters - process with standard delimiter handling
                cleaned = content
                for d in ['|', '/', ',', '&', '+', '-']:
                    cleaned = cleaned.replace(d, '|')
                
                # Replace word delimiters
                for wd in [' AND ', ' WITH ', ' FT ', ' FT. ', ' FEAT ', ' FEAT. ']:
                    if wd in f" {cleaned} ":
                        cleaned = cleaned.replace(wd.strip(), '|')
                
                # Split and add parts
                for part in cleaned.split('|'):
                    part = part.strip()
                    if part:
                        clean_part = normalize_special_chars_optimized(part)  # Using optimized version
                        if clean_part and len(clean_part) > 1:
                            all_parts.append(clean_part)
            else:
                # No delimiters - add the whole content
                clean_part = normalize_special_chars_optimized(content)  # Using optimized version
                if clean_part and len(clean_part) > 1:
                    all_parts.append(clean_part)
    
    # Check for name reversals (ONLY if we have exactly 2 main parts and no explicit delimiters)
    if len(main_parts) == 2 and not has_explicit_delimiters:
        reversed_name = f"{main_parts[1]} {main_parts[0]}"
        clean_reversed = normalize_special_chars_optimized(reversed_name)  # Using optimized version
        if clean_reversed and clean_reversed != normalize_special_chars_optimized(main_part):
            all_parts.append(clean_reversed)
    
    # Special case for single names: ensure we include the full name as a part
    if len(all_parts) == 0 and main_part:
        clean_full_name = normalize_special_chars_optimized(main_part)  # Using optimized version
        if clean_full_name and len(clean_full_name) > 1:
            all_parts.append(clean_full_name)
    
    # If this is a single name (e.g., "MICHAEL JACKSON"), make sure it's included in the list
    # Only if it's not already included as a result of the delimiter splitting
    if len(main_parts) == 1 and main_part:
        clean_full_name = normalize_special_chars_optimized(main_part)  # Using optimized version
        if clean_full_name and len(clean_full_name) > 1:
            if clean_full_name not in all_parts:
                all_parts.append(clean_full_name)
    
    # Remove duplicates and ensure all parts are clean
    unique_parts = []
    seen = set()
    for part in all_parts:
        # Final cleaning to ensure consistency
        clean_part = part.replace('(', '').replace(')', '').replace('?', '')
        if clean_part and clean_part not in seen and len(clean_part) > 1:
            seen.add(clean_part)
            unique_parts.append(clean_part)
    
    return unique_parts


def preprocess_adc_dataframe_vectorized(df, name_col='COMPOSER_NAME', id_col='ADC_COMPOSER_ID', batch_size=10000):

    df_pandas = df.to_pandas()
    total_rows = len(df_pandas)
    
    print(f"Processing {total_rows} rows in vectorized mode...")
    
    # Fill any None values with empty strings to prevent errors
    df_pandas[name_col] = df_pandas[name_col].fillna("")
    
    # Vectorized operations using pandas
    print("Applying clean_composer_name...")
    df_pandas['CLEAN_NAME'] = df_pandas[name_col].apply(clean_composer_name)
    
    print("Applying normalize_special_chars_optimized...")
    df_pandas['NORMALIZED_NAME'] = df_pandas[name_col].apply(normalize_special_chars_optimized)
    
    print("Applying split_composer_name...")
    df_pandas['DELIMITED_PARTS'] = df_pandas[name_col].apply(split_composer_name)
    
    # Convert back to Snowpark DataFrame
    result_df = df.session.create_dataframe(df_pandas)
    
    return result_df


def create_expanded_adc_dataframe_vectorized(df, name_col='COMPOSER_NAME', id_col='ADC_COMPOSER_ID', batch_size=10000):

    # Convert to pandas for processing
    df_pandas = df.to_pandas()
    total_rows = len(df_pandas)
    
    print(f"Expanding {total_rows} rows in vectorized mode...")
    
    expanded_rows = []
    
    # Process all rows at once using vectorized operations where possible
    for idx, row in df_pandas.iterrows():
        # Add the original name row with apostrophes preserved
        original_row = row.to_dict()
        original_row['IS_VARIANT'] = 'ORIGINAL'
        expanded_rows.append(original_row)
        
        # Skip if there are no delimited parts or DELIMITED_PARTS column doesn't exist
        if 'DELIMITED_PARTS' not in row or not row['DELIMITED_PARTS']:
            continue
        
        # Safely convert the original name to uppercase for comparison
        original_name_upper = ""
        if row[name_col] is not None:
            original_name_upper = str(row[name_col]).upper().replace("'", "")
        
        # Add a row for each delimited part
        for part in row['DELIMITED_PARTS']:
            # Only add if the part is different from the original name
            # and is substantial (more than 2 characters)
            if part and part != original_name_upper and len(part) > 2:
                variant_row = row.to_dict()
                variant_row[name_col] = part
                variant_row['CLEAN_NAME'] = clean_composer_name(part)
                variant_row['MUZOOKA_TRACK_ID'] = row['MUZOOKA_TRACK_ID']
                variant_row['NORMALIZED_NAME'] = normalize_special_chars_optimized(part)  # Using optimized version
                variant_row['IS_VARIANT'] = 'VARIANT'
                # Don't include DELIMITED_PARTS in variant rows
                variant_row['DELIMITED_PARTS'] = []
                expanded_rows.append(variant_row)
    
    # Create DataFrame from expanded rows
    expanded_df = pd.DataFrame(expanded_rows)
    
    # Convert back to Snowpark DataFrame
    result_df = df.session.create_dataframe(expanded_df)
    
    return result_df


def filter_adc_by_work_ids(session, table_name, work_ids):
    """
    Filter ADC data by work IDs
    """
    # Create a formatted string of work IDs for the SQL query
    work_ids_str = ", ".join([f"'{work_id}'" for work_id in work_ids])
    
    # Query with filter
    query = f"""
    SELECT * 
    FROM {table_name}
    WHERE APRA_WORK_ID IN ({work_ids_str})
    """
    
    # Execute query and return results
    return session.sql(query)


def process_adc_composers_optimized(session, mode="example", work_ids=None, sample_percentage=1):
    
    print(f"=== OPTIMIZED ADC COMPOSER PROCESSING ===")
    print(f"Running in {mode} mode")
    
    if mode == "example":
        # Create example ADC data
        print("Creating example ADC data...")
        adc_examples = pd.DataFrame({
            'APRA_WORK_ID': ['GW123456', 'GW234567', 'GW345678', 'GW456789', 'GW567891', 'GW678912', 'GW789123'],
            'COMPOSER_NAME': [
                'JOHN LENNON',
                'LUDWIG VAN BEETHOVEN | FRANZ LISZT (ARRANGED BY)',
                'ANDREW LLOYD WEBBER & TIM RICE',
                "RACHMANINOV'S SERGEI",
                'TRADITIONAL (ARR. TRAD)',
                'BOB DYLAN (LYRICS BY JOHNNY CASH)',
                'FREDDIE MERCURY (QUEEN)'
            ],
            'ADC_COMPOSER_ID': ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7'],
            'IPI': ['00123456789', '00287654321', '00398765432', '00456789123', '00567891234', '00678912345', '00789123456']
        })
        
        # Convert to Snowpark DataFrame
        adc_df = session.create_dataframe(adc_examples)
        
        # Preprocess ADC data using vectorized operations
        print("\nPreprocessing ADC composer data (VECTORIZED)...")
        adc_preprocessed = preprocess_adc_dataframe_vectorized(adc_df)
        
        # Create expanded ADC dataframe using vectorized operations
        print("\nCreating expanded ADC dataframe (VECTORIZED)...")
        adc_expanded = create_expanded_adc_dataframe_vectorized(adc_preprocessed)
        
        # Display results
        print("\nPreprocessed ADC Data:")
        adc_preprocessed_pandas = adc_preprocessed.to_pandas()
        for _, row in adc_preprocessed_pandas.iterrows():
            print(f"ID: {row['ADC_COMPOSER_ID']}, Name: {row['COMPOSER_NAME']}, IPI: {row['IPI']}")
            print(f"  Clean Name: {row['CLEAN_NAME']}")
            print(f"  Normalized Name: {row['NORMALIZED_NAME']}")
            print(f"  Delimited Parts: {row['DELIMITED_PARTS']}")
            print()
            
        print("\nExpanded ADC Data:")
        adc_expanded_pandas = adc_expanded.to_pandas()
        for _, row in adc_expanded_pandas.iterrows():
            print(f"ID: {row['ADC_COMPOSER_ID']}, Name: {row['COMPOSER_NAME']}, IPI: {row['IPI']}, Variant: {row['IS_VARIANT']}")
            print(f"  Clean Name: {row['CLEAN_NAME']}")
            print()
        
        return adc_expanded
        
    elif mode == "subset":
        # Process subset of ADC data with optimizations
        print(f"Running with {sample_percentage}% of ADC data using SQL SAMPLE (OPTIMIZED)")
        
        # Define table names
        adc_table = "EDW_APPS.MATCHING.ADC_WORKS_TRACKS_MATCHED_COMPOSERS"
        
        # Intermediate and final tables
        adc_preprocessed_table = "EDW_APPS.MATCHING.ADC_COMPOSERS_PREPROCESSED_TEMP_CLEAN"
        adc_expanded_table = "EDW_APPS.MATCHING.ADC_COMPOSERS_EXPANDED_CLEAN"
        
        try:
            # Use SQL SAMPLE clause
            adc_query = f"SELECT * FROM {adc_table} SAMPLE ({sample_percentage})"
            
            print(f"Executing query: {adc_query}")
            adc_df = session.sql(adc_query)
            adc_count = adc_df.count()
            print(f"ADC sample contains {adc_count} rows")
            
            if adc_count == 0:
                print("Warning: ADC DataFrame is empty. This might cause issues in processing.")
                return None
            
            # Step 1: Preprocess ADC data using vectorized operations
            print("\nPreprocessing ADC composer data (VECTORIZED)...")
            adc_preprocessed = preprocess_adc_dataframe_vectorized(adc_df, batch_size=20000)
            
            # Save intermediate results
            print(f"Saving preprocessed ADC data to {adc_preprocessed_table}...")
            adc_preprocessed.write.mode("overwrite").save_as_table(adc_preprocessed_table)
            
            # Step 2: Create expanded ADC dataframe using vectorized operations
            print("\nCreating expanded ADC dataframe (VECTORIZED)...")
            adc_preprocessed = session.table(adc_preprocessed_table)
            adc_expanded = create_expanded_adc_dataframe_vectorized(adc_preprocessed, batch_size=20000)
            
            # Save final ADC results
            print(f"Saving expanded ADC data to {adc_expanded_table}...")
            adc_expanded.write.mode("overwrite").save_as_table(adc_expanded_table)
            
            # Clean up intermediate tables
            print("\nCleaning up intermediate tables...")
            session.sql(f"DROP TABLE IF EXISTS {adc_preprocessed_table}").collect()
            
            print("Optimized ADC preprocessing completed successfully!")
            print(f"Final results: {adc_count} ADC composers processed")
            
            return adc_expanded
            
        except Exception as e:
            print(f"Error during ADC processing: {str(e)}")
            print("Stack trace:")
            import traceback
            traceback.print_exc()
            return None
            
    elif mode == "full":
        # Process full ADC dataset with optimizations
        print("Running with FULL ADC dataset (OPTIMIZED)...")
        
        # Define table names
        adc_table = "EDW_APPS.MATCHING.ADC_WORKS_NON_EXACT_MATCH_COMPOSER_NAMES"
        
        # Intermediate and final tables
        adc_preprocessed_table = "EDW_APPS.MATCHING.ADC_COMPOSERS_PREPROCESSED_TEMP"
        adc_expanded_table = "EDW_APPS.MATCHING.ADC_COMPOSERS_EXPANDED"
        
        # Read from Snowflake table
        print("Reading ADC data from Snowflake table...")
        adc_df = session.table(adc_table)
        
        adc_count = adc_df.count()
        print(f"ADC dataset contains {adc_count} rows")
        
        # Step 1: Preprocess ADC data using vectorized operations
        print("\nPreprocessing ADC composer data (VECTORIZED FULL DATASET)...")
        adc_preprocessed = preprocess_adc_dataframe_vectorized(adc_df, batch_size=20000)
        
        # Save intermediate results
        print(f"Saving preprocessed ADC data to {adc_preprocessed_table}...")
        adc_preprocessed.write.mode("overwrite").save_as_table(adc_preprocessed_table)
        
        # Step 2: Create expanded ADC dataframe using vectorized operations
        print("\nCreating expanded ADC dataframe (VECTORIZED FULL DATASET)...")
        adc_preprocessed = session.table(adc_preprocessed_table)
        adc_expanded = create_expanded_adc_dataframe_vectorized(adc_preprocessed, batch_size=20000)
        
        # Save final ADC results
        print(f"Saving expanded ADC data to {adc_expanded_table}...")
        adc_expanded.write.mode("overwrite").save_as_table(adc_expanded_table)
        
        # Clean up intermediate tables
        print("\nCleaning up intermediate tables...")
        session.sql(f"DROP TABLE IF EXISTS {adc_preprocessed_table}").collect()
        
        print("Optimized ADC preprocessing completed successfully!")
        print(f"Final results: {adc_count} ADC composers processed")
        
        return adc_expanded
    
    elif mode == "work":
        # Process specific work IDs with optimizations
        if not work_ids or len(work_ids) == 0:
            print("No work IDs provided. Please provide a list of APRA_WORK_ID values.")
            return None
            
        print(f"Running for {len(work_ids)} specific APRA work IDs: {work_ids} (OPTIMIZED)")
        
        # Define table names
        adc_table = "EDW_APPS.MATCHING.ADC_WORKS_TRACKS_MATCHED_COMPOSERS"
        
        # Intermediate and final tables
        adc_preprocessed_table = "EDW_APPS.MATCHING.ADC_COMPOSERS_PREPROCESSED_WORK_TEMP"
        adc_expanded_table = "EDW_APPS.MATCHING.ADC_COMPOSERS_EXPANDED"
        
        # Filter data for the specified work IDs
        print("Filtering ADC data for specified work IDs...")
        adc_df = filter_adc_by_work_ids(session, adc_table, work_ids)
        
        adc_count = adc_df.count()
        print(f"Filtered ADC data contains {adc_count} rows")
        
        if adc_count == 0:
            print("Warning: No records found in ADC data for the specified work IDs.")
            return None
            
        # Step 1: Preprocess ADC data using vectorized operations
        print("\nPreprocessing ADC composer data (VECTORIZED)...")
        adc_preprocessed = preprocess_adc_dataframe_vectorized(adc_df, batch_size=5000)
        
        # Save intermediate results
        print(f"Saving preprocessed ADC data to {adc_preprocessed_table}...")
        adc_preprocessed.write.mode("overwrite").save_as_table(adc_preprocessed_table)
        
        # Step 2: Create expanded ADC dataframe using vectorized operations
        print("\nCreating expanded ADC dataframe (VECTORIZED)...")
        adc_preprocessed = session.table(adc_preprocessed_table)
        adc_expanded = create_expanded_adc_dataframe_vectorized(adc_preprocessed, batch_size=5000)
        
        # Save final ADC results
        print(f"Saving expanded ADC data to {adc_expanded_table}...")
        adc_expanded.write.mode("overwrite").save_as_table(adc_expanded_table)
        
        # Clean up intermediate tables
        print("\nCleaning up intermediate tables...")
        session.sql(f"DROP TABLE IF EXISTS {adc_preprocessed_table}").collect()
        
        print("Optimized ADC preprocessing for specific work IDs completed successfully!")
        print(f"Final results: {adc_count} ADC composers processed")
        
        return adc_expanded

        
if __name__ == "__main__":
    # Example usage
    work_ids = ['GW00577031']
    
    # Process ADC composers with optimizations
    result = process_adc_composers_optimized(session, mode="subset", sample_percentage=1)