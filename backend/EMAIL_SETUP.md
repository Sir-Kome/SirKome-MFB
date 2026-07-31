Sending email notifications

The backend supports sending real email notifications via SMTP. By default, emails are only logged to the server console unless SMTP configuration is provided via environment variables.

Recommended local testing options

1) MailHog (Docker)

```powershell
docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
```
- SMTP: localhost:1025
- Web UI: http://localhost:8025/

2) smtp4dev (Windows)

Download and run smtp4dev and use the SMTP port it exposes (e.g. 25 or 1025). It also provides a web UI.

Environment variables

Set these before starting the backend (PowerShell example):

```powershell
$env:SIRKOME_SMTP_HOST = 'localhost'
$env:SIRKOME_SMTP_PORT = '1025'
$env:SIRKOME_SMTP_USER = 'no-reply@example.test'
$env:SIRKOME_SMTP_PASS = 'ignored'
$env:SIRKOME_FROM = 'no-reply@example.test'
```

For production, point `SIRKOME_SMTP_HOST`/`SIRKOME_SMTP_PORT`/`SIRKOME_SMTP_USER`/`SIRKOME_SMTP_PASS` to your SMTP provider (SendGrid, Mailgun SMTP, SES SMTP, or your corporate SMTP). Use TLS/STARTTLS on port 587.

Verify email sending

- Start MailHog/smtp4dev
- Start the backend (for example):

```powershell
uvicorn backend.main:app --reload
```

- Use the test endpoint to send an email (curl example):

```powershell
curl -X POST http://127.0.0.1:8000/debug/send-test-email -H "Content-Type: application/json" -d '{"email":"you@localhost.test","subject":"Test","body":"Hello"}'
```

If SMTP is configured correctly, you will see the message in MailHog/smtp4dev UI. If SMTP is not configured, the server will print the email payload to the console and return `sent: false` from the test endpoint.

Quick production setup (Gmail/Yahoo)

- Create `backend/.env` from one of the example files `.env.gmail.example` or `.env.yahoo.example` and fill in the secret `SIRKOME_SMTP_PASS` with the App Password or provider password. Example:

```
SIRKOME_SMTP_HOST=smtp.gmail.com
SIRKOME_SMTP_PORT=587
SIRKOME_SMTP_USER=your@gmail.com
SIRKOME_SMTP_PASS=YOUR_APP_PASSWORD_HERE
SIRKOME_FROM=your@gmail.com
```

- Restart the backend and trigger a real action (register/transfer/profile update). The recipient will receive a real email if credentials are correct and the provider allows sending from that account.

Security note: Do NOT commit `backend/.env` to version control. Use a secret manager for production deployments.
