#!/usr/bin/env python3
"""Check Railway super admin accounts."""
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    users = conn.execute(text("""
        SELECT email, full_name, is_active, created_at
        FROM users
        WHERE is_platform_admin = true
        ORDER BY created_at
        LIMIT 5
    """)).fetchall()
    
    if users:
        print("Super Admin accounts on Railway:")
        print("=" * 60)
        for user in users:
            print(f"Email: {user[0]}")
            print(f"Full Name: {user[1]}")
            print(f"Active: {user[2]}")
            print(f"Created: {user[3]}")
            print("=" * 60)
    else:
        print("No super admin found")
