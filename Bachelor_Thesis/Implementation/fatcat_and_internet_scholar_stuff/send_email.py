from email.mime.text import MIMEText
import ssl
import smtplib
import os

def send_email(email_receiver: str):
    email_sender = "authorsfromkeyword@gmail.com"
    email_password = os.environ.get("THESIS_EMAIL_PASSWORD")
    email_receiver = "ulascanzorer@gmail.com"

    subject = "Finished finding authors!"
    body = """
    Thank you for your patience! Finding relevant authors is now complete.
    Please check the results at <a href="https://www.google.com/">click here</a>
    """

    em = MIMEText(body, "html")
    em["From"] = email_sender
    em["To"] = email_receiver
    em["Subject"] = subject
    context = ssl.create_default_context()


    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receiver, em.as_string())