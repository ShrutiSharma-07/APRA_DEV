# import pandas as pd
# import numpy as np
# from datasketch import MinHashLSH, MinHash
# from fuzzywuzzy import fuzz
# import re
# import json
# import os
# import gc
# import time
# from tqdm import tqdm
# import warnings
# import Levenshtein
#
#
# # Suppress the warning about missing python-Levenshtein
# warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher")
#
# SAMPLE_MODE = True
# SAMPLE_SIZE = 5000000
# LSH_THRESHOLD = 0.7  # LSH threshold
# FUZZY_THRESHOLD = 80  # FuzzyWuzzy threshold (0-100)
# NUM_PERM = 128
#
# ADC_CSV_PATH = "adc_titles.csv"
# MZK_CSV_PATH = "mzk_titles.csv"
# OUTPUT_DIR = "../output"
#
# os.makedirs(OUTPUT_DIR, exist_ok=True)
#
#
# def preprocess_title_lsh(title):
#     if not title or pd.isna(title):
#         return ""
#     text = re.sub(r'[^\w\s]', ' ', str(title).lower())
#     text = re.sub(r'\s+', ' ', text).strip()
#     return text
#
#
# def track_progress(iterable, total=None, desc="Processing"):
#     return tqdm(iterable, total=total, desc=desc)
#
#
# def parse_hash_values(hash_string):
#     try:
#         hash_list = json.loads(hash_string)
#         return hash_list
#     except json.JSONDecodeError:
#         try:
#             clean_str = hash_string.strip('[]').replace('\n', '').replace(' ', '')
#             if not clean_str:  # Empty array
#                 return []
#             return [int(x.strip()) for x in clean_str.split(',') if x.strip()]
#         except Exception:
#             print(f"Failed to parse hash values: {hash_string[:50]}...")
#             return []
#
#
# # Process ADC titles and create MinHash signatures - unchanged
# def process_adc_titles(adc_path, chunk_size=50000, num_perm=NUM_PERM, sample_mode=False, sample_size=100):
#     start_time = time.time()
#     print("Loading and preprocessing ADC titles...")
#
#     # Read ADC data from CSV
#     adc_df = pd.read_csv(adc_path)
#     print(f"Loaded {len(adc_df)} records from {adc_path}")
#
#     # Apply sampling if in sample mode
#     if sample_mode:
#         if len(adc_df) > sample_size:
#             adc_df = adc_df.sample(sample_size)
#         print(f"Sampled down to {len(adc_df)} records")
#
#     # Create normalized titles column
#     print("Creating normalized titles...")
#     adc_df['NORMALIZED_TITLE'] = adc_df['APRA_CLEANED_TITLE'].apply(preprocess_title_lsh)
#
#     # Save normalized titles to CSV
#     adc_normalized_path = os.path.join(OUTPUT_DIR, "adc_normalized_titles.csv")
#     adc_df.to_csv(adc_normalized_path, index=False)
#     print(f"Saved normalized titles to {adc_normalized_path}")
#
#     # Process in chunks and create MinHash signatures
#     total_count = len(adc_df)
#     minhash_results = []
#
#     for chunk_start in range(0, total_count, chunk_size):
#         chunk_end = min(chunk_start + chunk_size, total_count)
#         chunk_df = adc_df.iloc[chunk_start:chunk_end]
#
#         print(
#             f"[PROGRESS] Processing chunk {chunk_start // chunk_size + 1}/{(total_count + chunk_size - 1) // chunk_size} ({chunk_start}-{chunk_end})...")
#
#         chunk_results = []
#         for idx, row in track_progress(chunk_df.iterrows(), total=len(chunk_df), desc="Creating MinHash signatures"):
#             if not row['NORMALIZED_TITLE'] or pd.isna(row['NORMALIZED_TITLE']):
#                 continue
#
#             # Create shingles and MinHash
#             title = row['NORMALIZED_TITLE']
#             # Create 3-grams (trigrams) as shingles
#             shingles = {title[i:i + 3] for i in range(len(title) - 3 + 1) if i + 3 <= len(title)}
#             if not shingles:
#                 continue
#
#             m = MinHash(num_perm=num_perm)
#             for s in shingles:
#                 m.update(s.encode('utf-8'))
#
#             # Store hash values as a JSON string
#             hash_values_json = json.dumps(m.hashvalues.tolist())
#
#             # Store result
#             chunk_results.append({
#                 'APRA_WORK_ID': row['APRA_WORK_ID'],
#                 'APRA_ISWC': row['APRA_ISWC'],
#                 'APRA_CLEANED_TITLE': row['APRA_CLEANED_TITLE'],
#                 'NORMALIZED_TITLE': row['NORMALIZED_TITLE'],
#                 'HASH_VALUES': hash_values_json
#             })
#
#         minhash_results.extend(chunk_results)
#
#         # Clear memory
#         del chunk_df, chunk_results
#         gc.collect()
#
#     # Convert results to DataFrame and save
#     minhash_df = pd.DataFrame(minhash_results)
#     minhash_path = os.path.join(OUTPUT_DIR, "adc_minhash_values.csv")
#     minhash_df.to_csv(minhash_path, index=False)
#
#     end_time = time.time()
#     total_duration = end_time - start_time
#     print(
#         f"Finished processing {len(minhash_df)} ADC titles in {total_duration:.2f} seconds ({total_duration / 60:.2f} minutes)")
#     print(f"MinHash values saved to {minhash_path}")
#
#     return minhash_df
#
#
# # OPTIMIZED: Function to match MZK titles with ADC titles using LSH + FuzzyWuzzy
# def match_mzk_titles(mzk_path, adc_minhash_df, lsh_threshold=0.7, fuzzy_threshold=80, chunk_size=10000,
#                      num_perm=NUM_PERM,
#                      sample_mode=False, sample_size=5000000):
#     start_time = time.time()
#     print("Starting title matching process...")
#
#     # Create a matches DataFrame
#     matches = []
#
#     # Read MZK data
#     mzk_df = pd.read_csv(mzk_path)
#     print(f"Loaded {len(mzk_df)} records from {mzk_path}")
#
#     # Apply sampling if in sample mode
#     if sample_mode:
#         if len(mzk_df) > sample_size:
#             mzk_df = mzk_df.sample(sample_size)
#         print(f"Sampled down to {len(mzk_df)} records")
#
#     # Create normalized titles
#     print("Creating normalized titles for MZK tracks...")
#     mzk_df['NORMALIZED_TITLE'] = mzk_df['MUZOOKA_CLEANED_TITLE'].apply(preprocess_title_lsh)
#
#     # Find exact matches first
#     print("Finding exact matches...")
#     exact_start_time = time.time()
#
#     # OPTIMIZATION: Create dictionaries for faster lookups - keep in memory for performance
#     adc_titles_dict = {}
#     adc_iswc_dict = {}
#
#     print("Building lookup dictionaries...")
#     for _, row in adc_minhash_df.iterrows():
#         # Title dictionary for exact matching
#         title = row['NORMALIZED_TITLE']
#         if title and not pd.isna(title):
#             if title not in adc_titles_dict:
#                 adc_titles_dict[title] = []
#             adc_titles_dict[title].append(row)
#
#         # ISWC dictionary for faster ISWC lookups
#         iswc = row['APRA_ISWC']
#         if iswc and not pd.isna(iswc) and iswc != '':
#             if iswc not in adc_iswc_dict:
#                 adc_iswc_dict[iswc] = []
#             adc_iswc_dict[iswc].append(row)
#
#     # Find exact matches with optimized lookups
#     exact_matches = []
#     for _, mzk_row in track_progress(mzk_df.iterrows(), total=len(mzk_df), desc="Finding exact matches"):
#         mzk_title = mzk_row['NORMALIZED_TITLE']
#         mzk_iswc = mzk_row['MUZOOKA_ISWC']
#
#         # OPTIMIZATION: Check for ISWC match first using dictionary lookup
#         iswc_matched_ids = set()
#         if pd.notna(mzk_iswc) and mzk_iswc != '' and mzk_iswc in adc_iswc_dict:
#             for adc_row in adc_iswc_dict[mzk_iswc]:
#                 iswc_match = "Y" if (pd.notna(mzk_row['MUZOOKA_ISWC']) and pd.notna(adc_row['APRA_ISWC']) and
#                                      adc_row['APRA_ISWC'] == mzk_row['MUZOOKA_ISWC']) else "N"
#
#                 exact_matches.append({
#                     'APRA_WORK_ID': adc_row['APRA_WORK_ID'],
#                     'APRA_CLEANED_TITLE': adc_row['APRA_CLEANED_TITLE'],
#                     'APRA_ISWC': adc_row['APRA_ISWC'],
#                     'MUZOOKA_CLEANED_TITLE': mzk_row['MUZOOKA_CLEANED_TITLE'],
#                     'MUZOOKA_TRACK_ID': mzk_row['MUZOOKA_TRACK_ID'],
#                     'MUZOOKA_ISWC': mzk_row['MUZOOKA_ISWC'],
#                     'ISWC_MATCH': iswc_match,
#                     'MATCH_SCORE': 1.0
#                 })
#
#         # OPTIMIZATION: Then check for exact title match using dictionary lookup
#         if mzk_title in adc_titles_dict:
#             for adc_row in adc_titles_dict[mzk_title]:
#                 # Skip if we already found an ISWC match for this work
#                 if adc_row['APRA_WORK_ID'] in iswc_matched_ids:
#                     continue
#
#                 exact_matches.append({
#                     'APRA_WORK_ID': adc_row['APRA_WORK_ID'],
#                     'APRA_CLEANED_TITLE': adc_row['APRA_CLEANED_TITLE'],
#                     'APRA_ISWC': adc_row['APRA_ISWC'],
#                     'MUZOOKA_CLEANED_TITLE': mzk_row['MUZOOKA_CLEANED_TITLE'],
#                     'MUZOOKA_TRACK_ID': mzk_row['MUZOOKA_TRACK_ID'],
#                     'MUZOOKA_ISWC': mzk_row['MUZOOKA_ISWC'],
#                     'ISWC_MATCH': "N",  # Not an ISWC match
#                     'MATCH_SCORE': 1.0
#                 })
#
#     # Create DataFrame of exact matches
#     exact_matches_df = pd.DataFrame(exact_matches) if exact_matches else pd.DataFrame()
#     matches.extend(exact_matches)
#
#     exact_end_time = time.time()
#     exact_duration = exact_end_time - exact_start_time
#     print(f"[PROGRESS] Found {len(exact_matches)} exact matches in {exact_duration:.2f} seconds")
#
#     # Find MZK titles without exact matches for fuzzy matching
#     matched_track_ids = set(exact_matches_df['MUZOOKA_TRACK_ID']) if not exact_matches_df.empty else set()
#     remaining_mzk = mzk_df[~mzk_df['MUZOOKA_TRACK_ID'].isin(matched_track_ids)]
#
#     print(f"[PROGRESS] Processing {len(remaining_mzk)} remaining MZK titles for fuzzy matching...")
#
#     # Create LSH index from ADC MinHash values
#     print("Creating LSH index from ADC MinHash values...")
#     lsh = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)
#
#     # OPTIMIZATION: Create an ID-to-row mapping for faster lookups during fuzzy matching
#     adc_id_to_row = {}
#
#     # Add ADC MinHash values to LSH index
#     for idx, row in track_progress(adc_minhash_df.iterrows(), total=len(adc_minhash_df), desc="Building LSH index"):
#         if pd.isna(row['HASH_VALUES']) or row['HASH_VALUES'] == '':
#             continue
#
#         hash_values = parse_hash_values(row['HASH_VALUES'])
#         if not hash_values:
#             continue
#
#         m = MinHash(num_perm=num_perm)
#         m.hashvalues = np.array(hash_values)
#         lsh.insert(str(idx), m)
#
#         # Store row for faster lookups
#         adc_id_to_row[str(idx)] = row
#
#     # Process MZK titles in chunks
#     total_count = len(remaining_mzk)
#     fuzzy_matches = []
#
#     for chunk_start in range(0, total_count, chunk_size):
#         chunk_end = min(chunk_start + chunk_size, total_count)
#         chunk_df = remaining_mzk.iloc[chunk_start:chunk_end]
#
#         print(
#             f"[PROGRESS] Processing MZK chunk {chunk_start // chunk_size + 1}/{(total_count + chunk_size - 1) // chunk_size} ({chunk_start}-{chunk_end})...")
#
#         for idx, mzk_row in track_progress(chunk_df.iterrows(), total=len(chunk_df), desc="Finding fuzzy matches"):
#             if not mzk_row['NORMALIZED_TITLE'] or pd.isna(mzk_row['NORMALIZED_TITLE']):
#                 continue
#
#             mzk_title = mzk_row['NORMALIZED_TITLE']
#
#             # Process all titles regardless of length (as requested)
#
#             # Create shingles and MinHash for MZK title
#             shingles = {mzk_title[i:i + 3] for i in range(len(mzk_title) - 3 + 1) if i + 3 <= len(mzk_title)}
#             if not shingles:
#                 continue
#
#             m = MinHash(num_perm=num_perm)
#             for s in shingles:
#                 m.update(s.encode('utf-8'))
#
#             # Find potential matches using LSH
#             candidates = lsh.query(m)
#
#             # Process all candidates that meet the threshold criteria
#             for candidate_idx in candidates:
#                 # Get the candidate row directly from our mapping
#                 adc_row = adc_id_to_row[candidate_idx]
#
#                 # Calculate FuzzyWuzzy similarity (token_set_ratio works well for titles)
#                 # Use token_sort_ratio for ordered comparison or token_set_ratio for fuzzy token matching
#                 similarity = fuzz.token_set_ratio(mzk_title, adc_row['NORMALIZED_TITLE'])
#
#                 # Convert to 0-1 scale for consistency with other similarity metrics
#                 similarity_normalized = similarity / 100.0
#
#                 # Check if ISWCs match - use "Y" or "N" string values
#                 iswc_match = "Y" if (pd.notna(mzk_row['MUZOOKA_ISWC']) and pd.notna(adc_row['APRA_ISWC']) and
#                                      mzk_row['MUZOOKA_ISWC'] != '' and adc_row['APRA_ISWC'] != '' and
#                                      mzk_row['MUZOOKA_ISWC'] == adc_row['APRA_ISWC']) else "N"
#
#                 # If similarity is above threshold, add to matches
#                 if similarity >= fuzzy_threshold:
#                     fuzzy_matches.append({
#                         'APRA_WORK_ID': adc_row['APRA_WORK_ID'],
#                         'APRA_CLEANED_TITLE': adc_row['APRA_CLEANED_TITLE'],
#                         'APRA_ISWC': adc_row['APRA_ISWC'],
#                         'MUZOOKA_CLEANED_TITLE': mzk_row['MUZOOKA_CLEANED_TITLE'],
#                         'MUZOOKA_TRACK_ID': mzk_row['MUZOOKA_TRACK_ID'],
#                         'MUZOOKA_ISWC': mzk_row['MUZOOKA_ISWC'],
#                         'ISWC_MATCH': iswc_match,
#                         'MATCH_SCORE': similarity_normalized
#                     })
#
#     # Add fuzzy matches to results
#     matches.extend(fuzzy_matches)
#
#     # Convert all matches to DataFrame and save
#     matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
#     matches_path = os.path.join(OUTPUT_DIR, "title_matches_lsh_fuzzywuzzy.csv")
#     matches_df.to_csv(matches_path, index=False)
#
#     # Final stats
#     print("\n===== FINAL MATCHING RESULTS =====")
#     if not matches_df.empty:
#         # Calculate stats for matches with ISWC match
#         iswc_matches = matches_df[matches_df['ISWC_MATCH'] == "Y"]
#         print(f"Matches with ISWC match: {len(iswc_matches)}")
#
#         # Calculate stats for title matches
#         title_matches = matches_df[matches_df['ISWC_MATCH'] == "N"]
#         print(f"Matches with title similarity only: {len(title_matches)}")
#
#         # Stats by similarity score
#         score_ranges = [
#             (0.7, 0.8, "0.7-0.8"),
#             (0.8, 0.9, "0.8-0.9"),
#             (0.9, 1.0, "0.9-1.0"),
#             (1.0, 1.0001, "1.0 (Exact)")
#         ]
#
#         for min_score, max_score, label in score_ranges:
#             count = len(matches_df[(matches_df['MATCH_SCORE'] >= min_score) & (matches_df['MATCH_SCORE'] < max_score)])
#             print(f"Matches with score {label}: {count}")
#
#         # Get unique MZK titles matched
#         unique_mzk = matches_df['MUZOOKA_TRACK_ID'].nunique()
#         print(
#             f"Unique MZK tracks matched: {unique_mzk} out of {len(mzk_df)} total ({unique_mzk * 100 / max(len(mzk_df), 1):.2f}%)")
#
#         # Get unique ADC titles matched
#         unique_adc = matches_df['APRA_WORK_ID'].nunique()
#         print(
#             f"Unique ADC works matched: {unique_adc} out of {len(adc_minhash_df)} total ({unique_adc * 100 / max(len(adc_minhash_df), 1):.2f}%)")
#     else:
#         print("No matches found!")
#
#     end_time = time.time()
#     total_duration = end_time - start_time
#     print(
#         f"\n[COMPLETE] Total matching process completed in {total_duration:.2f} seconds ({total_duration / 60:.2f} minutes)")
#     print(f"All matches saved to {matches_path}")
#
#     if sample_mode:
#         print(
#             "\n[SAMPLE MODE] Note: Results are based on a sample of data and do not represent complete matching statistics.")
#
#     return matches_df
#
#
# # Main execution function
# def main():
#     print("Starting LSH-based title matching process with FuzzyWuzzy integration...")
#
#     # Check if python-Levenshtein is installed
#     try:
#         import Levenshtein
#         print("Using fast C implementation of Levenshtein distance")
#     except ImportError:
#         print("WARNING: For much faster matching, install python-Levenshtein:")
#         print("pip install python-Levenshtein")
#
#     # Set sampling mode - change to False for full run
#     sample_mode = SAMPLE_MODE
#     sample_size = SAMPLE_SIZE
#
#     print(f"Running in {'SAMPLE' if sample_mode else 'FULL DATA'} mode...")
#
#     # Step 1: Process ADC titles and create MinHash signatures
#     print("Step 1: Processing ADC titles and creating MinHash signatures...")
#     adc_minhash_df = process_adc_titles(
#         ADC_CSV_PATH,
#         chunk_size=50000,
#         sample_mode=sample_mode,
#         sample_size=sample_size
#     )
#
#     # Step 2: Match MZK titles against ADC titles with LSH + FuzzyWuzzy
#     print("\nStep 2: Matching MZK titles against ADC titles with LSH + FuzzyWuzzy...")
#     matches_df = match_mzk_titles(
#         MZK_CSV_PATH,
#         adc_minhash_df,
#         lsh_threshold=LSH_THRESHOLD,
#         fuzzy_threshold=FUZZY_THRESHOLD,
#         chunk_size=10000,
#         sample_mode=sample_mode,
#         sample_size=sample_size
#     )
#
#     print("\nTitle matching process complete! Results are stored in the output directory.")
#
#
# if __name__ == "__main__":
#     main()


