import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import render_template_string
import logging

class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.email = os.environ.get('EMAIL_USER')
        self.password = os.environ.get('EMAIL_PASSWORD')
        self.enabled = bool(self.email and self.password)
        
        if not self.enabled:
            logging.warning("Email service disabled - EMAIL_USER and EMAIL_PASSWORD not configured")
    
    def send_status_notification(self, acquisition, new_status, user_email, user_name):
        """Send notification when acquisition status changes"""
        if not self.enabled:
            return False
            
        try:
            subject = f"[SENAI] Atualização na solicitação #{acquisition.id}"
            
            # Email template
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: #1e4a6b; color: white; padding: 20px; text-align: center;">
                        <h1>SENAI Morvan Figueiredo</h1>
                        <h2>Sistema de Acompanhamento de Aquisições</h2>
                    </div>
                    
                    <div style="padding: 20px; background: #f9f9f9; border-left: 4px solid #1e4a6b;">
                        <h3>Olá, {{ user_name }}!</h3>
                        <p>A solicitação <strong>#{{ acquisition.id }}</strong> teve seu status atualizado.</p>
                        
                        <div style="margin: 20px 0; padding: 15px; background: white; border-radius: 5px;">
                            <h4>Detalhes da Solicitação:</h4>
                            <p><strong>Título:</strong> {{ acquisition.title }}</p>
                            <p><strong>Tipo:</strong> {{ acquisition.type_display }}</p>
                            <p><strong>Status Atual:</strong> <span style="color: #1e4a6b; font-weight: bold;">{{ acquisition.status_display }}</span></p>
                            <p><strong>Solicitante:</strong> {{ acquisition.requester.full_name }}</p>
                            <p><strong>Data da Solicitação:</strong> {{ acquisition.created_at.strftime('%d/%m/%Y %H:%M') }}</p>
                        </div>
                        
                        <p>Para mais detalhes, acesse o sistema de acompanhamento.</p>
                    </div>
                    
                    <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                        <p>Este é um e-mail automático do Sistema de Acompanhamento de Aquisições - SENAI Morvan Figueiredo</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(template, 
                                                acquisition=acquisition, 
                                                user_name=user_name, 
                                                new_status=new_status)
            
            return self._send_email(user_email, subject, html_content)
            
        except Exception as e:
            logging.error(f"Error sending status notification: {e}")
            return False
    
    def send_approval_request(self, acquisition, approver_email, approver_name):
        """Send notification to approver when acquisition needs approval"""
        if not self.enabled:
            return False
            
        try:
            subject = f"[SENAI] Solicitação aguardando aprovação #{acquisition.id}"
            
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: #d32f2f; color: white; padding: 20px; text-align: center;">
                        <h1>SENAI Morvan Figueiredo</h1>
                        <h2>Solicitação Aguardando Aprovação</h2>
                    </div>
                    
                    <div style="padding: 20px; background: #fff3e0; border-left: 4px solid #d32f2f;">
                        <h3>Olá, {{ approver_name }}!</h3>
                        <p>Uma nova solicitação está aguardando sua aprovação.</p>
                        
                        <div style="margin: 20px 0; padding: 15px; background: white; border-radius: 5px;">
                            <h4>Detalhes da Solicitação:</h4>
                            <p><strong>Título:</strong> {{ acquisition.title }}</p>
                            <p><strong>Tipo:</strong> {{ acquisition.type_display }}</p>
                            <p><strong>Valor Estimado:</strong> R$ {{ "%.2f"|format(acquisition.estimated_value) if acquisition.estimated_value else "Não informado" }}</p>
                            <p><strong>Solicitante:</strong> {{ acquisition.requester.full_name }}</p>
                            <p><strong>Justificativa:</strong> {{ acquisition.justification[:200] }}{{ "..." if acquisition.justification|length > 200 else "" }}</p>
                        </div>
                        
                        <p style="color: #d32f2f; font-weight: bold;">Acesse o sistema para revisar e aprovar a solicitação.</p>
                    </div>
                    
                    <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                        <p>Este é um e-mail automático do Sistema de Acompanhamento de Aquisições - SENAI Morvan Figueiredo</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(template, 
                                                acquisition=acquisition, 
                                                approver_name=approver_name)
            
            return self._send_email(approver_email, subject, html_content)
            
        except Exception as e:
            logging.error(f"Error sending approval request: {e}")
            return False
    
    def _send_email(self, to_email, subject, html_content):
        """Send email with HTML content"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email or '', self.password or '')
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email to {to_email}: {e}")
            return False

# Global instance
email_service = EmailService()
