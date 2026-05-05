import smtplib
import ssl
from email.message import EmailMessage
import streamlit as st

def send_email_with_attachment(destinatario, subject, body, attachment_data, filename):
    """
    Envía un correo electrónico con un archivo adjunto utilizando las credenciales de st.secrets["email"].
    """
    try:
        # 1. Obtener credenciales de secrets.toml
        if "email" not in st.secrets:
            return False, "No se encontró la configuración [email] en st.secrets"
            
        email_cfg = st.secrets["email"]
        remitente = email_cfg["sender"]
        password = email_cfg["password"]
        servidor_smtp = email_cfg["smtp_server"]
        puerto_smtp = int(email_cfg["smtp_port"])
        
        # 2. Crear el mensaje
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = remitente
        msg['To'] = destinatario
        msg.set_content(body)
        
        # 3. Adjuntar el archivo
        # Determinamos el maintype y subtype simplificado para archivos generales
        msg.add_attachment(
            attachment_data, 
            maintype='application', 
            subtype='octet-stream', 
            filename=filename
        )
        
        # 4. Conexión y envío
        context = ssl.create_default_context()
        with smtplib.SMTP(servidor_smtp, puerto_smtp) as server:
            server.starttls(context=context)
            server.login(remitente, password)
            server.send_message(msg)
            
        return True, "Correo enviado exitosamente."
        
    except Exception as e:
        return False, f"Error al enviar correo: {str(e)}"
