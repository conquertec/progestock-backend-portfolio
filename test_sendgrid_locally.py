#!/usr/bin/env python
"""
Quick SendGrid Test Script
Run this locally to verify your SendGrid API key works
"""

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def test_sendgrid():
    """Test SendGrid API key and send a test email"""

    print("=" * 50)
    print("SendGrid Test Script")
    print("=" * 50)

    # Get API key from environment or prompt
    api_key = os.environ.get('SENDGRID_API_KEY')

    if not api_key:
        print("\n⚠️  SENDGRID_API_KEY not found in environment variables")
        api_key = input("\nPaste your SendGrid API key (starts with SG.): ").strip()

    if not api_key:
        print("❌ No API key provided. Exiting.")
        return

    if not api_key.startswith('SG.'):
        print("⚠️  Warning: API key doesn't start with 'SG.' - are you sure it's correct?")

    print(f"\n✓ API key found: {api_key[:10]}...")

    # Get test email
    to_email = input("\nEnter YOUR email to receive test email: ").strip()

    if not to_email or '@' not in to_email:
        print("❌ Invalid email address. Exiting.")
        return

    # Create test email
    print("\n📧 Creating test email...")
    message = Mail(
        from_email='no-reply@progestock.com',
        to_emails=to_email,
        subject='SendGrid Test - ProGestock',
        html_content='<strong>Success! Your SendGrid is working correctly.</strong><br><br>This is a test email from ProGestock backend.'
    )

    # Send email
    try:
        print("📤 Sending test email via SendGrid...")
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)

        print("\n" + "=" * 50)
        print("✅ EMAIL SENT SUCCESSFULLY!")
        print("=" * 50)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.body}")
        print(f"Response Headers: {response.headers}")
        print("\n📬 Check your email inbox (and spam folder) for the test email!")
        print("\nIf you received the email, your SendGrid is configured correctly!")
        print("Next step: Add this API key to Railway as SENDGRID_API_KEY variable")

    except Exception as e:
        print("\n" + "=" * 50)
        print("❌ ERROR SENDING EMAIL")
        print("=" * 50)
        print(f"Error: {str(e)}")
        print("\nCommon issues:")
        print("1. Invalid API key - check it's correct")
        print("2. API key doesn't have 'Mail Send' permission")
        print("3. Sender email 'no-reply@progestock.com' not verified in SendGrid")
        print("   → Go to: https://app.sendgrid.com/settings/sender_auth/senders")
        print("   → Verify your sender email")
        print("\n4. SendGrid account suspended (check SendGrid dashboard)")

if __name__ == "__main__":
    test_sendgrid()
