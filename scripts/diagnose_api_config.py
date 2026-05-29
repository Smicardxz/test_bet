"""
Diagnostic API Configuration
Vérifie précisément comment la clé API est chargée
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env BEFORE importing anything
from dotenv import load_dotenv

# Try to find .env
env_path = project_root / ".env"
env_exists = env_path.exists()

print("\n" + "="*60)
print(" DIAGNOSTIC API CONFIGURATION")
print("="*60 + "\n")

print("📂 Environment File:")
print(f"   Path: {env_path}")
print(f"   Exists: {env_exists}")
print(f"   Working directory: {os.getcwd()}")
print()

# Load .env
if env_exists:
    load_dotenv(env_path)
    print("✅ .env loaded")
else:
    print("⚠️  .env not found, using system environment only")

print()

# Check environment variables
print("🔑 Environment Variables:")
print()

# 1. DATA_PROVIDER
data_provider = os.getenv("DATA_PROVIDER", "NOT_SET")
print(f"1. DATA_PROVIDER")
print(f"   Value: {data_provider}")
print(f"   Expected: api_football")
print(f"   Match: {'✅' if data_provider == 'api_football' else '❌'}")
print()

# 2. API_FOOTBALL_KEY
api_key = os.getenv("API_FOOTBALL_KEY", "")
api_key_present = len(api_key) > 0

print(f"2. API_FOOTBALL_KEY")
print(f"   Present: {'✅ YES' if api_key_present else '❌ NO'}")
if api_key_present:
    print(f"   Length: {len(api_key)} characters")
    print(f"   First 4 chars: {api_key[:4]}...")
    print(f"   Last 4 chars: ...{api_key[-4:]}")
else:
    print(f"   Value: (empty)")
print()

# 3. API_FOOTBALL_URL
api_url = os.getenv("API_FOOTBALL_URL", "")
print(f"3. API_FOOTBALL_URL")
print(f"   Value: {api_url if api_url else '(not set, will use default)'}")
print(f"   Default: https://v3.football.api-sports.io")
print()

# Check for common mistakes
print("🔍 Common Issues Check:")
print()

# Check for wrong variable names
wrong_names = [
    "API_KEY",
    "FOOTBALL_API_KEY",
    "X_RAPIDAPI_KEY",
    "RAPIDAPI_KEY",
    "APISPORTS_KEY"
]

for name in wrong_names:
    value = os.getenv(name, "")
    if value:
        print(f"⚠️  Found {name} = {value[:10]}... (wrong variable name!)")

# Check for BOM or encoding issues
if env_exists:
    try:
        with open(env_path, 'rb') as f:
            content = f.read()
            if content.startswith(b'\xef\xbb\xbf'):
                print("⚠️  .env file has BOM (UTF-8 with BOM) - may cause issues")
            else:
                print("✅ .env file encoding OK (no BOM)")
    except Exception as e:
        print(f"⚠️  Could not check .env encoding: {e}")

print()

# Try to initialize provider
print("🔌 Provider Initialization:")
print()

try:
    from app.config.data_source_config import DataSourceConfig
    
    config = DataSourceConfig()
    
    print(f"   Source type: {config.source_type.value}")
    print(f"   Is real data: {config.is_real_data}")
    print(f"   Is mock data: {config.is_mock_data}")
    print()
    
    print("   Attempting to get provider...")
    try:
        provider = config.get_provider()
        print(f"   ✅ Provider: {provider.config.name}")
        print(f"   Type: {type(provider).__name__}")
        
        # Check if it's the right provider
        if "Mock" in type(provider).__name__:
            print(f"   ❌ PROBLEM: Got MockDataProvider instead of ApiFootballProvider!")
        else:
            print(f"   ✅ Got real provider")
            
    except ValueError as e:
        print(f"   ❌ ValueError: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"   ❌ Failed to load config: {e}")
    import traceback
    traceback.print_exc()

print()

# Summary
print("="*60)
print(" SUMMARY")
print("="*60)
print()

issues = []

if not env_exists:
    issues.append(".env file not found")

if data_provider != "api_football":
    issues.append(f"DATA_PROVIDER is '{data_provider}', should be 'api_football'")

if not api_key_present:
    issues.append("API_FOOTBALL_KEY is not set")

if issues:
    print("❌ ISSUES FOUND:")
    for issue in issues:
        print(f"   - {issue}")
    print()
    print("🔧 TO FIX:")
    print("   1. Ensure .env file exists in project root")
    print("   2. Add: DATA_PROVIDER=api_football")
    print("   3. Add: API_FOOTBALL_KEY=your_key_here")
    print("   4. Restart Flask/scripts")
else:
    print("✅ CONFIGURATION OK")
    print("   - .env file found")
    print("   - DATA_PROVIDER = api_football")
    print("   - API_FOOTBALL_KEY is set")

print()
