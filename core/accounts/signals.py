from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.dispatch import receiver

from .adapters import _ensure_profile


@receiver(social_account_added)
def on_social_account_added(sender, request, sociallogin, **kwargs):
    _ensure_profile(sociallogin.user)


@receiver(social_account_updated)
def on_social_account_updated(sender, request, sociallogin, **kwargs):
    _ensure_profile(sociallogin.user)
