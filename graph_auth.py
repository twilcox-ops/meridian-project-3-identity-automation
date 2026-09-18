"""Certificate-based auth for Graph, with the certificate held in Key Vault.

Two different identities are involved, deliberately:

1. To read the certificate out of Key Vault, we use AzureCliCredential —
   i.e. whoever is running this tool authenticates as themselves via
   `az login`, and their own Azure AD identity must be granted a Key Vault
   access policy / RBAC role (e.g. "Key Vault Secrets User") to read
   `CERT_NAME`. This is the standard local-dev pattern: no secret or
   credential for the Graph app is ever stored on disk or in env vars.

2. To call Graph, we use CertificateCredential built from the bytes just
   pulled out of Key Vault — this is the app-only client-credentials flow
   the project requires (certificate, not a client secret).

In production this would swap step 1 for a managed identity with a Key
Vault access policy, with zero code changes here.

A Key Vault *certificate* is backed by a *secret* holding the full PKCS#12
(PFX) bundle (cert + private key), unencrypted by default. Fetching it via
SecretClient (not CertificateClient, which only exposes the public cert) is
the documented way to get material usable for client-certificate auth.
"""
import base64

from azure.identity import AzureCliCredential, CertificateCredential
from azure.keyvault.secrets import SecretClient

import config


def get_graph_credential() -> CertificateCredential:
    vault_name = config.require_env("GRAPH_KEY_VAULT_NAME")
    cert_name = config.require_env("GRAPH_CERT_NAME")
    tenant_id = config.require_env("GRAPH_TENANT_ID")
    client_id = config.require_env("GRAPH_CLIENT_ID")

    vault_url = f"https://{vault_name}.vault.azure.net"
    kv_credential = AzureCliCredential()
    secret_client = SecretClient(vault_url=vault_url, credential=kv_credential)

    secret = secret_client.get_secret(cert_name)
    pfx_bytes = base64.b64decode(secret.value)

    return CertificateCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        certificate_data=pfx_bytes,
    )