import pandas as pd
import numpy as np
from datasketch import MinHashLSH, MinHash
from fuzzywuzzy import fuzz
import re
import json
import os
import gc
import time
from tqdm import tqdm
import warnings
import Levenshtein
import hashlib
import struct

# Suppress the warning about missing python-Levenshtein
warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher")

SAMPLE_MODE = True
SAMPLE_SIZE = 5000000
FUZZY_THRESHOLD = 80  # FuzzyWuzzy threshold (0-100)
SIMHASH_THRESHOLD = 3  # SimHash threshold (maximum number of bits that can differ)

ADC_CSV_PATH = "adc_titles.csv"
MZK_CSV_PATH = "mzk_titles.csv"
OUTPUT_DIR = "../output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# Custom SimHash implementation
class SimHash:
    def __init__(self, tokens=None, hashbits=64):
        self.hashbits = hashbits
        self.hash = 0

        if tokens:
            self.build_hash(tokens)

    def build_hash(self, tokens):
        # Initialize an array of zeros for counting
        v = [0] * self.hashbits

        # For each token, calculate its hash and add to the vector
        for token in tokens:
            # Get a hash value for the token
            token_hash = self._string_hash(token)

            # For each bit in the hash value
            for i in range(self.hashbits):
                bitmask = 1 << i
                if token_hash & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1

        # Construct the final hash value
        fingerprint = 0
        for i in range(self.hashbits):
            if v[i] >= 0:
                fingerprint |= (1 << i)

        self.hash = fingerprint

    def _string_hash(self, token):
        """Hash the token to a 64-bit integer using MD5"""
        md5 = hashlib.md5(token.encode('utf-8')).digest()
        return struct.unpack('<Q', md5[:8])[0]

    @property
    def value(self):
        return self.hash

    @staticmethod
    def hamming(hash1, hash2):
        """Calculate the Hamming distance between two hash values"""
        x = (hash1 ^ hash2) & ((1 << 64) - 1)
        ans = 0
        while x:
            ans += 1
            x &= x - 1
        return ans


