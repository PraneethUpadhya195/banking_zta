# 🏦 Zero Trust Architecture — Banking Engine

> *"Never trust, always verify."*

A full-stack core banking simulation built entirely on **Zero Trust Architecture (ZTA)** principles. Unlike traditional perimeter-based security, this system continuously evaluates the risk of every network connection, user session, and individual transaction — in real time — before granting access or executing operations.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔐 **mTLS Device Verification** | Nginx drops all connections at the network layer unless the device holds a valid cryptographic client certificate (`.p12`) |
| 🧠 **Dynamic Risk Assessment** | Open Policy Agent (OPA) evaluates every transaction in real time and returns a `Low / Medium / High` risk score |
| 📲 **Step-Up Authentication (TOTP)** | High-risk transactions trigger a TOTP MFA challenge via `pyotp` before funds are released |
| 👤 **Centralized IAM & RBAC** | Keycloak handles JWT issuance and enforces `customer` / `manager` role-based access control |
| 🌐 **Same-Origin Architecture** | Nginx serves both the React frontend and FastAPI backend under a single secure origin (`https://localhost`), eliminating CORS vulnerabilities and preflight mTLS conflicts |
| 🗄️ **ACID-Compliant Vault** | PostgreSQL guarantees data integrity, prevents race conditions, and ensures safe financial rollbacks |

---

## 🏗️ Architecture & Project Structure

```
banking-zta/
├── certs/                   # Security Infrastructure (⚠️ DO NOT COMMIT)
│   ├── ca.crt               # Local Certificate Authority
│   ├── ca.key               # CA Private Key
│   ├── server.crt           # Nginx Server Identity Certificate
│   ├── server.key           # Nginx Server Private Key
│   └── client.p12           # Trusted Device Identity (browser import)
│
├── frontend/                # Client UI — React + Vite
│   └── src/
│       └── api/
│           └── axios.js     # Axios interceptors for Keycloak JWT injection
│
├── backend/                 # Policy Enforcement Point — FastAPI
│   ├── core/                # Routing, Auth Logic, TOTP verification
│   └── shared/              # PostgreSQL models & async DB connections
│
├── opa/                     # Policy Decision Point
│   └── policy.rego          # Rego rules engine for dynamic risk scoring
│
├── .env                     # Environment variables (⚠️ DO NOT COMMIT)
└── nginx.conf               # API Gateway & mTLS Enforcer
```

---

## 🔄 Zero Trust Request Flow

Every request passes through four sequential enforcement layers before a transaction is executed:

```
  [Browser]
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Layer 1 — NETWORK (Nginx + mTLS)                   │
│  Validates client.p12 certificate. Rejects on miss. │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Layer 2 — AUTHENTICATION (Keycloak JWT)            │
│  FastAPI verifies token signature, extracts UUID    │
│  and RBAC roles from the Keycloak-issued JWT.       │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Layer 3 — AUTHORIZATION (OPA Risk Scoring)         │
│  FastAPI sends transaction context to OPA.          │
│  OPA returns: Low / Medium / High risk score.       │
└─────────────────────────────────────────────────────┘
     │
     ├── Low/Medium ──────────────────────────────────┐
     │                                                 │
     ▼ High Risk                                       │
┌─────────────────────────────────────────────────────┐ │
│  Layer 4 — STEP-UP VERIFICATION (TOTP / MFA)        │ │
│  FastAPI issues a 401 Step-Up challenge.            │ │
│  User submits a 6-digit TOTP code to proceed.       │ │
└─────────────────────────────────────────────────────┘ │
     │                                                 │
     └──────────────────┬──────────────────────────────┘
                        ▼
           ┌──────────────────────────┐
           │  Layer 5 — TRANSACTION   │
           │  PostgreSQL executes the │
           │  ACID-safe DB transfer.  │
           └──────────────────────────┘
```

---

## 🛠️ Prerequisites

Ensure the following are installed and running on your system:

- **Python** 3.10+
- **Node.js** 18+ & npm
- **PostgreSQL**
- **Keycloak** — running locally on port `8080`
- **Open Policy Agent (OPA)** — running locally on port `8181`
- **Nginx**
- **OpenSSL** — for certificate generation

---

## ⚙️ Environment Variables

Create a `.env` file inside the `backend/` directory:

```env
# ── Database ──────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/banking_db

# ── Keycloak IAM ──────────────────────────────────────────────
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=banking
KEYCLOAK_CLIENT_ID=fastapi-backend
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# ── Open Policy Agent ─────────────────────────────────────────
OPA_URL=http://localhost:8181/v1/data/banking/allow
```

> ⚠️ Never commit `.env` or the `certs/` directory to version control. Add both to `.gitignore`.

---

## 🚀 Setup Instructions

### 1 — Database and Docker

Build and Run
Ensure Docker and Docker Compose are installed, then run:
```bash
docker compose up -d --build

# Create the database in PostgreSQL
createdb banking_db

# Initialize tables
python backend/init_db.py
```

---

### 2 — Keycloak (IAM)

