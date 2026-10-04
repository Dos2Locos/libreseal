# permissions.py

from api.utils.access.network_policies import (
    UNENFORCEABLE_MESSAGE,
    network_access_denied,
)
from rest_framework.permissions import BasePermission


class IsIPAllowed(BasePermission):
    """
    Denies access when network access policies apply to the caller, since
    LibreSeal cannot enforce them (fail closed). Accounts without policies
    are governed by RBAC alone.
    """

    message = UNENFORCEABLE_MESSAGE

    def has_permission(self, request, view):
        org_member = request.auth.get("org_member", None)
        service_account = request.auth.get("service_account", None)

        account = org_member or service_account
        org = account.organisation if account is not None else None

        return not network_access_denied(org, account)
