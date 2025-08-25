# test_headers.py - Test different header scenarios
import requests
import json

BASE_URL = "http://localhost:5000"

def test_scenario(name, headers):
    """Test a specific header scenario"""
    print(f"\n🧪 Testing: {name}")
    print("-" * 40)
    
    try:
        # Test the whoami endpoint
        response = requests.get(f"{BASE_URL}/api/whoami", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Email: {data.get('email', 'None')}")
            print(f"✅ IP: {data.get('ip_address', 'None')}")
            print(f"✅ Host: {data.get('host', 'None')}")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("   Make sure the dev server is running!")

def run_tests():
    """Run various header test scenarios"""
    print("🦈 SHARK HEADER TESTING SUITE")
    print("=" * 50)
    
    # Scenario 1: Your actual Tailscale setup
    test_scenario("Your Tailscale Setup", {
        'X-Forwarded-User': '01nicklas07@gmail.com',
        'X-Forwarded-Email': None,
        'X-Auth-Request-Email': None,
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Host': 'sharky.snowy-burbot.ts.net',
        'X-Forwarded-Uri': None,
        'X-Real-IP': None,
        'X-Forwarded-For': '203.0.113.195, 192.168.1.100'
    })
    
    # Scenario 2: Standard oauth2-proxy setup
    test_scenario("Standard OAuth2-Proxy", {
        'X-Forwarded-Email': 'test@example.com',
        'X-Auth-Request-Email': 'test@example.com',
        'X-Real-IP': '192.168.1.100',
        'X-Forwarded-For': '203.0.113.195',
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Host': 'example.com'
    })
    
    # Scenario 3: Cloudflare proxy
    test_scenario("Cloudflare Proxy", {
        'CF-Connecting-IP': '203.0.113.195',
        'X-Forwarded-Email': 'cloudflare@example.com',
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Host': 'cf.example.com'
    })
    
    # Scenario 4: No auth headers (anonymous)
    test_scenario("Anonymous/No Headers", {
        'User-Agent': 'Test-Browser/1.0'
    })
    
    print(f"\n🔗 View results at: {BASE_URL}")
    print(f"📝 Check logs at: {BASE_URL}/logs")

if __name__ == "__main__":
    run_tests()
