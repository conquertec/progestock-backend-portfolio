#!/usr/bin/env python
"""
Quick script to verify you're ready to deploy to Railway.
Run this before deploying!

Usage:
    python check_railway_ready.py
"""

import os
import sys
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_tests():
    """Check if tests are passing."""
    print_header("1. Testing Status")
    print("Run: pytest -v")
    print("Expected: 18/18 tests passing")
    response = input("\n✅ Are all tests passing? (y/n): ")
    return response.lower() == 'y'


def check_docker():
    """Check if Docker setup exists."""
    print_header("2. Docker Configuration")

    project_root = Path(__file__).parent
    dockerfile = project_root / "Dockerfile"
    dockerignore = project_root / ".dockerignore"
    entrypoint = project_root / "entrypoint.sh"

    docker_ok = True

    if dockerfile.exists():
        print("✅ Dockerfile exists")
    else:
        print("❌ Dockerfile missing!")
        docker_ok = False

    if dockerignore.exists():
        print("✅ .dockerignore exists")
    else:
        print("⚠️  .dockerignore missing (optional but recommended)")

    if entrypoint.exists():
        print("✅ entrypoint.sh exists")
    else:
        print("❌ entrypoint.sh missing!")
        docker_ok = False

    return docker_ok


def check_credentials():
    """Check if user has necessary credentials."""
    print_header("3. Required Credentials")

    credentials = {
        "Google Cloud Storage bucket name": False,
        "GCS service account JSON": False,
        "SendGrid API key": False,
        "Google OAuth Client ID": False,
        "Google OAuth Client Secret": False,
    }

    print("\nDo you have these credentials ready?")
    all_ready = True

    for cred, _ in credentials.items():
        response = input(f"  {cred}? (y/n): ")
        credentials[cred] = response.lower() == 'y'
        if not credentials[cred]:
            all_ready = False

    if not all_ready:
        print("\n⚠️  Missing credentials. Get these before deploying:")
        for cred, has_it in credentials.items():
            if not has_it:
                print(f"   ❌ {cred}")

    return all_ready


def check_frontend():
    """Check if frontend is ready to be updated."""
    print_header("4. Frontend Integration")

    print("\nAfter Railway deployment, you'll need to:")
    print("  1. Update frontend .env with Railway URL")
    print("  2. Redeploy frontend")
    print("  3. Test end-to-end")

    response = input("\n✅ Are you prepared to update frontend? (y/n): ")
    return response.lower() == 'y'


def generate_secret_key():
    """Generate a new Django SECRET_KEY."""
    print_header("5. Generate SECRET_KEY")

    try:
        import secrets
        secret_key = secrets.token_urlsafe(50)
        print("\n🔑 New SECRET_KEY generated:")
        print(f"\n{secret_key}\n")
        print("⚠️  SAVE THIS! Add it to Railway environment variables.")
        print("   Never commit this to git!")
        return True
    except Exception as e:
        print(f"❌ Error generating secret key: {e}")
        return False


def show_checklist():
    """Show deployment checklist."""
    print_header("6. Deployment Checklist")

    print("""
📋 Before you deploy to Railway:

1. Create Railway project
   - Go to https://railway.app/
   - Click "New Project" → "Deploy from GitHub repo"

2. Add PostgreSQL database
   - In Railway project, click "New" → "Database" → "PostgreSQL"

3. Add environment variables
   - Open: RAILWAY_ENV_VARS.md
   - Copy variables to Railway dashboard
   - Replace placeholder values with real ones

4. Deploy!
   - Railway auto-deploys from GitHub
   - Or click "Deploy" button

5. After deployment:
   - Check logs for errors
   - Test: https://your-app.railway.app/health/
   - Update frontend API URL
   - Test end-to-end

6. Monitor
   - Watch Railway logs for 24 hours
   - Keep Render running as backup for 2-3 days
    """)


def main():
    """Main function."""
    print("\n" + "🚂 Railway Deployment Readiness Check" + "\n")

    checks = []

    # Run all checks
    tests_ok = check_tests()
    checks.append(("Tests", tests_ok))

    docker_ok = check_docker()
    checks.append(("Docker", docker_ok))

    creds_ok = check_credentials()
    checks.append(("Credentials", creds_ok))

    frontend_ok = check_frontend()
    checks.append(("Frontend Plan", frontend_ok))

    secret_ok = generate_secret_key()
    checks.append(("SECRET_KEY", secret_ok))

    # Show checklist
    show_checklist()

    # Final summary
    print_header("Summary")

    all_passed = all(status for _, status in checks)

    for name, status in checks:
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")

    if all_passed:
        print("\n" + "="*60)
        print("🎉 YOU'RE READY TO DEPLOY TO RAILWAY!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Open: RAILWAY_ENV_VARS.md")
        print("  2. Go to: https://railway.app/")
        print("  3. Create new project from GitHub")
        print("  4. Add PostgreSQL database")
        print("  5. Add environment variables")
        print("  6. Deploy!")
        print("\n🚀 Good luck!\n")
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("⚠️  NOT QUITE READY")
        print("="*60)
        print("\nPlease fix the issues above before deploying.")
        print("Then run this script again.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
