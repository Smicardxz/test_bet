"""Provider Health Check - Test all configured providers"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

load_dotenv()


def check_api_football():
    """Check API-Football provider"""
    api_key = os.getenv("API_FOOTBALL_KEY", "")
    
    if not api_key:
        return {
            "provider": "api_football",
            "configured": False,
            "status": "❌ API KEY MISSING",
            "details": "Set API_FOOTBALL_KEY in .env"
        }
    
    try:
        from app.providers.api_football_provider import ApiFootballProvider
        provider = ApiFootballProvider()
        status = provider.test_connection()
        
        if status.get("key_valid"):
            requests_info = status.get("requests", {})
            return {
                "provider": "api_football",
                "configured": True,
                "status": "✅ CONNECTED",
                "details": f"Quota: {requests_info.get('current', 0)}/{requests_info.get('limit_day', 100)}"
            }
        else:
            return {
                "provider": "api_football",
                "configured": True,
                "status": "❌ INVALID KEY",
                "details": status.get("error", "Unknown error")
            }
    
    except Exception as e:
        return {
            "provider": "api_football",
            "configured": True,
            "status": "❌ ERROR",
            "details": str(e)
        }


def main():
    """Run health check on all providers"""
    
    print("\n" + "="*60)
    print(" PROVIDER HEALTH CHECK")
    print("="*60 + "\n")
    
    # Check API-Football
    result = check_api_football()
    print(f"{result['status']} {result['provider']}")
    print(f"   {result['details']}\n")
    
    # Summary
    if result['status'].startswith("✅"):
        print("✅ REAL DATA PIPELINE OK\n")
        return 0
    else:
        print("❌ REAL DATA NOT CONNECTED\n")
        return 1


if __name__ == "__main__":
    exit(main())