def preprocess_title(title):
    """Preprocess the title for SimHash calculation"""
    if not title or pd.isna(title):
        return ""
    text = re.sub(r'[^\w\s]', ' ', str(title).lower())
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def track_progress(iterable, total=None, desc="Processing"):
    """Track progress with tqdm"""
    return tqdm(iterable, total=total, desc=desc)


def create_simhash(text):
    """Create a SimHash for the given text"""
    if not text or len(text) < 2:
        return None

    # Create tokens (words and character shingles for better matching)
    words = text.split()
    shingles = [text[i:i + 3] for i in range(len(text) - 2)]
    tokens = words + shingles

    if not tokens:
        return None

    # Create SimHash
    simhash = SimHash(tokens)
    return simhash


# Process ADC titles and create SimHash signatures
def process_adc_titles(adc_path, chunk_size=50000, sample_mode=False, sample_size=100):
    start_time = time.time()
    print("Loading and preprocessing ADC titles...")

    # Read ADC data from CSV
    adc_df = pd.read_csv(adc_path)
    print(f"Loaded {len(adc_df)} records from {adc_path}")

    # Apply sampling if in sample mode
    if sample_mode:
        if len(adc_df) > sample_size:
            adc_df = adc_df.sample(sample_size)
        print(f"Sampled down to {len(adc_df)} records")

    # Create normalized titles column
    print("Creating normalized titles...")
    adc_df['NORMALIZED_TITLE'] = adc_df['APRA_CLEANED_TITLE'].apply(preprocess_title)

    # Save normalized titles to CSV
    adc_normalized_path = os.path.join(OUTPUT_DIR, "adc_normalized_titles.csv")
    adc_df.to_csv(adc_normalized_path, index=False)
    print(f"Saved normalized titles to {adc_normalized_path}")

    # Process in chunks and create SimHash signatures
    total_count = len(adc_df)
    simhash_results = []

    for chunk_start in range(0, total_count, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_count)
        chunk_df = adc_df.iloc[chunk_start:chunk_end]

        print(
            f"[PROGRESS] Processing chunk {chunk_start // chunk_size + 1}/{(total_count + chunk_size - 1) // chunk_size} ({chunk_start}-{chunk_end})...")

        chunk_results = []
        for idx, row in track_progress(chunk_df.iterrows(), total=len(chunk_df), desc="Creating SimHash signatures"):
            if not row['NORMALIZED_TITLE'] or pd.isna(row['NORMALIZED_TITLE']):
                continue

            # Create SimHash
            title = row['NORMALIZED_TITLE']
            simhash = create_simhash(title)
            if simhash is None:
                continue

            # Store result
            chunk_results.append({
                'APRA_WORK_ID': row['APRA_WORK_ID'],
                'APRA_ISWC': row['APRA_ISWC'],
                'APRA_CLEANED_TITLE': row['APRA_CLEANED_TITLE'],
                'NORMALIZED_TITLE': row['NORMALIZED_TITLE'],
                'HASH_VALUE': str(simhash.value)
            })

        simhash_results.extend(chunk_results)

        # Clear memory
        del chunk_df, chunk_results
        gc.collect()

    # Convert results to DataFrame and save
    simhash_df = pd.DataFrame(simhash_results)
    simhash_path = os.path.join(OUTPUT_DIR, "adc_simhash_values.csv")
    simhash_df.to_csv(simhash_path, index=False)

    end_time = time.time()
    total_duration = end_time - start_time
    print(
        f"Finished processing {len(simhash_df)} ADC titles in {total_duration:.2f} seconds ({total_duration / 60:.2f} minutes)")
    print(f"SimHash values saved to {simhash_path}")

    return simhash_df


