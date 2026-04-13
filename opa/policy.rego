package banking.authz

import rego.v1

# ─────────────────────────────────────────
# Main decision — this is what FastAPI reads
# ─────────────────────────────────────────

result := {
    "decision": decision,
    "score": risk_score,
    "reasons": reasons
}

# ─────────────────────────────────────────
# Main decision — Absolute Overrides First
# ─────────────────────────────────────────

result := {
    "decision": decision,
    "score": risk_score,
    "reasons": reasons
}

# 1. THE HARD BLOCK: Over ₹200,000 is instantly blocked, no matter the score.
decision := "block" if {
    input.amount > 200000
}

# 2. THE MFA TRAP: ₹50,000 to ₹200,000 forces Step-Up, unless already passed.
decision := "step_up" if {
    input.amount > 50000
    input.amount <= 200000
    not mfa_passed
}

# 3. DYNAMIC SCORING: For amounts under ₹50,000, rely on the risk score.
decision := "block" if {
    input.amount <= 50000
    risk_score >= data.thresholds.step_up
}

decision := "step_up" if {
    input.amount <= 50000
    risk_score >= data.thresholds.allow
    risk_score < data.thresholds.step_up
    not mfa_passed
}

decision := "allow" if {
    input.amount <= 50000
    risk_score < data.thresholds.allow
}

# (If they passed MFA on a medium tier, allow them through)
decision := "allow" if {
    input.amount > 50000
    input.amount <= 200000
    mfa_passed
}

decision := "block"   if risk_score >= data.thresholds.step_up
decision := "step_up" if {
    risk_score >= data.thresholds.allow
    risk_score < data.thresholds.step_up
}
decision := "allow"   if risk_score < data.thresholds.allow


# ─────────────────────────────────────────
# Risk Score — sum of all triggered signals
# ─────────────────────────────────────────

risk_score := sum(triggered_scores)

triggered_scores := [score |
    some signal in triggered_signals
    score := signal.score
]


# ─────────────────────────────────────────
# Triggered Signals — each rule adds to score
# ─────────────────────────────────────────

triggered_signals := signals if {
    signals := {signal |
        some signal in all_signals
        signal.triggered == true
    }
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
        "name": "amount_medium",
        "triggered": amount_medium,
        "score": data.score_weights.amount_medium
    },
    {
        "name": "amount_high",
        "triggered": amount_high,
        "score": data.score_weights.amount_high
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
# Helper Rules
# ─────────────────────────────────────────

default untrusted_ip := false
default blocked_ip := false
default ip_in_trusted_range := false
default off_hours := false
default amount_medium := false
default amount_high := false

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

amount_medium if {
    input.amount > 50000
    input.amount <= 100000
}

amount_high if {
    input.amount > 100000
}

# ─────────────────────────────────────────
# Reasons — human readable list for audit log
# ─────────────────────────────────────────

reasons := [reason |
    some signal in triggered_signals
    reason := concat(": ", [signal.name, format_int(signal.score, 10)])
]

# Allow Managers to access the /admin/ routes
default allow = false

allow if {
    input.role == "manager"
    startswith(input.path, "/admin/")
}

allow if {
    input.role == "admin"
    startswith(input.path, "/admin/")
}