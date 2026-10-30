
import os
import smtplib
import ssl
from dotenv import load_dotenv

load_dotenv(override=True)

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")
SERVER = "smtp.gmail.com"
PORT = 587

if not EMAIL or not PASSWORD:
    print("Email credentials are missing.")
    raise SystemExit

try:
    print("Connecting to Gmail...")

    with smtplib.SMTP(SERVER, PORT, timeout=30) as server:

        print("SMTP connection established.")

        server.ehlo()
        print("EHLO successful.")

        server.starttls(context=ssl.create_default_context())
        print("STARTTLS successful.")

        server.ehlo()

        print("Trying Gmail authentication...")

        server.login(EMAIL, PASSWORD)

        print("Gmail authentication successful!")

        msg = "Subject: SMTP Test\n\nTest email from Smart Text Summarizer."

        server.sendmail(EMAIL, EMAIL, msg)

        print("Test email sent successfully!")

except Exception as e:
    print("Error type:", type(e).__name__)
    print("Error details:", str(e))
