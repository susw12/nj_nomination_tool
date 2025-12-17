from datetime import datetime
import pandas as pd

class NominationProcessor:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def _clean_replacing_field(self, text, nominee_name):
        """
        Parses the 'replacing' text to match user requirements:
        - 'Reappointment' if replacing self.
        - Name of the person being replaced.
        - 'Vacant' or 'Appointment' if empty.
        """
        if not text:
            return "Vacant"
        
        text_lower = text.lower()
        
        # Check for reappointment (self-succession)
        if "himself" in text_lower or "herself" in text_lower or nominee_name.lower() in text_lower:
            return "Reappointment"
        
        # Clean common prefixes to extract just the name
        # "Vice John Doe" -> "John Doe"
        # "To replace John Doe" -> "John Doe"
        clean_text = text.replace("Vice ", "").replace("To replace ", "").strip()
        
        # If the result is still just "Vacant" or similar, standardize it
        if "vacan" in clean_text.lower():
             return "Vacant"

        return clean_text

    def _parse_date(self, date_str):
        """Parses API date strings (handling 'Z' UTC markers)."""
        if not date_str:
            return None
        try:
            # Handle ISO format usually returned by APIs (e.g., 2025-01-14T00:00:00)
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None

    def process(self, target_year=2025):
        extracted_data = []

        for entry in self.raw_data:
            # 1. Date Filtering
            last_action_date = self._parse_date(entry.get('lastActionDate'))
            
            # Skip if no date or date is not in target year
            if not last_action_date or last_action_date.year != target_year:
                continue

            # 2. Name Extraction
            first = entry.get('firstName', '').strip()
            last = entry.get('lastName', '').strip()
            full_name = f"{first} {last}".strip()

            # 3. 'Replacing' Logic
            raw_replacing = entry.get('replacing', '')
            clean_replacing = self._clean_replacing_field(raw_replacing, full_name)

            # 4. Build Row
            row = {
                'Board/Commission': entry.get('board', 'N/A'),
                'Name': full_name,
                'Last Action Date': last_action_date.strftime('%m/%d/%Y'),
                'Last Action': entry.get('lastAction', 'N/A'),
                'Replacing': clean_replacing,
                'County': entry.get('county', 'N/A'),
                'Address': entry.get('city', 'N/A'), # 'city' is standard for address in this feed
                'LD of Residence': entry.get('legislativeDistrict', 'N/A')
            }
            extracted_data.append(row)

        # Return DataFrame sorted by date (newest first)
        df = pd.DataFrame(extracted_data)
        if not df.empty:
            df.sort_values(by='Last Action Date', ascending=False, inplace=True)
            
        return df