"""
Script to run the FastAPI application
"""

import uvicorn
from app.utils.mock_data import create_mock_data
from app.db.session import SessionLocal

if __name__ == "__main__":
    # Create mock data
    print("🔧 Creating mock data...")
    db = SessionLocal()
    try:
        create_mock_data(db)
    except Exception as e:
        print(f"⚠️ Warning: {e}")
    finally:
        db.close()
    
    # Run API
    print("\n🚀 Starting FastAPI server...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 Docs available at: http://localhost:8000/docs")
    print("\n")
    
    uvicorn.run(
        "app.main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
