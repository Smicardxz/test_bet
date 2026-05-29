"""Test DataSourceConfig with API-Football"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

load_dotenv()

from app.config.data_source_config import DataSourceConfig, DataSourceType


def main():
    """Test data source configuration"""
    
    print("\n" + "="*60)
    print(" DATA SOURCE CONFIGURATION TEST")
    print("="*60 + "\n")
    
    # Show environment
    env_provider = os.getenv("DATA_PROVIDER", "not set")
    print(f"Environment DATA_PROVIDER: {env_provider}\n")
    
    # Initialize config
    config = DataSourceConfig()
    
    print(f"Source Type: {config.source_type}")
    print(f"Source Label: {config.source_label}")
    print(f"Is Real Data: {config.is_real_data}")
    print(f"Is Mock Data: {config.is_mock_data}\n")
    
    # Get provider
    print("Getting provider...")
    try:
        provider = config.get_provider()
        print(f"✅ Provider: {provider.__class__.__name__}")
        print(f"   Config Name: {provider.config.name}")
        
        # Test connection if API-Football
        if config.source_type == DataSourceType.API_FOOTBALL:
            print("\nTesting API connection...")
            status = provider.test_connection()
            
            if status.get("key_valid"):
                print("✅ API Key Valid")
                requests = status.get("requests", {})
                print(f"   Quota: {requests.get('current', 0)}/{requests.get('limit_day', 100)}")
            else:
                print(f"❌ API Error: {status.get('error')}")
        
        # Test fetching matches
        print("\nFetching today's matches...")
        response = provider.get_today_matches()
        
        if response.success:
            print(f"✅ {len(response.data)} matches retrieved")
            print(f"   Provider: {response.provider}")
        else:
            print(f"❌ Error: {response.error}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    print("\n" + "="*60)
    print(" CONFIGURATION OK")
    print("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