# Function to match MZK titles with ADC titles using SimHash + FuzzyWuzzy
def match_mzk_titles(mzk_path, adc_simhash_df, simhash_threshold=3, fuzzy_threshold=80, chunk_size=10000,
                     sample_mode=False, sample_size=5000000):
    start_time = time.time()
    print("Starting title matching process...")

    # Create a matches DataFrame
    matches = []

    # Read MZK data
    mzk_df = pd.read_csv(mzk_path)
    print(f"Loaded {len(mzk_df)} records from {mzk_path}")

    # Apply sampling if in sample mode
    if sample_mode:
        if len(mzk_df) > sample_size:
            mzk_df = mzk_df.sample(sample_size)
        print(f"Sampled down to {len(mzk_df)} records")

    # Create normalized titles
    print("Creating normalized titles for MZK tracks...")
    mzk_df['NORMALIZED_TITLE'] = mzk_df['MUZOOKA_CLEANED_TITLE'].apply(preprocess_title)

    # Find exact matches first
    print("Finding exact matches...")
    exact_start_time = time.time()

    # Create dictionaries for faster lookups
    adc_titles_dict = {}
    adc_iswc_dict = {}

    print("Building lookup dictionaries...")
    for _, row in adc_simhash_df.iterrows():
        # Title dictionary for exact matching
        title = row['NORMALIZED_TITLE']
        if title and not pd.isna(title):
            if title not in adc_titles_dict:
                adc_titles_dict[title] = []
            adc_titles_dict[title].append(row)

        # ISWC dictionary for faster ISWC lookups
        iswc = row['APRA_ISWC']
        if iswc and not pd.isna(iswc) and iswc != '':
            if iswc not in adc_iswc_dict:
                adc_iswc_dict[iswc] = []
            adc_iswc_dict[iswc].append(row)

    # Find exact matches with optimized lookups
    exact_matches = []
    for _, mzk_row in track_progress(mzk_df.iterrows(), total=len(mzk_df), desc="Finding exact matches"):
        mzk_title = mzk_row['NORMALIZED_TITLE']
        mzk_iswc = mzk_row['MUZOOKA_ISWC']

        # Check for ISWC match first using dictionary lookup
        iswc_matched_ids = set()
        if pd.notna(mzk_iswc) and mzk_iswc != '' and mzk_iswc in adc_iswc_dict:
            for adc_row in adc_iswc_dict[mzk_iswc]:
                iswc_match = "Y" if (pd.notna(mzk_row['MUZOOKA_ISWC']) and pd.notna(adc_row['APRA_ISWC']) and
                                     adc_row['APRA_ISWC'] == mzk_row['MUZOOKA_ISWC']) else "N"

                exact_matches.append({
                    'APRA_WORK_ID': adc_row['APRA_WORK_ID'],
                    'APRA_CLEANED_TITLE': adc_row['APRA_CLEANED_TITLE'],
                    'APRA_ISWC': adc_row['APRA_ISWC'],
                    'MUZOOKA_CLEANED_TITLE': mzk_row['MUZOOKA_CLEANED_TITLE'],
                    'MUZOOKA_TRACK_ID': mzk_row['MUZOOKA_TRACK_ID'],
                    'MUZOOKA_ISWC': mzk_row['MUZOOKA_ISWC'],
                    'ISWC_MATCH': iswc_match,
                    'MATCH_SCORE': 1.0
                })
                iswc_matched_ids.add(adc_row['APRA_WORK_ID'])

        # Then check for exact title match using dictionary lookup
        if mzk_title in adc_titles_dict:
            for adc_row in adc_titles_dict[mzk_title]:
                # Skip if we already found an ISWC match for this work
                if adc_row['APRA_WORK_ID'] in iswc_matched_ids:
                    continue

                exact_matches.append({
                    'APRA_WORK_ID': adc_row['APRA_WORK_ID'],
                    'APRA_CLEANED_TITLE': adc_row['APRA_CLEANED_TITLE'],
                    'APRA_ISWC': adc_row['APRA_ISWC'],
                    'MUZOOKA_CLEANED_TITLE': mzk_row['MUZOOKA_CLEANED_TITLE'],
                    'MUZOOKA_TRACK_ID': mzk_row['MUZOOKA_TRACK_ID'],
                    'MUZOOKA_ISWC': mzk_row['MUZOOKA_ISWC'],
                    'ISWC_MATCH': "N",  # Not an ISWC match
                    'MATCH_SCORE': 1.0
                })

    # Create DataFrame of exact matches
    exact_matches_df = pd.DataFrame(exact_matches) if exact_matches else pd.DataFrame()
    matches.extend(exact_matches)

    exact_end_time = time.time()
    exact_duration = exact_end_time - exact_start_time
    print(f"[PROGRESS] Found {len(exact_matches)} exact matches in {exact_duration:.2f} seconds")

    # Find MZK titles without exact matches for fuzzy matching
    matched_track_ids = set(exact_matches_df['MUZOOKA_TRACK_ID']) if not exact_matches_df.empty else set()
    remaining_mzk = mzk_df[~mzk_df['MUZOOKA_TRACK_ID'].isin(matched_track_ids)]

    print(f"[PROGRESS] Processing {len(remaining_mzk)} remaining MZK titles for fuzzy matching...")

    # Create a dictionary for ADC SimHash values
    adc_hash_dict = {}
    for _, row in track_progress(adc_simhash_df.iterrows(), total=len(adc_simhash_df), desc="Building SimHash index"):
        if pd.isna(row['HASH_VALUE']) or row['HASH_VALUE'] == '':
            continue

        # Convert string hash value back to integer
        hash_value = int(row['HASH_VALUE'])
        if hash_value not in adc_hash_dict:
            adc_hash_dict[hash_value] = []
        adc_hash_dict[hash_value].append(row)

    # Process MZK titles in chunks
    total_count = len(remaining_mzk)
    fuzzy_matches = []

    for chunk_start in range(0, total_count, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_count)
        chunk_df = remaining_mzk.iloc[chunk_start:chunk_end]

        print(
            f"[PROGRESS] Processing MZK chunk {chunk_start // chunk_size + 1}/{(total_count + chunk_size - 1) // chunk_size} ({chunk_start}-{chunk_end})...")

        for idx, mzk_row in track_progress(chunk_df.iterrows(), total=len(chunk_df), desc="Finding fuzzy matches"):
            if not mzk_row['NORMALIZED_TITLE'] or pd.isna(mzk_row['NORMALIZED_TITLE']):
                continue

            mzk_title = mzk_row['NORMALIZED_TITLE']
            mzk_simhash = create_simhash(mzk_title)

            if mzk_simhash is None:
                continue

            # Find potential matches using SimHash
            candidates = []

            # Check all ADC hashes - this is an O(n) operation but we can optimize it with bucketing in a production environment
            for adc_hash, adc_rows in adc_hash_dict.items():
                # Calculate Hamming distance
                distance = SimHash.hamming(mzk_simhash.value, adc_hash)

                # If distance is within threshold, add as candidates
                if distance <= simhash_threshold:
                    for adc_row in adc_rows:
                        # Calculate FuzzyWuzzy similarity for more precise matching
                        similarity = fuzz.token_set_ratio(mzk_title, adc_row['NORMALIZED_TITLE'])

                        # Convert to 0-1 scale for consistency
                        similarity_normalized = similarity / 100.0

                        # Check if ISWCs match
                        iswc_match = "Y" if (pd.notna(mzk_row['MUZOOKA_ISWC']) and pd.notna(adc_row['APRA_ISWC']) and
                                             mzk_row['MUZOOKA_ISWC'] != '' and adc_row['APRA_ISWC'] != '' and
                                             mzk_row['MUZOOKA_ISWC'] == adc_row['APRA_ISWC']) else "N"

                        # If similarity is above threshold, add to matches
                        if similarity >= fuzzy_threshold:
                            fuzzy_matches.append({
                                'APRA_WORK_ID': adc_row['APRA_WORK_ID'],
                                'APRA_CLEANED_TITLE': adc_row['APRA_CLEANED_TITLE'],
                                'APRA_ISWC': adc_row['APRA_ISWC'],
                                'MUZOOKA_CLEANED_TITLE': mzk_row['MUZOOKA_CLEANED_TITLE'],
                                'MUZOOKA_TRACK_ID': mzk_row['MUZOOKA_TRACK_ID'],
                                'MUZOOKA_ISWC': mzk_row['MUZOOKA_ISWC'],
                                'ISWC_MATCH': iswc_match,
                                'MATCH_SCORE': similarity_normalized
                            })

    # Add fuzzy matches to results
    matches.extend(fuzzy_matches)

    # Convert all matches to DataFrame and save
    matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
    matches_path = os.path.join(OUTPUT_DIR, "title_matches_simhash_fuzzywuzzy.csv")
    matches_df.to_csv(matches_path, index=False)

    # Final stats
    print("\n===== FINAL MATCHING RESULTS =====")
    if not matches_df.empty:
        # Calculate stats for matches with ISWC match
        iswc_matches = matches_df[matches_df['ISWC_MATCH'] == "Y"]
        print(f"Matches with ISWC match: {len(iswc_matches)}")

        # Calculate stats for title matches
        title_matches = matches_df[matches_df['ISWC_MATCH'] == "N"]
        print(f"Matches with title similarity only: {len(title_matches)}")

        # Stats by similarity score
        score_ranges = [
            (0.7, 0.8, "0.7-0.8"),
            (0.8, 0.9, "0.8-0.9"),
            (0.9, 1.0, "0.9-1.0"),
            (1.0, 1.0001, "1.0 (Exact)")
        ]

        for min_score, max_score, label in score_ranges:
            count = len(matches_df[(matches_df['MATCH_SCORE'] >= min_score) & (matches_df['MATCH_SCORE'] < max_score)])
            print(f"Matches with score {label}: {count}")

        # Get unique MZK titles matched
        unique_mzk = matches_df['MUZOOKA_TRACK_ID'].nunique()
        print(
            f"Unique MZK tracks matched: {unique_mzk} out of {len(mzk_df)} total ({unique_mzk * 100 / max(len(mzk_df), 1):.2f}%)")

        # Get unique ADC titles matched
        unique_adc = matches_df['APRA_WORK_ID'].nunique()
        print(
            f"Unique ADC works matched: {unique_adc} out of {len(adc_simhash_df)} total ({unique_adc * 100 / max(len(adc_simhash_df), 1):.2f}%)")
    else:
        print("No matches found!")

    end_time = time.time()
    total_duration = end_time - start_time
    print(
        f"\n[COMPLETE] Total matching process completed in {total_duration:.2f} seconds ({total_duration / 60:.2f} minutes)")
    print(f"All matches saved to {matches_path}")

    if sample_mode:
        print(
            "\n[SAMPLE MODE] Note: Results are based on a sample of data and do not represent complete matching statistics.")

    return matches_df


