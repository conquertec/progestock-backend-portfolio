from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

google_app = SocialApp.objects.get(provider='google')
print(f"Provider: {google_app.provider}")
print(f"Name: {google_app.name}")
print(f"Client ID: {google_app.client_id}")
print(f"Secret: {google_app.secret[:10]}...")
print(f"Sites: {list(google_app.sites.all())}")

# Ensure it's linked to your site
current_site = Site.objects.get_current()
if current_site not in google_app.sites.all():
    google_app.sites.add(current_site)
    print(f"Added site: {current_site}")