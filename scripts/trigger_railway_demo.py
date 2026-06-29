#!/usr/bin/env python3
"""Quick script to call Railway admin endpoint to trigger demo data."""

import jwt
import requests

# Generate super-admin token (using Railway's secret)
AUTH_JWT_SECRET = "VoQK4-bnpQDG6RpBiQlkGGwOq2QUDoQPWdD5qk7T1piYPAMT6aZ288LejXjFDEbt"
AUTH_JWT_ALGORITHM = "HS256"

token_payload = {
    "sub": "admin@alpmark.com",
    "email": "admin@alpmark.com",
    "platform_role": "super_admin",
}

token = jwt.encode(token_payload, AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALGORITHM)

# Call Railway endpoint
railway_url = "https://alpmarklabs-production.up.railway.app"
endpoint = f"{railway_url}/admin/demo-data/trigger"

print(f"🎯 Triggering demo data on Railway...")
print(f"Endpoint: {endpoint}\n")

response = requests.post(
    endpoint,
    headers={"Authorization": f"Bearer {token}"},
    timeout=60,
)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Success!")
    print(f"   Orders created: {data.get('orders_created', 0)}")
    print(f"   Line items created: {data.get('line_items_created', 0)}")
else:
    print(f"❌ Error {response.status_code}")
    print(f"   {response.text}")
