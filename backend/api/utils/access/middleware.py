# permissions.py

from api.utils.access.ip import get_client_ip
from api.utils.access.network_policies import (
    denial_message,
    network_access_denied,
)
from rest_framework.permissions import BasePermission


class IsIPAllowed(BasePermission):
    """
    Enforces network access policies: callers with applicable policies are
    allowed only from a client IP covered by one of them. Accounts without
    policies are governed by RBAC alone.
    """

    message = "Access denied: a network access policy restricts access from your IP address."

    def get_client_ip(self, request):
        return get_client_ip(request)

    def has_permission(self, request, view):
        org_member = request.auth.get("org_member", None)
        service_account = request.auth.get("service_account", None)

        account = org_member or service_account
        org = account.organisation if account is not None else None

        if network_access_denied(org, account, self.get_client_ip(request)):
            self.message = denial_message()
            return False
        return True
