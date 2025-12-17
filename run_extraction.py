from nj_nomination import get_2025_nominations

def main():
    print("Fetching 2025 Senate Nominations...")
    df = get_2025_nominations()

    if df.empty:
        print("No nominations found for 2025.")
    else:
        # Save to CSV
        output_file = "senate_nominations_2025.csv"
        df.to_csv(output_file, index=False)
        
        # Print preview to console
        print(f"\nSuccess! Found {len(df)} records.")
        print(df.head().to_markdown(index=False))
        print(f"\nFull file saved to: {output_file}")

if __name__ == "__main__":
    main()