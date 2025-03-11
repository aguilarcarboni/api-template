from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from jinja2 import Environment, FileSystemLoader
from premailer import transform

from laserfocus.utils.logger import logger
from laserfocus.utils.exception import handle_exception
from src.utils.secret_manager import get_secret

import os
import base64

class Gmail:

  def __init__(self):
    logger.announcement('Initializing Gmail connection.', type='info')
    SCOPES = ["https://mail.google.com/"]
    creds = get_secret('OAUTH_PYTHON_CREDENTIALS_INFO')
    try:
      creds = Credentials(
        token=creds['token'],
        refresh_token=creds['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds['client_id'],
        client_secret=creds['client_secret'],
        scopes=SCOPES
      )
      self.service = build("gmail", "v1", credentials=creds)
      logger.announcement('Initialized Gmail connection.', type='success')
    except Exception as e:
      logger.error(f"Error initializing Gmail: {str(e)}")
      raise Exception(f"Error initializing Gmail: {str(e)}")

  @handle_exception
  def create_html_email(self, content, subject, client_email, email_template):
    """
    Create an HTML email that can handle both plain text and dictionary content.
    
    Args:
        content: Can be either a string (plain text) or a dictionary (structured data)
        subject: Email subject
        client_email: Recipient email address
        email_template: Name of the template file to use
    """
    logger.info(f'Creating {email_template} email with subject: {subject}')

    # Get the template html file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env = Environment(loader=FileSystemLoader(os.path.join(current_dir, '../lib/email_templates')))
    template = env.get_template(f'{email_template}.html')

    # Prepare the content based on its type
    template_data = {
        'subject': subject,
        'content': content
    }

    # Render the template with the content
    html_content = template.render(**template_data)

    # Inline the CSS
    html_content_inlined = transform(html_content)

    # Create a multipart message
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = "info@agmtechnology.com"

    # Convert dictionary to readable plain text format
    if isinstance(content, dict):
        text_content = "\n".join(f"{key}: {value}" for key, value in content.items())
    else:
        text_content = str(content)

    # Attach plain text and HTML versions
    text_part = MIMEText(text_content.encode('utf-8'), 'plain', 'utf-8')
    html_part = MIMEText(html_content_inlined.encode('utf-8'), 'html', 'utf-8')
    
    message.attach(text_part)
    message.attach(html_part)

    # Create the final multipart message
    final_message = MIMEMultipart('related')
    final_message['Subject'] = subject
    final_message['To'] = client_email
    final_message['From'] = "info@agmtechnology.com"
    final_message['Bcc'] = "cr@agmtechnology.com,aa@agmtechnology.com,jc@agmtechnology.com,hc@agmtechnology.com,rc@agmtechnology.com"

    final_message.attach(message)

    # Attach the logo image
    logo_path = 'public/assets/brand/agm-logo.png'
    with open(logo_path, 'rb') as logo_file:
        logo_mime = MIMEImage(logo_file.read())
        logo_mime.add_header('Content-ID', '<logo>')
        final_message.attach(logo_mime)

    logger.success(f'Successfully created {email_template} email with subject: {subject}')
    raw_message = base64.urlsafe_b64encode(final_message.as_bytes()).decode()
    return {'raw': raw_message}

  @handle_exception
  def send_email(self, content, client_email, subject, email_template):
    """
    Send an email using either plain text or dictionary content.
    
    Args:
        content: Can be either a string (plain text) or a dictionary (structured data)
        client_email: Recipient email address
        subject: Email subject
        email_template: Name of the template file to use
    """
    logger.announcement(f'Sending {email_template} email to: {client_email}', type='info')
    raw_message = self.create_html_email(content, subject, client_email, email_template)

    send_message = (
        self.service.users()
        .messages()
        .send(userId="me", body=raw_message)
        .execute()
    )
    logger.announcement(f'Successfully sent {email_template} email to: {client_email}', type='success')
    return {'emailId': send_message["id"]}