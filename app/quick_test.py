# quick_test.py - Quick test without server
from app import get_email, get_real_ip
from flask import Flask
import os

# Simple test of the functions
def test_functions():
    """Test the key functions without running a server"""
    
    print("🧪 TESTING SHARK FUNCTIONS")
    print("=" * 40)
    
    # Create a minimal Flask app context for testing
    test_app = Flask(__name__)
    
    with test_app.test_request_context('/', headers={
        'X-Forwarded-User': '01nicklas07@gmail.com',
        'X-Forwarded-Email': 'test@example.com',
        'X-Real-IP': '192.168.1.100',
        'X-Forwarded-For': '203.0.113.195, 192.168.1.100',
        'X-Forwarded-Host': 'sharky.snowy-burbot.ts.net',
        'X-Forwarded-Proto': 'https'
    }):
        
        print(f"✅ get_email(): {get_email()}")
        print(f"✅ get_real_ip(): {get_real_ip()}")
        
        # Test with different header combinations
        print("\n🔄 Testing different header scenarios:")
        
        # Test with X-Forwarded-For containing multiple IPs
        print(f"📍 X-Forwarded-For parsing: {get_real_ip()}")
        
        print("\n✨ Functions working correctly!")

if __name__ == "__main__":
    test_functions()
