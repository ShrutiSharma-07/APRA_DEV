import re
import pandas as pd

# Title variant generation functions
articles = ['a', 'an', 'the']

def is_article(word: str) -> bool:
    return word.lower() in articles


def remove_articles(title: str) -> str:
    # Remove leading and trailing articles
    words = title.strip().split()
    if words and is_article(words[0]):
        words = words[1:]
    if words and is_article(words[-1]):
        words = words[:-1]
    return ' '.join(words)


def normalize_whitespace(title: str) -> str:
    # Normalize whitespaces
    return re.sub(r'\s+', ' ', title.strip())


def clean_unmatched_brackets(title: str) -> str:
    """Remove unmatched brackets from a title"""
    # Check for balanced brackets
    stack = []
    bracket_pairs = {'(': ')', '[': ']', '{': '}'}
    reverse_pairs = {')': '(', ']': '[', '}': '{'}

    # First pass - remove unmatched brackets
    cleaned_title = ""
    skip_indices = set()

    for i, char in enumerate(title):
        if char in bracket_pairs:  # Opening bracket
            stack.append((char, i))
        elif char in reverse_pairs:  # Closing bracket
            if stack and stack[-1][0] == reverse_pairs[char]:
                stack.pop()  # Matched pair
            else:
                # Unmatched closing bracket - mark for removal
                skip_indices.add(i)

    # Any remaining opening brackets are unmatched
    for _, idx in stack:
        skip_indices.add(idx)

    # Build cleaned title without unmatched brackets
    for i, char in enumerate(title):
        if i not in skip_indices:
            cleaned_title += char

    return normalize_whitespace(cleaned_title)


def identify_bracket_groups(cleaned_title):
    """
    Identify groups of brackets in the title.
    A group is defined as adjacent brackets with no text in between.
    Returns a list of (start_idx, end_idx, [bracket_matches]) for each group.
    """
    bracket_pattern = r'([\[\(\{])([^\[\]\(\)\{\}]*)([\]\)\}])'
    bracket_matches = list(re.finditer(bracket_pattern, cleaned_title))

    if not bracket_matches:
        return []

    # Sort matches by start position
    bracket_matches.sort(key=lambda m: m.start())

    # Group adjacent brackets
    groups = []
    current_group = [bracket_matches[0]]

    for i in range(1, len(bracket_matches)):
        prev_end = bracket_matches[i - 1].end()
        current_start = bracket_matches[i].start()

        # Check if there's text between brackets
        if cleaned_title[prev_end:current_start].strip():
            # Non-adjacent brackets, start a new group
            groups.append((current_group[0].start(), current_group[-1].end(), current_group))
            current_group = [bracket_matches[i]]
        else:
            # Adjacent brackets, add to current group
            current_group.append(bracket_matches[i])

    # Add the last group
    groups.append((current_group[0].start(), current_group[-1].end(), current_group))

    return groups


