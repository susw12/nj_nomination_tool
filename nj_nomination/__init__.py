from .client import NJLegAPIClient
from .processor import NominationProcessor

def get_2025_nominations():
    client = NJLegAPIClient()
    data = client.fetch_nominations()
    
    processor = NominationProcessor(data)
    df = processor.process(target_year=2025)
    
    return df