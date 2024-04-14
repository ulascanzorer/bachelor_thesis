from email.mime.text import MIMEText
import ssl
import smtplib
import os

# A function which sends an email to an email address, using a sender email address and a password saved as an environment variables.

def send_email(email_receiver, email_content):
    # email_sender = "talentsearchtool@gmail.com"
    email_sender = os.environ.get("EMAIL_SENDER_ADDRESS")
    email_password = os.environ.get("EMAIL_SENDER_PASSWORD")

    subject = "Your results are ready!"
    body = email_content

    em = MIMEText(body, "html")
    em["From"] = email_sender
    em["To"] = email_receiver
    em["Subject"] = subject
    context = ssl.create_default_context()


    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receiver, em.as_string())