def generate_title_variants(title: str) -> list:
    """Generate title variants with proper handling of bracket groups"""
    original_title = title.strip()
    cleaned_title = clean_unmatched_brackets(original_title)
    variants = set()

    # Find all matched brackets in the cleaned title
    bracket_pattern = r'([\[\(\{])([^\[\]\(\)\{\}]*)([\]\)\}])'
    bracket_matches = list(re.finditer(bracket_pattern, cleaned_title))

    # If no brackets, just return empty list (no variants)
    # If no brackets left after cleaning (which means any brackets were unmatched and removed)
    if not bracket_matches:
        # Check if original title had any brackets at all
        if any(char in original_title for char in '[](){}'):
            clean_title = remove_articles(cleaned_title)
            if clean_title:  # Only add non-empty titles
                variants.add(clean_title)
        else:
            # Original didn't have brackets, so no variants needed
            pass
        return sorted(list(variants))
    # Create a variant with all brackets completely removed
    no_brackets = re.sub(bracket_pattern, '', cleaned_title)
    no_brackets = normalize_whitespace(no_brackets)
    no_brackets = remove_articles(no_brackets)
    if no_brackets and no_brackets.lower() != remove_articles(original_title.lower()):
        variants.add(no_brackets)

    # Identify bracket groups (adjacent brackets)
    bracket_groups = identify_bracket_groups(cleaned_title)

    # Split the title into segments: text segments and bracket groups
    segments = []
    last_end = 0

    for group_start, group_end, group_matches in bracket_groups:
        # Add text before this group
        if group_start > last_end:
            segments.append(('text', cleaned_title[last_end:group_start]))

        # Add this bracket group
        segments.append(('group', group_matches))

        # Update last_end
        last_end = group_end

    # Add any remaining text after the last bracket group
    if last_end < len(cleaned_title):
        segments.append(('text', cleaned_title[last_end:]))

    # Now create variants based on rules

    # 1. Variant with first bracket of first group only
    first_variant_parts = []

    for segment_type, segment_content in segments:
        if segment_type == 'text':
            first_variant_parts.append(segment_content)
        elif segment_type == 'group':
            # Add only first bracket content from first group
            first_variant_parts.append(segment_content[0].group(2))

    first_variant = normalize_whitespace(' '.join(first_variant_parts))
    first_variant = remove_articles(first_variant)

    if first_variant and first_variant not in variants and first_variant.lower() != remove_articles(
            original_title.lower()):
        variants.add(first_variant)

    # 2. If there are multiple groups, create a variant with first bracket of first group
    # and first bracket of last group
    if len(bracket_groups) > 1:
        second_variant_parts = []
        first_group_used = False
        last_group_used = False

        for segment_type, segment_content in segments:
            if segment_type == 'text':
                second_variant_parts.append(segment_content)
            elif segment_type == 'group':
                if not first_group_used and segment_content == bracket_groups[0][2]:
                    # First group - add only first bracket content
                    second_variant_parts.append(segment_content[0].group(2))
                    first_group_used = True
                elif not last_group_used and segment_content == bracket_groups[-1][2]:
                    # Last group - add only first bracket content if it's different from first group
                    if bracket_groups[0] != bracket_groups[-1]:
                        second_variant_parts.append(segment_content[0].group(2))
                        last_group_used = True

        second_variant = normalize_whitespace(' '.join(second_variant_parts))
        second_variant = remove_articles(second_variant)

        if second_variant and second_variant not in variants and second_variant.lower() != remove_articles(
                original_title.lower()):
            variants.add(second_variant)

    # 3. If there are multiple groups, create a variant with just text and first bracket of last group
    if len(bracket_groups) > 1:
        third_variant_parts = []
        last_group_used = False

        for segment_type, segment_content in segments:
            if segment_type == 'text':
                third_variant_parts.append(segment_content)
            elif segment_type == 'group' and not last_group_used and segment_content == bracket_groups[-1][2]:
                # Last group - add only first bracket content
                third_variant_parts.append(segment_content[0].group(2))
                last_group_used = True

        third_variant = normalize_whitespace(' '.join(third_variant_parts))
        third_variant = remove_articles(third_variant)

        if third_variant and third_variant not in variants and third_variant.lower() != remove_articles(
                original_title.lower()):
            variants.add(third_variant)

    # 4. Handle titles that start with a bracket
    if bracket_matches and bracket_matches[0].start() == 0:
        # Get just the content of the first bracket
        bracket_content = normalize_whitespace(bracket_matches[0].group(2))
        rest_of_title = cleaned_title[bracket_matches[0].end():]

        # Remove all other brackets
        rest_of_title = re.sub(bracket_pattern, '', rest_of_title)
        rest_of_title = normalize_whitespace(rest_of_title)

        # Create variant with just bracket content + rest of title
        combined = normalize_whitespace(f"{bracket_content} {rest_of_title}")
        combined = remove_articles(combined)

        if combined and combined not in variants and combined.lower() != remove_articles(original_title.lower()):
            variants.add(combined)

        # Also create a variant with just the bracket content if it's followed by more brackets
        if len(bracket_matches) > 1 and bracket_matches[1].start() == bracket_matches[0].end():
            just_content = remove_articles(bracket_content)
            if just_content and just_content not in variants and just_content.lower() != remove_articles(
                    original_title.lower()):
                variants.add(just_content)

    # 5. Specific handling for the complex case
    # For titles like "(NEW WORLD) (HI) HELLO (SMILE TIME) WORLD (TIME) (XXXX)"
    if len(bracket_groups) >= 2:

        middle_brackets = []
        for match in bracket_matches:
            is_in_group = False
            for _, _, group_matches in bracket_groups:
                if match in group_matches:
                    is_in_group = True
                    break
            if not is_in_group:
                middle_brackets.append(match)

        # If we have a complex pattern with middle brackets
        if middle_brackets:
            # Create variant with first group content + middle brackets + last group content
            complex_variant_parts = []
            base_text_added = False

            # Add first group content
            complex_variant_parts.append(bracket_groups[0][2][0].group(2))

            # Add base text
            base_text = re.sub(bracket_pattern, '', cleaned_title)
            complex_variant_parts.append(base_text)
            base_text_added = True

            # Add content from middle brackets
            for middle_match in middle_brackets:
                complex_variant_parts.append(middle_match.group(2))

            # Add last group content (first bracket only)
            complex_variant_parts.append(bracket_groups[-1][2][0].group(2))

            complex_variant = normalize_whitespace(' '.join(complex_variant_parts))
            complex_variant = remove_articles(complex_variant)

            if complex_variant and complex_variant not in variants and complex_variant.lower() != remove_articles(
                    original_title.lower()):
                variants.add(complex_variant)

            # Also create variant with base text + last group content
            if not base_text_added:
                base_variant_parts = [base_text, bracket_groups[-1][2][0].group(2)]
                base_variant = normalize_whitespace(' '.join(base_variant_parts))
                base_variant = remove_articles(base_variant)

                if base_variant and base_variant not in variants and base_variant.lower() != remove_articles(
                        original_title.lower()):
                    variants.add(base_variant)

    return sorted(list(variants))


