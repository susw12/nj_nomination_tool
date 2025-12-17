from datetime import datetime
import pandas as pd
import xml.etree.ElementTree as ET
import re
import os

class MunicipalityLookup:
    """
    Helper to fetch and map NJ municipalities to counties using a local XML file.
    Expects 'municipalities.xml' to be in the SAME DIRECTORY as this script.
    """
    def __init__(self):
        # Determine the absolute path to the XML file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.xml_file_path = os.path.join(current_dir, "municipalities.xml")
        
        self.mapping = self._build_mapping()

    def _build_mapping(self):
        print(f"Loading county lookup from {self.xml_file_path}...")
        
        if not os.path.exists(self.xml_file_path):
            print(f"Warning: File not found at {self.xml_file_path}. County lookup will fail.")
            return {}

        try:
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()
            
            lookup = {}
            
            for muni in root.findall('municipality'):
                county = muni.find('county').text
                if not county:
                    continue
                
                # 1. Map Official Name
                official_name = muni.find('name').text
                if official_name:
                    self._add_to_lookup(lookup, official_name, county)

                # 2. Map Local Names
                local_names_node = muni.find('localNames')
                if local_names_node is not None and local_names_node.text:
                    aliases = local_names_node.text.split(';')
                    for alias in aliases:
                        self._add_to_lookup(lookup, alias, county)
            
            return lookup

        except Exception as e:
            print(f"Warning: Could not parse XML: {e}")
            return {}

    def _add_to_lookup(self, lookup_dict, city_name, county):
        if not city_name:
            return
        
        clean_name = city_name.strip().lower()
        if not clean_name:
            return

        if clean_name not in lookup_dict:
            lookup_dict[clean_name] = set()
        
        lookup_dict[clean_name].add(county.strip())

    def get_county(self, city_name):
        if not city_name or city_name == "N/A":
            return "N/A"
        
        city_clean = city_name.strip().lower()
        counties = self.mapping.get(city_clean)
        
        if counties:
            return ", ".join(sorted(list(counties)))
            
        return "N/A"


class NominationProcessor:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.geo_lookup = MunicipalityLookup()

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y")
        except ValueError:
            return None

    def _clean_board_name(self, text):
        if not text:
            return "N/A"
        
        clean = text
        prefixes = [
            "to be a member of the ", 
            "to be a member of ", 
            "to be a judge of the ",
            "to be a judge of ",
            "to be the ", 
            "to be an "
        ]
        
        matched = True
        while matched:
            matched = False
            lower_clean = clean.lower()
            for p in prefixes:
                if lower_clean.startswith(p):
                    clean = clean[len(p):]
                    matched = True
                    break
        
        return clean.strip()

    def _clean_replacing_field(self, term_text, nominee_name):
        if not term_text:
            return "Vacant"
        
        text_lower = term_text.lower()
        
        # 1. Vacancy Check
        if "fill a vacancy" in text_lower and "replace" not in text_lower and "succeed" not in text_lower:
            return "Vacant"
        
        # 2. Reappointment Check
        if "succeed himself" in text_lower or "succeed herself" in text_lower or nominee_name.lower() in text_lower:
            return "Reappointment"
        
        # 3. Name Extraction
        match = re.search(r"(?:replace|succeed)\s+([^,]+)", term_text, re.IGNORECASE)
        if match:
            extracted_name = match.group(1).replace("the Honorable", "").strip()
            if "vacan" in extracted_name.lower():
                return "Vacant"
            return extracted_name

        # 4. Generic Term Check
        if "for the term prescribed by law" in text_lower or "for term" in text_lower:
            return "for term"

        # 5. Final Vacancy Catch
        if "vacan" in text_lower:
            return "Vacant"
            
        return "Appointment"

    def process(self, target_year=2025):
        if not isinstance(self.raw_data, list) or len(self.raw_data) < 2:
            print("Error: Data format incorrect. Expected list of two lists.")
            return pd.DataFrame()

        profiles_list = self.raw_data[0]
        actions_list = self.raw_data[1]

        # Map Actions
        action_map = {}
        for action in actions_list:
            key = (
                action.get('FirstName', '').strip(), 
                action.get('LastName', '').strip(), 
                action.get('Nominee_Sequence', 0)
            )
            if key not in action_map:
                action_map[key] = []
            
            dt = self._parse_date(action.get('agendaDate'))
            if dt:
                action_map[key].append({
                    'date': dt,
                    'action': action.get('NominationAction')
                })

        extracted_data = []

        # Process Profiles
        for profile in profiles_list:
            first = profile.get('FirstName', '').strip()
            last = profile.get('LastName', '').strip()
            seq = profile.get('Nominee_Sequence', 0)
            
            key = (first, last, seq)
            person_actions = action_map.get(key, [])
            
            if not person_actions:
                continue

            person_actions.sort(key=lambda x: x['date'], reverse=True)
            most_recent = person_actions[0]
            
            if most_recent['date'].year != target_year:
                continue

            full_name = f"{first} {profile.get('MiddleName', '')} {last} {profile.get('Suffix') or ''}".replace("  ", " ").strip()
            
            city = profile.get('Resides_At', 'N/A')
            county = self.geo_lookup.get_county(city)

            row = {
                'Board/Commission': self._clean_board_name(profile.get('Position', '')),
                'Name': full_name,
                'Last Action Date': most_recent['date'].strftime('%m/%d/%Y'),
                'Last Action': most_recent['action'],
                'Replacing': self._clean_replacing_field(profile.get('Term', ''), full_name),
                'County': county,
                'Address': city,
                'LD of Residence': "N/A"
            }
            extracted_data.append(row)

        df = pd.DataFrame(extracted_data)
        if not df.empty:
            df.sort_values(by='Last Action Date', ascending=False, inplace=True)
            
        return df