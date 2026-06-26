#!/usr/bin/env python3
"""
Seed optimization strategies for One8 tenant on Railway.
Calls the admin API endpoint with super-admin authentication.
"""
import sys
import jwt
import requests

# Railway backend URL
BACKEND_URL = "https://alpmarklabs-production.up.railway.app"

# JWT secret from Railway environment
AUTH_JWT_SECRET = "VoQK4-bnpQDG6RpBiQlkGGwOq2QUDoQPWdD5qk7T1piYPAMT6aZ288LejXjFDEbt"
AUTH_JWT_ALGORITHM = "HS256"

# Super admin email
SUPER_ADMIN_EMAIL = "admin@alpmark.ai"


def generate_token(email: str, platform_role: str = "super_admin") -> str:
    """Generate a JWT token for authentication."""
    payload = {
        "sub": email,
        "email": email,
        "platform_role": platform_role,
    }
    return jwt.encode(payload, AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALGORITHM)


def seed_strategies():
    """Call the Railway API to seed optimization strategies."""
    token = generate_token(SUPER_ADMIN_EMAIL)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    url = f"{BACKEND_URL}/admin/optimization-strategies/seed"
    
    print(f"Seeding optimization strategies at {url}...")
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print("\n✅ Optimization strategies seeded successfully!")
        print(f"   Tenant: {data.get('tenant', 'N/A')}")
        print(f"   Strategies created: {data.get('strategies_created', 0)}")
        print(f"   Enabled strategies: {data.get('enabled_strategies', 0)}")
        
        if "strategies" in data:
            print("\n📋 Strategies:")
            for s in data["strategies"]:
                status = "✅ ENABLED" if s["is_enabled"] else "⚪ disabled"
                print(f"   • {s['domain']:12} | {s['strategy_name']:35} | {status}")
        
        return 0
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        if e.response is not None:
            print(f"   Response: {e.response.text}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(seed_strategies())
