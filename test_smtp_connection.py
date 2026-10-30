
import socket
import smtplib

SMTP_SERVER = "smtp.gmail.com"

for port in [465, 587]:
    try:
        print(f"\nTesting port {port}...")

        with socket.create_connection(
            (SMTP_SERVER, port),
            timeout=15
        ):
            print(f"TCP connection successful on port {port}")

        if port == 465:
            with smtplib.SMTP_SSL(
                SMTP_SERVER,
                port,
                timeout=15
            ) as server:
                print(server.ehlo())

        else:
            with smtplib.SMTP(
                SMTP_SERVER,
                port,
                timeout=15
            ) as server:
                print(server.ehlo())
                print(server.starttls())
                print(server.ehlo())

        print(f"SMTP test successful on port {port}")

    except Exception as e:
        print(f"Port {port} failed: {type(e).__name__}: {e}")
