import requests

class NJLegAPIClient:
    BASE_URL = "https://www.njleg.state.nj.us/api/senateNominations"

    def fetch_nominations(self):
        """Fetches the raw JSON data from the Senate Nominations API."""
        try:
            response = requests.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Failed: {e}")
            return []