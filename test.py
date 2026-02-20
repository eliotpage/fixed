import smtplib
from email.message import EmailMessage

gmail_user = "noreply.popmap@gmail.com"
gmail_password = "dkhagcgakixxflxl"  # Use an App Password

msg = EmailMessage()
msg.set_content("Hello from Python SMS gateway!")

# Example: US AT&T number
msg["To"] = "447598328056@o2.co.uk"
msg["From"] = gmail_user
msg["Subject"] = ""

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(gmail_user, gmail_password)
    smtp.send_message(msg)

print("Sent!")
