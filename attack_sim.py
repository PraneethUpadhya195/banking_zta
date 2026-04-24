import requests
import json

# Your local OPA server endpoint
OPA_URL = "http://localhost:8181/v1/data/banking/authz"

def run_attack_simulation():
    print("="*75)
    print("ZTA POLICY ENGINE - ATTACK MATRIX SIMULATOR")
    print("="*75)
    print(f"{'SCENARIO':<35} | {'EXPECTED':<10} | {'ACTUAL':<10} | {'SCORE':<5}")
    print("-" * 75)

    test_cases = [
        {
            "name": "1. The Perfect User (Baseline)",
            "description": "Customer, normal amount, daytime, trusted IP, registered device.",
            "expected": "allow",
            "input": {
                "role": "customer", "path": "/transfer/", "amount": 10000,
                "ip": "192.168.1.50", "hour": 14, "device_registered": True, 
                "mfa_verified": False, "is_blocked": False
            }
        },
        {
            "name": "2. Privilege Escalation (RBAC)",
            "description": "Customer trying to access the /admin/ dashboard.",
            "expected": "deny", # OPA defaults to deny if no allow rule matches
            "input": {
                "role": "customer", "path": "/admin/dashboard", "amount": 0,
                "ip": "192.168.1.50", "hour": 14, "device_registered": True, 
                "mfa_verified": False, "is_blocked": False
            }
        },
        {
            "name": "3. The Heist (Absolute Block)",
            "description": "Massive transfer > ₹200k, overrides all good behavior.",
            "expected": "block",
            "input": {
                "role": "customer", "path": "/transfer/", "amount": 250000,
                "ip": "192.168.1.50", "hour": 14, "device_registered": True, 
                "mfa_verified": False, "is_blocked": False
            }
        },
        {
            "name": "4. The Business Trap (MFA)",
            "description": "Normal user, trusted context, but amount is ₹75k (>50k).",
            "expected": "step_up",
            "input": {
                "role": "customer", "path": "/transfer/", "amount": 75000,
                "ip": "192.168.1.50", "hour": 14, "device_registered": True, 
                "mfa_verified": False, "is_blocked": False
            }
        },
        {
            "name": "5. Credential Stuffing (Risk Trap)",
            "description": "Small amount (₹5k), but untrusted IP + Mobile + Off-hours.",
            "expected": "step_up",
            "input": {
                "role": "customer", "path": "/transfer/", "amount": 5000,
                "ip": "203.0.113.5", "hour": 3, "device_registered": False, 
                "mfa_verified": False, "is_blocked": False
            }
        },
        {
            "name": "6. Mitigated Threat (MFA Passed)",
            "description": "Same as Case 5, but the user successfully provided TOTP.",
            "expected": "allow",
            "input": {
                "role": "customer", "path": "/transfer/", "amount": 5000,
                "ip": "203.0.113.5", "hour": 3, "device_registered": False, 
                "mfa_verified": True, "is_blocked": False
            }
        },
        {
            "name": "7. Known Threat Intel (Hard Block)",
            "description": "Attacker IP is on the explicit blocklist.",
            "expected": "block",
            "input": {
                "role": "customer", "path": "/transfer/", "amount": 1000,
                "ip": "1.2.3.4", "hour": 14, "device_registered": True, 
                "mfa_verified": False, "is_blocked": False
            }
        },
        {
            "name": "8. Impossible Travel",
            "description": "Logged in from two different IPs within 60 minutes.",
            "expected": "allow",
            "input": {
                "role": "customer", "path": "/transfer/", "amount": 5000,
                "ip": "45.22.12.9", "last_ip": "192.168.1.50", "minutes_since_last_action": 15,
                "hour": 14, "device_registered": True, "mfa_verified": False, "is_blocked": False
            }
        }
    ]

    passed_tests = 0

    for case in test_cases:
        payload = {"input": case["input"]}
        try:
            response = requests.post(OPA_URL, json=payload)
            data = response.json().get("result", {})
            
            # Extract decision
            decision = data.get("decision", "deny" if not data.get("allow") else "allow")
            score = data.get("risk_score", 0)
            
            # Format output
            status = " PASS" if decision == case["expected"] else " FAIL"
            if status == " PASS":
                passed_tests += 1
                
            print(f"{case['name']:<35} | {case['expected']:<10} | {decision:<10} | {score:<5} | {status}")
            
        except requests.exceptions.ConnectionError:
            print("CRITICAL ERROR: Could not connect to OPA. Is it running on port 8181?")
            return

    print("-" * 75)
    print(f"SIMULATION COMPLETE: {passed_tests}/{len(test_cases)} Tests Passed.")
    print("="*75)

if __name__ == "__main__":
    run_attack_simulation()