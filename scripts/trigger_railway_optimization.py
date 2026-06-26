#!/usr/bin/env python3
"""
Manually trigger the optimization engine on Railway to generate recommendations.
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


def trigger_optimization_engine():
    """Call the Railway API to trigger optimization engine."""
    token = generate_token(SUPER_ADMIN_EMAIL)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    url = f"{BACKEND_URL}/admin/optimization-engine/trigger"
    
    print(f"Triggering optimization engine at {url}...")
    
    try:
        response = requests.post(url, headers=headers, timeout=300)  # 5 min timeout
        response.raise_for_status()
        
        data = response.json()
        print("\n✅ Optimization engine triggered successfully!")
        print(f"   Tenants processed: {data.get('tenants_processed', 'N/A')}")
        print(f"   Recommendations generated: {data.get('recommendations_generated', 'N/A')}")
        
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
    sys.exit(trigger_optimization_engine())
