"""
Simple script to upload email logo to Google Cloud Storage
Run this once to upload the logo to your GCS bucket
"""
import os

def upload_logo():
    """Upload email logo to GCS bucket"""

    try:
        from google.cloud import storage
        from google.oauth2 import service_account

        # Read credentials from JSON file
        creds_file = r'C:\Users\Dell\Documents\progestock-85af5aa3be15.json'

        if not os.path.exists(creds_file):
            print(f"[ERROR] Credentials file not found: {creds_file}")
            return

        print(f"Loading credentials from: {creds_file}")
        credentials = service_account.Credentials.from_service_account_file(creds_file)

        # Initialize GCS client
        client = storage.Client(
            project='progestock',
            credentials=credentials
        )

        bucket_name = 'progestock_bucket'
        bucket = client.bucket(bucket_name)

        # Upload logo
        logo_path = 'progestock_backend/email_logo.png'
        if not os.path.exists(logo_path):
            print(f"[ERROR] Logo file not found at {logo_path}")
            return

        print(f"Uploading logo from {logo_path}...")
        blob = bucket.blob('email_logo.png')
        blob.upload_from_filename(logo_path, content_type='image/png')

        # Make it publicly accessible
        blob.make_public()

        public_url = blob.public_url
        print(f"\n[SUCCESS] Logo uploaded successfully!")
        print(f"Public URL: {public_url}")
        print(f"\nAdd this to your Railway environment variables:")
        print(f"   EMAIL_LOGO_URL={public_url}")

    except Exception as e:
        print(f"[ERROR] Error uploading logo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    upload_logo()