1. Log into the Keycloak Admin Console at `http://localhost:8080/admin`.
2. Create a **Realm** named `banking`.
3. Create two **Clients** — one for the React frontend and one for the FastAPI backend.

   **Required settings for each client:**
   | Setting | Value |
   |---|---|
   | Valid Redirect URIs | `https://localhost/*` |
   | Web Origins | `https://localhost` (no trailing slash) |

4. Under **Realm Roles**, create two roles: `customer` and `manager`.
5. Edit the `default-roles-banking` composite role and assign `customer` to it so new users receive it automatically.

---

### 3 — Open Policy Agent (OPA)

```bash
cd opa
opa run --server ./policy.rego ./data.json
```

---

### 4 — Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn core.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### 5 — Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

> ℹ️ Vite runs on port `5173`, but **never access this port directly**. Nginx handles all routing — always use `https://localhost`.

---

## 🔒 Security Setup — mTLS via Nginx

To enforce Zero Trust device verification, you must act as your own Certificate Authority (CA).

### Step 1: Generate Certificates

Run the following from the **project root**:

```bash
mkdir certs && cd certs

# ── 1. Create the Certificate Authority (CA) ──────────────────
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
  -subj "/CN=ZeroTrustBankCA"

# ── 2. Create the Nginx Server Certificate ────────────────────
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/CN=localhost"
openssl x509 -req -days 365 -in server.csr \
  -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt

# ── 3. Create the Client Device Certificate (.p12) ────────────
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
  -subj "/CN=TrustedEmployeeDevice"
openssl x509 -req -days 365 -in client.csr \
  -CA ca.crt -CAkey ca.key -set_serial 02 -out client.crt
openssl pkcs12 -export -out client.p12 \
  -inkey client.key -in client.crt -certfile ca.crt
```

> 📝 Remember the export password you set for `client.p12` — you'll need it when importing into your browser.

---

### Step 2: Configure Nginx

Create `nginx.conf` in the project root. Replace `/absolute/path/to/` with your actual path (use `pwd` to find it):

```nginx
events {
    worker_connections 1024;
}

http {
    server {
        listen 443 ssl;
        server_name localhost;

        # ── Server Identity ─────────────────────────────────────
        ssl_certificate     /absolute/path/to/banking-zta/certs/server.crt;
        ssl_certificate_key /absolute/path/to/banking-zta/certs/server.key;

        # ── Demand mTLS Client Certificate ──────────────────────
        ssl_client_certificate /absolute/path/to/banking-zta/certs/ca.crt;
        ssl_verify_client optional;

        # ── Secure API Routes (FastAPI) ──────────────────────────
        location ~ ^/(transfer|security|admin|accounts) {
            if ($ssl_client_verify != SUCCESS) {
                return 403 "Zero Trust Violation: Valid Client Certificate Required\n";
            }
            proxy_pass http://localhost:8000;
            proxy_set_header Host               $host;
            proxy_set_header X-Real-IP          $remote_addr;
            proxy_set_header X-Forwarded-Proto  $scheme;
            proxy_set_header Authorization      $http_authorization;
        }

        # ── Frontend Route (React / Vite HMR) ───────────────────
        location / {
            proxy_pass http://localhost:5173;
            proxy_set_header Host       $host;
            proxy_set_header Upgrade    $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

---

### Step 3: Start Nginx

```bash
sudo nginx -c /absolute/path/to/banking-zta/nginx.conf
```

To reload config without downtime:

```bash
sudo nginx -s reload
```

---

## 🎬 Running the Demo

Follow these steps end-to-end to see all four Zero Trust layers in action:

**1. Install the Device Certificate**

Open Firefox → Settings → Privacy & Security → View Certificates → Import `client.p12`.
Set the browser to **"Ask every time"** for certificate selection.

**2. Access the Application**

Navigate to `https://localhost`.

**3. Pass the Network Gate**

Accept the self-signed certificate warning, then select **TrustedEmployeeDevice** when prompted. Nginx verifies the certificate and grants access.

**4. Set Up MFA**

Log in, go to **Security Settings**, and generate a TOTP QR code. Scan it with **Google Authenticator** or **Authy**.

**5. Trigger the Step-Up Challenge**

Attempt to transfer a high-value amount (e.g., `₹90,000`). OPA flags the transaction as high-risk, blocking it and rendering the MFA modal. Enter your 6-digit TOTP code to complete the transfer.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend / PEP | FastAPI (Python) |
| IAM | Keycloak |
| Policy Engine / PDP | Open Policy Agent (Rego) |
| Database | PostgreSQL (asyncpg) |
| API Gateway | Nginx |
| MFA | pyotp (TOTP) |
| Device Auth | mTLS / X.509 Certificates |

---

## 🛡️ Security Checklist

- [ ] `certs/` added to `.gitignore`
- [ ] `.env` added to `.gitignore`
- [ ] Keycloak admin credentials changed from defaults in production
- [ ] Client certificate export password stored securely
- [ ] OPA policy reviewed and locked to minimum required permissions
- [ ] Database user restricted to `banking_db` with least-privilege grants

---

## 📄 License

This project is for educational and demonstration purposes. Ensure compliance with your organization's security policies before deploying in any production environment.