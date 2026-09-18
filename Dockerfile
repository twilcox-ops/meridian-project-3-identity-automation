FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py graph_auth.py graph_client.py mailer.py build_report.py ./
COPY audit_mfa.py audit_stale_licensed.py audit_guests.py audit_privileged_roles.py audit_sp_creds.py audit_ownerless_groups.py audit_devices.py ./

CMD ["python", "build_report.py", "--output", "report.html"]
