# company/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound  # ✅ Add this import
from .serializers import CompanySerializer, UpdateCompanySerializer
from .models import Company
from auditing.models import LogEntry

import os

# --- Onboarding View (No Changes) ---
class CompanyOnboardingView(generics.CreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        company = serializer.save()
        user = self.request.user
        user.company = company
        user.save()
        LogEntry.objects.create(
            user=user, 
            company=company, 
            action_type='COMPANY_CREATED', 
            details={'company_name': company.name}
        )

class CompleteOnboardingView(APIView):
    """
    An endpoint to mark the company's onboarding wizard as complete.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = request.user.company
        if company:
            company.onboarding_complete = True
            company.save()
            return Response({"status": "Onboarding marked as complete."}, status=status.HTTP_200_OK)
        
        return Response({"error": "No company associated with this user."}, status=status.HTTP_400_BAD_REQUEST)

# --- New AI Profile Generation View ---
class GenerateProfileView(APIView):
    """
    An endpoint to generate a business profile using the Gemini AI.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        company = user.company

        if not company:
            return Response({"error": "No company associated with this user."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                mock_profile = f"{company.name} is a leading company in the {company.industry} sector. It is known for its innovative solutions and commitment to customer satisfaction, driving excellence and setting new standards in the market."
                company.business_profile = mock_profile
                company.save()
                return Response({'business_profile': mock_profile}, status=status.HTTP_200_OK)

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"Generate a professional, concise, and engaging one-paragraph business profile for a company. The company name is '{company.name}' and it operates in the '{company.industry}' industry. Focus on a positive and forward-looking tone."
            
            response = model.generate_content(prompt)
            generated_profile = response.text

            company.business_profile = generated_profile
            company.save()

            return Response({'business_profile': generated_profile}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Failed to generate profile: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================
# SETTINGS VIEWS
# ===========================

class CompanySettingsView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update company settings.
    Only the company owner can update these settings.
    """
    serializer_class = UpdateCompanySerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the company associated with the current user."""
        company = self.request.user.company
        if not company:
            # ✅ Fixed: Raise NotFound exception instead of trying to raise Response
            raise NotFound(detail="No company associated with this user.")
        return company

    def perform_update(self, serializer):
        """Log company updates."""
        company = serializer.save()
        LogEntry.objects.create(
            user=self.request.user,
            company=company,
            action_type='COMPANY_UPDATED',
            details={'updated_fields': list(serializer.validated_data.keys())}
        )