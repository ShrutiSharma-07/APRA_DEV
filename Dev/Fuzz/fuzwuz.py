import pandas as pd
from rapidfuzz import fuzz
import time
import os


def main():
    # File paths (modify these to match your local setup)
    apra_file = 'adc_titles.csv'
    muzooka_file = 'mzk_titles.csv'
    output_file = 'fuzzy_match_results.csv'
    iswc_match_file = 'iswc_match_results.csv'
    title_match_file = 'title_match_results.csv'

    # Set fuzzy match threshold (e.g., 90 out of 100)
    threshold = 90

    # Set batch size for processing (adjust based on your available memory)
    batch_size = 1000

    print("Starting two-phase matching process...")

    # Load data from CSV files
    print(f"Loading data from CSV files...")
    start_time = time.time()

    try:
        apra_works = pd.read_csv(apra_file)
        elapsed = time.time() - start_time
        print(f"Loaded APRA works data: {len(apra_works)} rows in {elapsed:.2f} seconds")
    except Exception as e:
        print(f"Error loading APRA works data: {e}")
        print(
            f"Make sure {apra_file} exists and contains columns 'APRA_WORK_ID', 'APRA_CLEANED_TITLE', and 'APRA_ISWC'")
        return

    start_time = time.time()
    try:
        muzooka_tracks = pd.read_csv(muzooka_file)
        elapsed = time.time() - start_time
        print(f"Loaded Muzooka tracks data: {len(muzooka_tracks)} rows in {elapsed:.2f} seconds")
    except Exception as e:
        print(f"Error loading Muzooka tracks data: {e}")
        print(
            f"Make sure {muzooka_file} exists and contains columns 'MUZOOKA_TRACK_ID', 'MUZOOKA_CLEANED_TITLE', and 'MUZOOKA_ISWC'")
        return

    print(f"Using fuzzy match threshold: {threshold}")
    print(f"Using batch size: {batch_size}")

    # =============================================
    # PHASE 1: Match works with identical ISWCs
    # =============================================
    print("\n===== PHASE 1: Matching works with identical ISWCs =====")

    # Filter out rows with empty ISWCs
    apra_works_with_iswc = apra_works[apra_works['APRA_ISWC'].notna() & (apra_works['APRA_ISWC'] != '')]
    muzooka_tracks_with_iswc = muzooka_tracks[
        muzooka_tracks['MUZOOKA_ISWC'].notna() & (muzooka_tracks['MUZOOKA_ISWC'] != '')]

    print(
        f"APRA works with valid ISWC: {len(apra_works_with_iswc)} of {len(apra_works)} ({len(apra_works_with_iswc) / len(apra_works) * 100:.1f}%)")
    print(
        f"Muzooka tracks with valid ISWC: {len(muzooka_tracks_with_iswc)} of {len(muzooka_tracks)} ({len(muzooka_tracks_with_iswc) / len(muzooka_tracks) * 100:.1f}%)")

    # Create a lookup dictionary for Muzooka tracks by ISWC for faster matching
    muzooka_by_iswc = {}
    for _, row in muzooka_tracks_with_iswc.iterrows():
        iswc = str(row['MUZOOKA_ISWC']).strip()
        if iswc not in muzooka_by_iswc:
            muzooka_by_iswc[iswc] = []
        muzooka_by_iswc[iswc].append(row)

    # Perform ISWC matching
    iswc_results = []
    iswc_match_count = 0
    total_rows_iswc = len(apra_works_with_iswc)

    print(f"Starting ISWC matching for {total_rows_iswc} APRA works with valid ISWCs...")
    start_time = time.time()

    # Process in batches
    for batch_start in range(0, total_rows_iswc, batch_size):
        batch_end = min(batch_start + batch_size, total_rows_iswc)
        batch = apra_works_with_iswc.iloc[batch_start:batch_end]

        batch_matches = 0

        # Process each row in the batch
        for _, row_apra in batch.iterrows():
            iswc = str(row_apra['APRA_ISWC']).strip()

            # Find matches in the Muzooka tracks with the same ISWC
            if iswc in muzooka_by_iswc:
                for row_muzooka in muzooka_by_iswc[iswc]:
                    # Calculate title similarity score
                    score = fuzz.WRatio(row_apra['APRA_CLEANED_TITLE'], row_muzooka['MUZOOKA_CLEANED_TITLE'])

                    # Add to results
                    iswc_results.append({
                        "APRA_WORK_ID": row_apra['APRA_WORK_ID'],
                        "APRA_CLEANED_TITLE": row_apra['APRA_CLEANED_TITLE'],
                        "APRA_ISWC": row_apra['APRA_ISWC'],
                        "MUZOOKA_TRACK_ID": row_muzooka['MUZOOKA_TRACK_ID'],
                        "MUZOOKA_CLEANED_TITLE": row_muzooka['MUZOOKA_CLEANED_TITLE'],
                        "MUZOOKA_ISWC": row_muzooka['MUZOOKA_ISWC'],
                        "ISWC_MATCH": "Y",
                        "MATCH_SCORE": score,
                        "MATCH_TYPE": "ISWC"
                    })
                    batch_matches += 1

        # Update total matches
        iswc_match_count += batch_matches

        # Print progress
        elapsed = time.time() - start_time
        percent_complete = (batch_end / total_rows_iswc) * 100
        print(
            f"ISWC Batch progress: {batch_end}/{total_rows_iswc} rows ({percent_complete:.1f}%) processed in {elapsed:.2f} seconds")
        print(f"ISWC matches found so far: {iswc_match_count}")

        # Show sample match if available
        if batch_matches > 0:
            sample_match = iswc_results[-1]
            print(
                f"Sample ISWC match: APRA '{sample_match['APRA_CLEANED_TITLE']}' matched with Muzooka '{sample_match['MUZOOKA_CLEANED_TITLE']}' (title similarity: {sample_match['MATCH_SCORE']})")

    # Create DataFrame from ISWC results
    iswc_matches_df = pd.DataFrame(iswc_results) if iswc_results else pd.DataFrame()

    # Save ISWC match results to CSV
    if not iswc_matches_df.empty:
        print(f"\nFound {len(iswc_matches_df)} ISWC matches. Saving to CSV...")
        iswc_matches_df.to_csv(iswc_match_file, index=False)
        print(f"ISWC match results saved to '{iswc_match_file}'")

        # Print distribution of title similarity scores for ISWC matches
        print("\nTitle similarity score distribution for ISWC matches:")
        score_bins = [0, 50, 70, 80, 90, 95, 100]

        for i in range(len(score_bins) - 1):
            count = ((iswc_matches_df['MATCH_SCORE'] >= score_bins[i]) &
                     (iswc_matches_df['MATCH_SCORE'] < score_bins[i + 1])).sum()
            print(
                f"  Score {score_bins[i]}-{score_bins[i + 1]}: {count} matches ({count / len(iswc_matches_df) * 100:.1f}%)")
    else:
        print("No ISWC matches found.")

    # =========================================================
    # PHASE 2: Perform fuzzy title matching for remaining works
    # =========================================================
    print("\n===== PHASE 2: Fuzzy matching titles for remaining works =====")

    # Create sets of APRA work IDs and Muzooka track IDs that already have ISWC matches
    matched_apra_ids = set()
    matched_muzooka_ids = set()

    if not iswc_matches_df.empty:
        matched_apra_ids = set(iswc_matches_df['APRA_WORK_ID'])
        matched_muzooka_ids = set(iswc_matches_df['MUZOOKA_TRACK_ID'])

    # Filter out already matched works
    apra_works_remaining = apra_works[~apra_works['APRA_WORK_ID'].isin(matched_apra_ids)]
    muzooka_tracks_remaining = muzooka_tracks[~muzooka_tracks['MUZOOKA_TRACK_ID'].isin(matched_muzooka_ids)]

    print(
        f"Remaining APRA works for title matching: {len(apra_works_remaining)} of {len(apra_works)} ({len(apra_works_remaining) / len(apra_works) * 100:.1f}%)")
    print(
        f"Remaining Muzooka tracks for title matching: {len(muzooka_tracks_remaining)} of {len(muzooka_tracks)} ({len(muzooka_tracks_remaining) / len(muzooka_tracks) * 100:.1f}%)")

    # Process title matches in batches
    title_results = []
    title_match_count = 0
    total_rows_title = len(apra_works_remaining)

    print(f"Starting title matching for {total_rows_title} remaining APRA works...")
    start_time = time.time()

    # Process in batches
    for batch_start in range(0, total_rows_title, batch_size):
        batch_end = min(batch_start + batch_size, total_rows_title)
        batch = apra_works_remaining.iloc[batch_start:batch_end]

        batch_matches = 0

        # Process each row in the batch
        for _, row_apra in batch.iterrows():
            for _, row_muzooka in muzooka_tracks_remaining.iterrows():
                # Calculate title similarity score
                score = fuzz.WRatio(row_apra['APRA_CLEANED_TITLE'], row_muzooka['MUZOOKA_CLEANED_TITLE'])

                # Add to results if score meets threshold
                if score >= threshold:
                    # Check if ISWCs match (for info only)
                    iswc_match = "Y" if (
                            pd.notna(row_apra['APRA_ISWC']) and
                            pd.notna(row_muzooka['MUZOOKA_ISWC']) and
                            str(row_apra['APRA_ISWC']).strip() == str(row_muzooka['MUZOOKA_ISWC']).strip()
                    ) else "N"

                    # Add to results
                    title_results.append({
                        "APRA_WORK_ID": row_apra['APRA_WORK_ID'],
                        "APRA_CLEANED_TITLE": row_apra['APRA_CLEANED_TITLE'],
                        "APRA_ISWC": row_apra['APRA_ISWC'],
                        "MUZOOKA_TRACK_ID": row_muzooka['MUZOOKA_TRACK_ID'],
                        "MUZOOKA_CLEANED_TITLE": row_muzooka['MUZOOKA_CLEANED_TITLE'],
                        "MUZOOKA_ISWC": row_muzooka['MUZOOKA_ISWC'],
                        "ISWC_MATCH": iswc_match,
                        "MATCH_SCORE": score,
                        "MATCH_TYPE": "TITLE"
                    })
                    batch_matches += 1

        # Update total matches
        title_match_count += batch_matches

        # Print progress
        elapsed = time.time() - start_time
        percent_complete = (batch_end / total_rows_title) * 100
        print(
            f"Title Batch progress: {batch_end}/{total_rows_title} rows ({percent_complete:.1f}%) processed in {elapsed:.2f} seconds")
        print(f"Title matches found so far: {title_match_count}")

        # Show sample match if available
        if batch_matches > 0:
            sample_match = title_results[-1]
            print(
                f"Sample title match: APRA '{sample_match['APRA_CLEANED_TITLE']}' matched with Muzooka '{sample_match['MUZOOKA_CLEANED_TITLE']}' (score: {sample_match['MATCH_SCORE']})")

        # Save interim results every 5 batches
        if batch_end % (batch_size * 5) == 0 and title_results:
            interim_df = pd.DataFrame(title_results)
            interim_file = f"interim_title_results_batch_{batch_end // batch_size}.csv"
            interim_df.to_csv(interim_file, index=False)
            print(f"Saved interim title results to {interim_file}")

    # Create DataFrame from title results
    title_matches_df = pd.DataFrame(title_results) if title_results else pd.DataFrame()

    # Save title match results to CSV
    if not title_matches_df.empty:
        print(f"\nFound {len(title_matches_df)} title matches. Saving to CSV...")
        title_matches_df.to_csv(title_match_file, index=False)
        print(f"Title match results saved to '{title_match_file}'")

        # Print distribution of match scores
        print("\nTitle match score distribution:")
        score_bins = [threshold, threshold + 2, threshold + 5, threshold + 10, 100]

        for i in range(len(score_bins) - 1):
            count = ((title_matches_df['MATCH_SCORE'] >= score_bins[i]) &
                     (title_matches_df['MATCH_SCORE'] < score_bins[i + 1])).sum()
            print(
                f"  Score {score_bins[i]}-{score_bins[i + 1]}: {count} matches ({count / len(title_matches_df) * 100:.1f}%)")
    else:
        print("No title matches found with the current threshold.")

    # =============================================
    # COMBINE ALL RESULTS
    # =============================================
    print("\n===== COMBINING ALL RESULTS =====")

    # Combine ISWC and title matches
    all_results = []
    if not iswc_matches_df.empty:
        all_results.extend(iswc_results)
    if not title_matches_df.empty:
        all_results.extend(title_results)

    # Create DataFrame from all results
    all_matches_df = pd.DataFrame(all_results) if all_results else pd.DataFrame()

    # Save combined results to CSV
    if not all_matches_df.empty:
        print(
            f"Found total of {len(all_matches_df)} matches ({len(iswc_matches_df) if not iswc_matches_df.empty else 0} ISWC + {len(title_matches_df) if not title_matches_df.empty else 0} title). Saving to CSV...")
        all_matches_df.to_csv(output_file, index=False)
        print(f"Combined results saved to '{output_file}'")

        # Print combined statistics
        print("\nCombined match statistics:")
        iswc_match_count = len(all_matches_df[all_matches_df['MATCH_TYPE'] == 'ISWC'])
        title_match_count = len(all_matches_df[all_matches_df['MATCH_TYPE'] == 'TITLE'])
        print(f"  ISWC matches: {iswc_match_count} ({iswc_match_count / len(all_matches_df) * 100:.1f}%)")
        print(f"  Title matches: {title_match_count} ({title_match_count / len(all_matches_df) * 100:.1f}%)")

        # Print distribution of match scores
        print("\nOverall match score distribution:")
        score_bins = [0, 50, 70, 80, 90, 95, 100]

        for i in range(len(score_bins) - 1):
            count = ((all_matches_df['MATCH_SCORE'] >= score_bins[i]) &
                     (all_matches_df['MATCH_SCORE'] < score_bins[i + 1])).sum()
            print(
                f"  Score {score_bins[i]}-{score_bins[i + 1]}: {count} matches ({count / len(all_matches_df) * 100:.1f}%)")
    else:
        print("No matches found.")

    print("\nFuzzy matching process completed!")


if __name__ == "__main__":
    main()