# Main execution function
def main():
    print("Starting SimHash-based title matching process with FuzzyWuzzy integration...")

    # Check if python-Levenshtein is installed
    try:
        import Levenshtein
        print("Using fast C implementation of Levenshtein distance")
    except ImportError:
        print("WARNING: For much faster matching, install python-Levenshtein:")
        print("pip install python-Levenshtein")

    # Set sampling mode - change to False for full run
    sample_mode = SAMPLE_MODE
    sample_size = SAMPLE_SIZE

    print(f"Running in {'SAMPLE' if sample_mode else 'FULL DATA'} mode...")

    # Step 1: Process ADC titles and create SimHash signatures
    print("Step 1: Processing ADC titles and creating SimHash signatures...")
    adc_simhash_df = process_adc_titles(
        ADC_CSV_PATH,
        chunk_size=50000,
        sample_mode=sample_mode,
        sample_size=sample_size
    )

    # Step 2: Match MZK titles against ADC titles with SimHash + FuzzyWuzzy
    print("\nStep 2: Matching MZK titles against ADC titles with SimHash + FuzzyWuzzy...")
    matches_df = match_mzk_titles(
        MZK_CSV_PATH,
        adc_simhash_df,
        simhash_threshold=SIMHASH_THRESHOLD,
        fuzzy_threshold=FUZZY_THRESHOLD,
        chunk_size=10000,
        sample_mode=sample_mode,
        sample_size=sample_size
    )

    print("\nTitle matching process complete! Results are stored in the output directory.")


if __name__ == "__main__":
    main()