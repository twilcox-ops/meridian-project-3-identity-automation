"""Non-secret runtime config, read from environment variables.

No credentials live here or anywhere else in code — the certificate stays in
Key Vault (see graph_auth.py). Tenant/client/vault/cert *names* are not
secrets, but they're kept out of source anyway so this repo is safe to share
and the same code works against a different tenant by changing env vars only.

A .env file in the working directory (see .env.example) is loaded
automatically if present; real shell env vars still take precedence and
override it.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. See README.md setup."
        )
    return value
