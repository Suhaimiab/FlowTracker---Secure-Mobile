#!/usr/bin/env python3
"""
Password Hash Generator for VandaTrack Navigator
Generates SHA256 hash for password protection
"""

import hashlib
import getpass

def generate_password_hash():
    """Generate SHA256 hash for password."""
    
    print("=" * 60)
    print("🔐 VandaTrack Navigator - Password Hash Generator")
    print("=" * 60)
    print()
    
    print("This tool generates a SHA256 hash for your password.")
    print("The hash will be stored in Streamlit secrets for authentication.")
    print()
    
    while True:
        # Get password (hidden input)
        password = getpass.getpass("Enter your password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("❌ Passwords don't match. Please try again.\n")
            continue
        
        if len(password) < 8:
            print("⚠️  Password too short. Minimum 8 characters required.\n")
            continue
        
        break
    
    # Generate hash
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    print()
    print("✅ Password hash generated successfully!")
    print()
    print("=" * 60)
    print("Copy this hash to your secrets.toml file:")
    print("=" * 60)
    print()
    print(f'password_hash = "{password_hash}"')
    print()
    print("=" * 60)
    print()
    print("For Streamlit Cloud deployment:")
    print("1. Go to your app settings")
    print("2. Click on 'Secrets'")
    print("3. Add this line:")
    print(f'   password_hash = "{password_hash}"')
    print()
    print("⚠️  IMPORTANT: Keep this hash secure!")
    print("   Do NOT share it publicly or commit to GitHub.")
    print()

if __name__ == "__main__":
    generate_password_hash()
