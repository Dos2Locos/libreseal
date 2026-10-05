from allauth.account.signals import user_signed_up
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings
from backend.api.notifier import notify_slack
from api.models import DynamicSecret, DynamicSecretLease, RotatingSecret

CLOUD_HOSTED = settings.APP_HOST == "cloud"


@receiver(user_signed_up)
def notify_new_user_signup(request, user, **kwargs):
    """Notify Slack when a new user signs up. Uses allauth's user_signed_up signal
    which fires AFTER the user is committed to the database, avoiding duplicate
    notifications from failed/retried OAuth flows."""

    if CLOUD_HOSTED:
        try:
            social_account = user.socialaccount_set.first()
            full_name = (
                (social_account.extra_data.get("name") if social_account else None)
                or user.full_name
                or user.username
                or user.email
            )
            notify_slack(f"New user signup: {full_name} - {user.email}")
        except Exception as e:
            print(f"Error notifying Slack: {e}")


@receiver(pre_delete, sender=RotatingSecret)
def _rotating_secret_pre_delete(sender, instance, **kwargs):
    # Cascade hard-deletes from Environment/App/Folder bypass the soft-delete
    # RotatingSecret.delete(). Secret rotation is not available in LibreSeal,
    # so live provider credentials (only possible in a database migrated from
    # Phase) cannot be revoked: abort the cascade instead of orphaning them.
    if instance.has_live_credentials():
        from backend.edition import Feature, FeatureUnavailable

        raise FeatureUnavailable(Feature.SECRET_ROTATION)


@receiver(pre_delete, sender=DynamicSecret)
def _dynamic_secret_pre_delete(sender, instance, **kwargs):
    # Same as above for dynamic secrets: cascade hard-deletes bypass the
    # soft-delete DynamicSecret.delete(); active leases cannot be revoked.
    if instance.leases.filter(status=DynamicSecretLease.ACTIVE).exists():
        from backend.edition import Feature, FeatureUnavailable

        raise FeatureUnavailable(Feature.DYNAMIC_SECRETS)
