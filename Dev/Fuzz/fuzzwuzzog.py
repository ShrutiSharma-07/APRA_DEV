import pandas as pd
from rapidfuzz import fuzz
import time

def main():
    apra_file = 'adc_titles.csv'
    muzooka_file = 'mzk_titles.csv'
    output_file = 'fuzzy_match_results.csv'

    threshold = 90
    print("Starting fuzzy matching process...")
    start_time = time.time()

    apra_works = pd.read_csv(apra_file)
    elapsed = time.time() - start_time
    print(f"Loaded APRA works data: {len(apra_works)} rows in {elapsed:.2f} seconds")

    start_time = time.time()

    muzooka_tracks = pd.read_csv(muzooka_file)
    elapsed = time.time() - start_time
    print(f"Loaded Muzooka tracks data: {len(muzooka_tracks)} rows in {elapsed:.2f} seconds")

    print(f"Using match threshold: {threshold}")

    def find_matches(row_apra_works, m_tracks, threshold):
        matches = []

        for _, row_m_tracks in m_tracks.iterrows():
            score = fuzz.WRatio(row_apra_works['APRA_CLEANED_TITLE'], row_m_tracks['MUZOOKA_CLEANED_TITLE'])

            if score >= threshold:
                iswc_match = "Y" if str(row_apra_works['APRA_ISWC']).strip() == str(
                    row_m_tracks['MUZOOKA_ISWC']).strip() else "N"

                matches.append({
                    "APRA_WORK_ID": row_apra_works['APRA_WORK_ID'],
                    "APRA_CLEANED_TITLE": row_apra_works['APRA_CLEANED_TITLE'],
                    "APRA_ISWC": row_apra_works['APRA_ISWC'],
                    "MUZOOKA_CLEANED_TITLE": row_m_tracks['MUZOOKA_CLEANED_TITLE'],
                    "MUZOOKA_TRACK_ID": row_m_tracks['MUZOOKA_TRACK_ID'],
                    "MUZOOKA_ISWC": row_m_tracks['MUZOOKA_ISWC'],
                    "ISWC_MATCH": iswc_match,
                    "MATCH_SCORE": score
                })

        return matches

    results = []
    total_rows = len(apra_works)
    print(f"Starting matching process for {total_rows} APRA works...")

    start_time = time.time()
    last_report_time = start_time
    match_count = 0

    for idx, row_apra_works in apra_works.iterrows():
        # Print progress update every 100 rows or 30 seconds
        current_time = time.time()
        if idx % 100 == 0 or current_time - last_report_time > 30:
            elapsed = current_time - start_time
            percent_complete = (idx / total_rows) * 100
            print(f"Progress: {idx}/{total_rows} rows ({percent_complete:.1f}%) processed in {elapsed:.2f} seconds")
            print(f"Current matches found: {match_count}")
            last_report_time = current_time

        # Find matches for this row
        new_matches = find_matches(row_apra_works, muzooka_tracks, threshold)
        results.extend(new_matches)
        match_count += len(new_matches)

        # Occasionally show sample match details
        if len(new_matches) > 0 and idx % 500 == 0:
            sample_match = new_matches[0]
            print(
                f"Sample match: APRA '{sample_match['APRA_CLEANED_TITLE']}' matched with Muzooka '{sample_match['MUZOOKA_CLEANED_TITLE']}' (score: {sample_match['MATCH_SCORE']})")

    total_elapsed = time.time() - start_time
    print(f"\nProcessed {total_rows} rows in {total_elapsed:.2f} seconds")
    print(f"Total matches found: {match_count}")

    matches_df = pd.DataFrame(results)

    if not matches_df.empty:
        print(f"Found {len(matches_df)} matches. Saving to CSV...")

        start_time = time.time()
        matches_df.to_csv(output_file, index=False)

        elapsed = time.time() - start_time
        print(f"Results saved to CSV file '{output_file}' in {elapsed:.2f} seconds")
        print(f"Total matches saved: {len(matches_df)}")

    else:
        print("No matches found with the current threshold.")

    print("\nFuzzy matching process completed")


if __name__ == "__main__":
    main()