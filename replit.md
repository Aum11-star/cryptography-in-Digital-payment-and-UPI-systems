# Workspace

## Overview

pnpm workspace monorepo using TypeScript, with an additional Python/Streamlit application.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.

---

## SimPay — Secure Digital Payment Network Simulator

A Streamlit-based academic demonstration of hybrid cryptography in a UPI-style payment network.

### Location

`simpay/` — Python/Streamlit app (served on port 5000)

### Architecture

```
simpay/
├── app.py                   # Home page / entry point
├── crypto_utils.py          # Hybrid crypto engine (RSA + AES-256)
├── database.py              # SQLite ledger + user store
├── bank_server.py           # Simulated payment gateway
├── requirements.txt         # Python dependencies
├── .streamlit/config.toml   # Streamlit server config
├── data/                    # SQLite DB + bank RSA keys (auto-created)
└── pages/
    ├── 1_Login_Register.py  # User auth (SHA-256 password hash, RSA key gen)
    ├── 2_Send_Payment.py    # Payment with live encryption demo
    ├── 3_My_Account.py      # User dashboard + transaction history
    └── 4_Admin_Dashboard.py # Admin analytics (pandas + matplotlib)
```

### Crypto Stack

- **SHA-256**: Password and PIN hashing (hashlib)
- **RSA-2048 OAEP**: Asymmetric key exchange (cryptography library)
- **AES-256-CBC**: Symmetric payload encryption (cryptography library)
- **Hybrid flow**: AES session key encrypted with RSA; payload encrypted with AES

### Run Command

```bash
cd simpay && streamlit run app.py --server.port 5000
```

### Admin Credentials (demo)

- Username: `admin`
- Password: `admin123`
