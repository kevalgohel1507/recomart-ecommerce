from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import Group

from .models import UserProfile


class CustomAccountAdapter(DefaultAccountAdapter):
    """Standard allauth adapter — no changes needed here."""
    pass


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    After a social login (Google / Facebook) completes, ensure a UserProfile
    row exists for the user with role='customer'.
    """

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        _ensure_profile(user)
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Called when the OAuth callback returns.  If the social account is
        already connected to an existing Django user, make sure that user
        still has a profile (handles the case where the profile was deleted).
        """
        super().pre_social_login(request, sociallogin)
        if sociallogin.is_existing:
            _ensure_profile(sociallogin.user)


def _ensure_profile(user):
    """
    Create a UserProfile (customer) and add to the 'customer' group
    if one doesn't already exist for this user.
    """
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': 'customer',
            'email_verified': True,
        }
    )
    if created:
        group, _ = Group.objects.get_or_create(name='customer')
        user.groups.add(group)
    return profile
