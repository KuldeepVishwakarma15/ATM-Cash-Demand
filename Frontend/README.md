# CashCast frontend

React + Vite: landing page, sign-in popup and the dashboard. Everything on the dashboard comes from the FastAPI backend (sign-in uses `POST /auth/login`, the JWT is kept in `sessionStorage` and sent as a Bearer token; a 401 on an authenticated call signs the user out).

```bash
npm ci
npm run dev        # http://127.0.0.1:5173, proxies the API on http://127.0.0.1:8000
npm run lint
npm run build
npm run test:e2e   # drives the real UI against a running API (skipped if the API is down)
```