def print_example_results():
    test_examples = [
        "(NEW WORLD) (HI) HELLO (SMILE TIME) WORLD (TIME) (XXXX)",
        "a thousand years [pt. 2] [the twilight saga: breaking dawn soundtrack]",
        "[hey brother]",
        "[hello] hey brother",
        "hey brother [hello]",
        "[hello] [hi] hey brother",
        "waka waka this time for africa [the official 2010 fifa world cup tm song] single",
        "stay don't go away [",
        "don't stop (color on the walls)",
        "the a team",
    ]

    print("\n" + "=" * 80)
    print("EXAMPLE RESULTS BEFORE PROCESSING".center(80))
    print("=" * 80)

    for example in test_examples:
        print(f"\nOriginal title: \"{example}\"")
        print(f"After cleaning unmatched brackets: \"{clean_unmatched_brackets(example)}\"")
        variants = generate_title_variants(example)

        if variants:
            print("Generated variants:")
            for i, variant in enumerate(variants, 1):
                print(f"  {i}. \"{variant}\"")
        else:
            print("No variants generated")
        print("-" * 60)

    print("=" * 80 + "\n")


def process_muzooka_tracks(input_file_path, output_file_path):
    # First, print example results
    print_example_results()
    df = pd.read_csv(input_file_path,dtype=str,low_memory=False)

    print(f"Loaded {len(df)} tracks from {input_file_path}")

    # Step 2: Create indicator columns for titles with brackets and hyphens
    # Include all types of brackets: (), [], {}
    df['has_brackets'] = df['Title'].str.contains(r'[\[\]\(\)\{\}]', regex=True, na=False)
    df['has_hyphens'] = df['Title'].str.contains(r'-', regex=True, na=False)

    # Step 3: Standardize all columns: lowercase + strip whitespace
    for col in df.columns:
        if df[col].dtype == object:  # Only process string columns
            df[col] = df[col].astype(str).str.lower().str.strip()

    # Step 4: Clean ISWC column to remove all non-alphanumeric characters
    df['ISWC'] = df['ISWC'].apply(lambda x: re.sub(r'[^a-zA-Z0-9]', '', x))

    # Step 5: Generate title variants and create expanded dataframe
    expanded_rows = []

    # Print some example rows from the dataset
    print("\nExample rows from dataset:")
    sample_rows = min(5, len(df))
    for i in range(sample_rows):
        title = df.iloc[i]['Title']
        variants = generate_title_variants(title)
        print(f"\nOriginal: {title}")
        print(f"Variants: {variants}")

    # Modify the expanded_rows creation section as follows:
    for index, row in df.iterrows():
        if index % 1000 == 0:
            print(f"Processing row {index} of {len(df)}")

        original_title = row['Title']

        # Get title variants
        variants = generate_title_variants(original_title)

        # Add the original row (with Original_Title)
        original_row = row.copy()
        original_row['Original_Title'] = original_title

        if variants:
            # If we have variants, don't include the original in Title_Variant
            original_row['Title_Variant'] = None  # or use empty string
            original_row['Is_Variant'] = False
            expanded_rows.append(original_row)

            # Add a row for each variant
            for variant in variants:
                variant_row = row.copy()
                variant_row['Original_Title'] = original_title
                variant_row['Title_Variant'] = variant
                variant_row['Is_Variant'] = True
                expanded_rows.append(variant_row)
        else:
            # No variants found, so keep original title in both columns
            original_row['Title_Variant'] = original_title
            original_row['Is_Variant'] = False
            expanded_rows.append(original_row)

    expanded_df = pd.DataFrame(expanded_rows)
    expanded_df.to_excel(output_file_path, index=False)

    print(f"Processed {len(df)} original tracks into {len(expanded_df)} rows (including variants)")
    print(f"Data saved to {output_file_path}")

    return expanded_df

if __name__ == "__main__":
    input_path = r"C:\Users\Shruti Sharma\Desktop\APRA Data Cleanup\muzooka_tracks.csv"
    output_path = r"C:\Users\Shruti Sharma\Desktop\APRA Data Cleanup\muzooka_tracks_with_variants.xlsx"

    result_df = process_muzooka_tracks(input_path, output_path)

    # Display stats
    original_count = len(result_df[result_df['Is_Variant'] == False])
    variant_count = len(result_df[result_df['Is_Variant'] == True])

    print(f"\nSummary:")
    print(f"Original tracks: {original_count}")
    print(f"Generated variants: {variant_count}")
    print(f"Total rows in output: {len(result_df)}")


