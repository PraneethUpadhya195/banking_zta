import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/banking/authz/result")


async def evaluate_policy(
    user: str,
    role: str,
    path: str,
    method: str,
    ip: str,
    device_registered: bool = False,
    is_blocked: bool = False,
    amount: float = 0.0,
    device_id: str = None,
    last_ip: str = None,
    minutes_since_last_action: float = 0.0,
    mfa_verified: bool = False
) -> dict:
    input_data = {
        "input": {
            "user": user,
            "role": role,
            "path": path,
            "method": method,
            "ip": ip,
            "device_registered": device_registered,
            "is_blocked": is_blocked,
            #"hour": 3,
            "hour": datetime.utcnow().hour,
            "amount": amount,
            "device_id": device_id or "",
            "last_ip": last_ip,
            "minutes_since_last_action": minutes_since_last_action,
            "mfa_verified": mfa_verified
        }
    }

    print(f"2. Sending to OPA: mfa_verified is {input_data['input']['mfa_verified']}")
    print(f"----------------------\n")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(OPA_URL, json=input_data, timeout=5.0)
            result = response.json().get("result", {})
            return {
                "decision": result.get("decision", "block"),
                "score": result.get("score", 100),
                "reasons": result.get("reasons", [])
            }
    except Exception as e:
        print(f"OPA error: {e}")
        # fail closed — if OPA is unreachable, block the request
        return {
            "decision": "block",
            "score": 100,
            "reasons": ["opa_unreachable: +100"]
        }