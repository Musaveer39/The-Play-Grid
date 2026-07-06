# backend/app/services/notification.py
import httpx
import sendgrid
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from app.core.config import settings

class NotificationService:
    def __init__(self):
        self.twilio_client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.sendgrid_client = sendgrid.SendGridAPIClient(
            settings.SENDGRID_API_KEY
        )
    
    async def send_whatsapp(self, to: str, message: str):
        """Send WhatsApp message using Twilio"""
        try:
            message = self.twilio_client.messages.create(
                body=message,
                from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}',
                to=f'whatsapp:{to}'
            )
            return {"success": True, "sid": message.sid}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_email(self, to: str, subject: str, content: str):
        """Send email using SendGrid"""
        try:
            message = Mail(
                from_email=settings.SENDGRID_FROM_EMAIL,
                to_emails=to,
                subject=subject,
                html_content=content
            )
            response = self.sendgrid_client.send(message)
            return {"success": response.status_code == 202}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_booking_confirmation(self, booking, user, turf):
        """Send booking confirmation via WhatsApp & Email"""
        message = f"""
        🏟️ Booking Confirmed - The Play Grid
        
        Booking ID: {booking['id'][:8]}
        Turf: {turf['name']}
        Date: {booking['booking_date']}
        Time: {booking['start_time']} - {booking['end_time']}
        Amount: ₹{booking['total_amount']}
        
        Thank you for booking with The Play Grid!
        """
        
        email_content = f"""
        <h2>Booking Confirmed!</h2>
        <p><strong>Booking ID:</strong> {booking['id'][:8]}</p>
        <p><strong>Turf:</strong> {turf['name']}</p>
        <p><strong>Date:</strong> {booking['booking_date']}</p>
        <p><strong>Time:</strong> {booking['start_time']} - {booking['end_time']}</p>
        <p><strong>Amount:</strong> ₹{booking['total_amount']}</p>
        <br>
        <p>Thank you for choosing The Play Grid!</p>
        """
        
        # Send WhatsApp
        if user.get('phone'):
            await self.send_whatsapp(user['phone'], message)
        
        # Send Email
        if user.get('email'):
            await self.send_email(
                user['email'],
                "Booking Confirmed - The Play Grid",
                email_content
            )