from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx

# This tells FastAPI to look for the "Authorization: Bearer <token>" header
security = HTTPBearer()

# Your local Keycloak realm URL for public keys
KEYCLOAK_CERTS_URL = "http://localhost:8080/realms/banking/protocol/openid-connect/certs"

def get_public_keys():
    try:
        response = httpx.get(KEYCLOAK_CERTS_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot reach Keycloak: {str(e)}")

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        jwks = get_public_keys()
        
        # Decode and verify the token signature
        # We temporarily disable audience verification to ensure baseline connectivity
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False} 
        )
        return payload
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )