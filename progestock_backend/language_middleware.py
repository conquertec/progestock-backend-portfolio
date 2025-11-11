"""
Language detection middleware for ProGestock API.
Sets the language based on company settings or Accept-Language header.
"""
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class LanguageMiddleware(MiddlewareMixin):
    """
    Middleware to set the language for each request based on:
    1. User's company language setting (if authenticated)
    2. Accept-Language header (fallback)
    3. Default language (en)
    """

    def process_request(self, request):
        """
        Determine and activate the appropriate language for the request.
        """
        language = None

        # Try to get language from authenticated user's company settings
        if request.user and request.user.is_authenticated:
            try:
                # Check if user has a company and company has language setting
                if hasattr(request.user, 'company') and request.user.company:
                    company_language = getattr(request.user.company, 'language', None)
                    if company_language:
                        language = company_language
                        logger.debug(f"Using company language: {language} for user {request.user.email}")
            except Exception as e:
                logger.warning(f"Error getting company language for user {request.user.email}: {e}")

        # Fallback to Accept-Language header if no company language
        if not language:
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            if accept_language:
                # Parse Accept-Language header (e.g., "fr-FR,fr;q=0.9,en;q=0.8")
                # Extract the primary language code
                try:
                    lang_code = accept_language.split(',')[0].split('-')[0].strip()
                    # Validate against supported languages
                    supported_languages = ['en', 'fr']
                    if lang_code in supported_languages:
                        language = lang_code
                        logger.debug(f"Using Accept-Language header: {language}")
                except Exception as e:
                    logger.warning(f"Error parsing Accept-Language header: {e}")

        # Default to English if no language detected
        if not language:
            language = 'en'
            logger.debug("Using default language: en")

        # Activate the language for this request
        try:
            translation.activate(language)
            request.LANGUAGE_CODE = language
        except Exception as e:
            # If translation activation fails (e.g., missing locale files),
            # fall back to English and continue without crashing
            logger.error(f"Failed to activate language '{language}': {e}")
            try:
                translation.activate('en')
                request.LANGUAGE_CODE = 'en'
            except Exception as fallback_error:
                # If even English fails, just log and continue
                # The app will use untranslated strings
                logger.error(f"Failed to activate fallback language 'en': {fallback_error}")
                request.LANGUAGE_CODE = 'en'

    def process_response(self, request, response):
        """
        Deactivate the current language after the response is processed.
        """
        translation.deactivate()
        return response
