from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests

security = HTTPBearer()

# Replace with your actual Keycloak realm details
KEYCLOAK_URL = "http://localhost:8080/realms/banking/protocol/openid-connect/certs"
ALGORITHM = "RS256"
AUDIENCE = "account" # Or whatever your client audience is configured to

def get_public_key(token: str):
    # In production, cache this request!
    jwks = requests.get(KEYCLOAK_URL).json()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
            break
    return rsa_key

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        rsa_key = get_public_key(token)
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            options={"verify_aud": False} # Adjust based on your strictness
        )
        
        # Priority 2 Fix: Robust Role Extraction
        roles = payload.get("realm_access", {}).get("roles", [])
        role_priority = ["admin", "manager", "teller", "customer"]
        primary_role = "customer" # Default fallback
        
        for r in role_priority:
            if r in roles:
                primary_role = r
                break
                
        # Attach the normalized role to the payload so downstream services don't have to guess
        payload["normalized_role"] = primary_role
        
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Keycloak token: {str(e)}")