import re

articles = ['A', 'AN', 'THE']
def is_article(word: str) -> bool:
    return word.upper() in articles

def remove_articles(title: str) -> str:
    #Remove leading and trailing articles
    words = title.strip().split()
    if words and is_article(words[0]):
        words = words[1:]
    if words and is_article(words[-1]):
        words = words[:-1]
    return ' '.join(words)

def normalize_whitespace(title: str) -> str:
    #Normalize whitespaces
    return re.sub(r'\s+', ' ', title.strip())

def generate_title_variants(title: str) -> list:
    title = title.strip()
    variants = set()

    # Base title with all brackets removed
    base_title = re.sub(r'\([^()]*\)', '', title).strip()
    base_title = normalize_whitespace(base_title)
    variants.add(remove_articles(base_title))

    # Handle leading brackets
    leading_content = None
    leading_match = re.match(r'^\s*\(([^()]*)\)', title)

    if leading_match:
        content = leading_match.group(1).strip()
        # Check if first bracket contains an article
        if content.upper() in articles:
            # If it's an article, try to use the second bracket instead
            remainder = title[leading_match.end():].strip()
            second_match = re.match(r'^\s*\(([^()]*)\)', remainder)
            if second_match:
                leading_content = second_match.group(1).strip()
        else:
            # Not an article, use the first bracket content
            leading_content = content

        # Create variant with leading content
        if leading_content and leading_content.upper() not in articles:
            leading_variant = f"{leading_content} {base_title}"
            leading_variant = normalize_whitespace(leading_variant)
            variants.add(remove_articles(leading_variant))

    # Handle trailing brackets - find first bracket from the end
    # First remove all leading brackets to find true end content
    no_leading = title
    if leading_match:
        # Skip all consecutive leading brackets
        pattern = r'^\s*(?:\([^()]*\)\s*)+'
        leading_sequence = re.match(pattern, no_leading)
        if leading_sequence:
            no_leading = no_leading[leading_sequence.end():].strip()

    trailing_content = None
    trailing_match = re.search(r'\(([^()]*)\)\s*(?:\([^()]*\)\s*)*$', no_leading)

    if trailing_match:
        trailing_content = trailing_match.group(1).strip()

        # Create variant with trailing content
        if trailing_content and trailing_content.upper() not in articles:
            trailing_variant = f"{base_title} {trailing_content}"
            trailing_variant = normalize_whitespace(trailing_variant)
            variants.add(remove_articles(trailing_variant))

    # Create variant with both leading and trailing content
    if (leading_content and trailing_content and leading_content.upper()
            not in articles and trailing_content.upper() not in articles):

        both_variant = f"{leading_content} {base_title} {trailing_content}"
        both_variant = normalize_whitespace(both_variant)
        variants.add(remove_articles(both_variant))

    # Find middle brackets
    # First, create a modified title without leading and trailing brackets
    modified_title = title

    # Remove leading brackets
    if leading_match:
        pattern = r'^\s*(?:\([^()]*\)\s*)+'
        leading_sequence = re.match(pattern, modified_title)
        if leading_sequence:
            modified_title = modified_title[leading_sequence.end():].strip()

    # Remove trailing brackets
    if trailing_match:
        pattern = r'\s*(?:\([^()]*\)\s*)+$'
        trailing_sequence = re.search(pattern, modified_title)
        if trailing_sequence:
            modified_title = modified_title[:trailing_sequence.start()].strip()

    # Find the first middle bracket in the remaining text
    middle_match = re.search(r'\(([^()]*)\)', modified_title)

    if middle_match:
        middle_content = middle_match.group(1).strip()

        if middle_content and middle_content.upper() not in articles:
            # Split the base title into words
            base_words = base_title.split()

            # Find position to insert middle content
            title_before_bracket = modified_title[:middle_match.start()]
            # Remove any brackets in the title before
            title_before_without_brackets = re.sub(r'\([^()]*\)', '', title_before_bracket)
            word_count = len(title_before_without_brackets.strip().split())

            # My middle variant lol
            if word_count < len(base_words):
                middle_variant = ' '.join(base_words[:word_count]) + ' ' + middle_content + ' ' + ' '.join(
                    base_words[word_count:])
            else:
                middle_variant = base_title + ' ' + middle_content

            middle_variant = normalize_whitespace(middle_variant)
            variants.add(remove_articles(middle_variant))

            # Variants with middle content and leading/trailing content
            if leading_content and leading_content.upper() not in articles:
                leading_middle_variant = f"{leading_content} {middle_variant}"
                leading_middle_variant = normalize_whitespace(leading_middle_variant)
                variants.add(remove_articles(leading_middle_variant))

            if trailing_content and trailing_content.upper() not in articles:
                middle_trailing_variant = f"{middle_variant} {trailing_content}"
                middle_trailing_variant = normalize_whitespace(middle_trailing_variant)
                variants.add(remove_articles(middle_trailing_variant))

            # Special case for example 10
            if (leading_content and trailing_content and leading_content.upper()
                    not in articles and trailing_content.upper() not in articles):

                all_variant = f"{leading_content} {middle_variant} {trailing_content}"
                all_variant = normalize_whitespace(all_variant)
                variants.add(remove_articles(all_variant))

    return sorted(list(variants))


def test_title(title):
    """Test function to display variants for a given title."""
    print(f"\nAPRA Title: {title}")
    print("Variants:")
    for variant in generate_title_variants(title):
        print(f"  - {variant}")


# Test with examples
if __name__ == "__main__":
    # Test other examples for verification
    test_titles = [
        "HELLO WORLD (NEW WORLD)",  # 1
        "(NEW WORLD) HELLO WORLD",  # 3
        "(NEW WORLD) HELLO WORLD (TIME)",  # 5
        "HELLO WORLD (TIME) (ANOTHER WORLD)",  # 6
        "(THE) (BEST) HELLO WORLD",  # 7
        "(WHO) (BEST) HELLO WORLD",
        "(ONE) (TWO) HELLO WORLD (TIME) (ANOTHER WORLD)",  # 8
        "HELLO (TIME) WORLD",  # 9
        "(NEW TIME) (HI) HELLO (1) (2) WORLD  (NEW WORLD) (ORDER)"  # 10 Generates extra results as well
    ]

    for title in test_titles:
        test_title(title)
