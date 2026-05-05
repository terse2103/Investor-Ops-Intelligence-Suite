"""Mint JWTs using Supabase Admin API (service-role key, no passwords needed)."""
import json, sys, httpx

SUPABASE_URL = "https://lepcsaucizpcvvfuwhyi.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxlcGNzYXVjaXpwY3Z2ZnV3aHlpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Njk2MTYwMCwiZXhwIjoyMDkyNTM3NjAwfQ.v1HXwOoCoerxiC9riIVyGHz3swPn6HJ_gkkclqStVAs"

ADMIN_EMAIL = "atharvterse21@gmail.com"
USER_EMAIL = "atharv.cognizance@gmail.com"

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}

def generate_link(email: str) -> str:
    """Generate an OTP link via admin API and extract the access_token."""
    resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/admin/generate_link",
        json={"email": email, "type": "magiclink"},
        headers=HEADERS,
        timeout=15.0,
    )
    if resp.status_code != 200:
        print(f"generate_link FAILED for {email}: {resp.status_code} {resp.text}", file=sys.stderr)
        return ""
    data = resp.json()
    # The response contains hashed_token; we need to verify it to get a JWT.
    # Alternative: use the admin API to create a session directly.
    hashed = data.get("hashed_token", "")
    action_link = data.get("action_link", "")
    print(f"  action_link for {email}: {action_link[:80]}...", file=sys.stderr)
    
    # Extract the token_hash and use verify endpoint
    import urllib.parse
    parsed = urllib.parse.urlparse(action_link)
    params = urllib.parse.parse_qs(parsed.fragment or parsed.query)
    # Supabase magic link format: ...#access_token=... or /verify?token=...&type=magiclink
    
    # Try to verify the OTP via the token_hash
    token_hash = params.get("token_hash", [None])[0] or params.get("token", [None])[0]
    if not token_hash:
        # Try fragment
        fragment = parsed.fragment
        if fragment:
            fparams = urllib.parse.parse_qs(fragment)
            token_hash = fparams.get("token_hash", [None])[0]
    
    if not token_hash:
        print(f"  Could not extract token_hash from action_link", file=sys.stderr)
        return ""
    
    # Verify the OTP to get a session
    verify_resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/verify",
        json={"token_hash": token_hash, "type": "magiclink"},
        headers={"apikey": SERVICE_ROLE_KEY, "Content-Type": "application/json"},
        timeout=15.0,
    )
    if verify_resp.status_code != 200:
        print(f"  verify FAILED: {verify_resp.status_code} {verify_resp.text[:200]}", file=sys.stderr)
        return ""
    return verify_resp.json().get("access_token", "")


if __name__ == "__main__":
    print("Minting USER_JWT...", file=sys.stderr)
    user_jwt = generate_link(USER_EMAIL)
    print("Minting ADMIN_JWT...", file=sys.stderr)
    admin_jwt = generate_link(ADMIN_EMAIL)
    
    if user_jwt:
        print(f"USER_JWT={user_jwt}")
    else:
        print("Failed to get USER_JWT", file=sys.stderr)
    
    if admin_jwt:
        print(f"ADMIN_JWT={admin_jwt}")
    else:
        print("Failed to get ADMIN_JWT", file=sys.stderr)
