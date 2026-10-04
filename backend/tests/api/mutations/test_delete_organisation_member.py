"""DeleteOrganisationMemberMutation in LibreSeal.

SCIM provisioning is not available in LibreSeal, so members that were
SCIM-provisioned in a database migrated from Phase are removed through the
regular soft-delete path. Ownership and RBAC guards still apply.
"""

from unittest.mock import MagicMock, patch

import pytest


def _info(user):
    info = MagicMock()
    info.context.user = user
    return info


@patch("backend.graphene.mutations.organisation.OrganisationMember")
@patch("backend.graphene.mutations.organisation.user_has_permission", return_value=True)
def test_non_scim_member_soft_deletes_om(_mock_perm, MockOM):
    from backend.graphene.mutations.organisation import DeleteOrganisationMemberMutation

    target = MagicMock()
    target.user = MagicMock()
    target.scimuser_set.all.return_value = []
    MockOM.objects.get.return_value = target

    DeleteOrganisationMemberMutation.mutate(None, _info(MagicMock()), member_id="m1")

    target.delete.assert_called_once()


@patch("backend.graphene.mutations.organisation.OrganisationMember")
@patch("backend.graphene.mutations.organisation.user_has_permission", return_value=True)
def test_legacy_scim_member_is_removed_like_any_other(_mock_perm, MockOM):
    from backend.graphene.mutations.organisation import DeleteOrganisationMemberMutation

    scim_user = MagicMock()
    target = MagicMock()
    target.user = MagicMock()
    target.scimuser_set.all.return_value = [scim_user]
    MockOM.objects.get.return_value = target

    DeleteOrganisationMemberMutation.mutate(None, _info(MagicMock()), member_id="m1")

    target.delete.assert_called_once()


@patch("backend.graphene.mutations.organisation.OrganisationMember")
@patch("backend.graphene.mutations.organisation.user_has_permission", return_value=True)
def test_caller_cannot_remove_themselves(_mock_perm, MockOM):
    from backend.graphene.mutations.organisation import DeleteOrganisationMemberMutation
    from graphql import GraphQLError

    caller = MagicMock()
    target = MagicMock()
    target.user = caller
    MockOM.objects.get.return_value = target

    with pytest.raises(GraphQLError, match="can't remove yourself"):
        DeleteOrganisationMemberMutation.mutate(None, _info(caller), member_id="m1")

    target.delete.assert_not_called()


@patch("backend.graphene.mutations.organisation.OrganisationMember")
@patch("backend.graphene.mutations.organisation.user_has_permission", return_value=True)
def test_managed_owner_cannot_be_removed(_mock_perm, MockOM):
    """Even a global caller must use ownership transfer, not member deletion."""
    from backend.graphene.mutations.organisation import DeleteOrganisationMemberMutation
    from graphql import GraphQLError

    owner_role = MagicMock(is_default=True, managed_key="owner")
    owner_role.name = "Renamed owner role"
    target = MagicMock(role=owner_role)
    target.user = MagicMock()
    MockOM.objects.get.return_value = target

    with pytest.raises(GraphQLError, match="ownership transfer"):
        DeleteOrganisationMemberMutation.mutate(
            None, _info(MagicMock()), member_id="owner"
        )

    target.delete.assert_not_called()


@patch("backend.graphene.mutations.organisation.OrganisationMember")
@patch("backend.graphene.mutations.organisation.user_has_permission", return_value=False)
def test_rbac_check_blocks_unauthorized_caller(_mock_perm, MockOM):
    from backend.graphene.mutations.organisation import DeleteOrganisationMemberMutation
    from graphql import GraphQLError

    target = MagicMock()
    target.user = MagicMock()
    MockOM.objects.get.return_value = target

    with pytest.raises(GraphQLError, match="permission"):
        DeleteOrganisationMemberMutation.mutate(None, _info(MagicMock()), member_id="m1")

    target.delete.assert_not_called()
