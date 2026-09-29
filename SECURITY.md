# Security notes

DineIQ is an analytical competition project with synthetic data. Local demo credentials are intentionally documented for reproducibility and must be replaced for any public deployment.

Implemented controls include password hashing, signed sessions, HttpOnly/SameSite cookies, CSRF checks on state changes, role gates, parameterized SQLite, strict upload size/path checks, formula-neutralized CSV export, and security headers. The application does not claim an independent penetration test, production multi-tenant isolation, durable distributed jobs, or 99% hosted uptime.

For a public deployment use HTTPS, a strong `DINEIQ_SECRET_KEY`, replacement user credentials, durable persistent storage, a production WSGI server, monitoring, a durable job queue, and least-privilege infrastructure permissions.
