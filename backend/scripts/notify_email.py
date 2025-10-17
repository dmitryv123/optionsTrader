#!/usr/bin/env python3
import os, smtplib, sys, traceback
from email.message import EmailMessage
from datetime import datetime

# --- EDIT THESE ---
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "user@example.com")
SMTP_PASS = os.getenv("SMTP_PASS", "REPLACE_ME")
TO_EMAIL  = os.getenv("TO_EMAIL",  "you@example.com")
FROM_EMAIL= os.getenv("FROM_EMAIL", SMTP_USER)

def send(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

if __name__ == "__main__":
    # usage: notify_email.py "subject" "body"
    try:
        subject = sys.argv[1]
        body = sys.argv[2] if len(sys.argv) > 2 else ""
        send(subject, body)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

