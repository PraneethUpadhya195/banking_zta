package banking.authz

import rego.v1

# ─────────────────────────────────────────
# 1. Main Decision Output
# ─────────────────────────────────────────
result := {
    "decision": decision,
    "score": risk_score,
    "reasons": reasons
}

default decision := "deny"

# ─────────────────────────────────────────
# 2. Decision Logic (Hierarchical)
# ─────────────────────────────────────────

# A2. RBAC Hard Block (Privilege Escalation)
decision := "deny" if {
    is_unauthorized
}

# A. The Hard Blocks (Overrides Everything)
decision := "block" if {
    input.amount > 200000
}

decision := "block" if {
    input.amount <= 200000
    risk_score >= data.thresholds.block
}

# B. The MFA Traps (Step-Up)
decision := "step_up" if {
    input.amount > 50000
    input.amount <= 200000
    not mfa_passed
    risk_score < data.thresholds.block
}

decision := "step_up" if {
    input.amount <= 50000
    risk_score >= data.thresholds.allow
    risk_score < data.thresholds.block
    not mfa_passed
}

# C. The Allows
decision := "allow" if {
    input.amount <= 50000
    risk_score < data.thresholds.allow
}

# If they passed MFA on a step-up tier, allow them through
decision := "allow" if {
    input.amount <= 200000
    mfa_passed
    risk_score < data.thresholds.block
}

# ─────────────────────────────────────────
# 3. Risk Score Calculation
# ─────────────────────────────────────────
risk_score := sum(triggered_scores)

triggered_scores := [score |
    some signal in triggered_signals
    score := signal.score
]

triggered_signals := {signal |
    some signal in all_signals
    signal.triggered == true
}

all_signals := [
    {
        "name": "unregistered_device",
        "triggered": unregistered_device,
        "score": data.score_weights.unregistered_device
    },
    {
        "name": "untrusted_ip",
        "triggered": untrusted_ip,
        "score": data.score_weights.untrusted_ip
    },
    {
        "name": "blocked_ip",
        "triggered": blocked_ip,
        "score": data.score_weights.blocked_ip
    },
    {
        "name": "off_hours",
        "triggered": off_hours,
        "score": data.score_weights.off_hours
    },
    {
        "name": "user_blocked",
        "triggered": user_blocked,
        "score": data.score_weights.user_blocked
    },
    {
        "name": "impossible_travel",
        "triggered": impossible_travel,
        "score": data.score_weights.impossible_travel
    },
    {
        "name": "mfa_passed",
        "triggered": mfa_passed,
        "score": data.score_weights.mfa_passed
    }
]

# ─────────────────────────────────────────
# 4. Helper Rules
# ─────────────────────────────────────────
default untrusted_ip := false
default blocked_ip := false
default ip_in_trusted_range := false
default off_hours := false

default is_unauthorized := false
is_unauthorized if {
    startswith(input.path, "/admin/")
    input.role == "customer"
}

default impossible_travel := false
impossible_travel if {
    input.ip != input.last_ip
    input.last_ip != null  # Prevents firing on their very first login
    input.minutes_since_last_action < 60
}

default unregistered_device := false
unregistered_device if {
    input.device_registered == false
}

default mfa_passed := false
mfa_passed if {
    input.mfa_verified == true
}

default user_blocked := false
user_blocked if {
    input.is_blocked == true
}

untrusted_ip if {
    not blocked_ip
    not ip_in_trusted_range
}

blocked_ip if {
    some blocked in data.blocked_ips
    input.ip == blocked
}

ip_in_trusted_range if {
    some trusted in data.trusted_ip_ranges
    startswith(input.ip, trusted)
}

off_hours if {
    input.hour < data.trusted_hours.start
}

off_hours if {
    input.hour >= data.trusted_hours.end
}

# ─────────────────────────────────────────
# 5. Reasons & RBAC
# ─────────────────────────────────────────
reasons := [reason |
    some signal in triggered_signals
    reason := concat(": ", [signal.name, format_int(signal.score, 10)])
]

default allow = false

allow if {
    input.role == "manager"
    startswith(input.path, "/admin/")
}

allow if {
    input.role == "admin"
    startswith(input.path, "/admin/")
}