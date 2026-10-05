"""Break-glass command: libreseal_clear_network_policies."""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

MODULE = "api.management.commands.libreseal_clear_network_policies"
ORG_A = "11111111-1111-1111-1111-111111111111"
ORG_B = "22222222-2222-2222-2222-222222222222"


def _org(org_id, name):
    org = MagicMock(id=org_id)
    org.name = name
    return org


def _policy(pid, org, name="office", is_global=False):
    policy = MagicMock(id=pid, organisation=org, is_global=is_global)
    policy.name = name
    return policy


@pytest.fixture
def models():
    with patch(f"{MODULE}.NetworkAccessPolicy") as Policy, patch(
        f"{MODULE}.Organisation"
    ) as Org, patch(f"{MODULE}.log_audit_event") as audit:
        qs = Policy.objects.select_related.return_value
        yield Policy, Org, audit, qs


def _run(*args):
    out = StringIO()
    call_command("libreseal_clear_network_policies", *args, stdout=out)
    return out.getvalue()


def test_lists_without_deleting(models):
    _, _, audit, qs = models
    policy = _policy("p1", _org(ORG_A, "homelab"), is_global=True)
    qs.__iter__.return_value = iter([policy])

    out = _run()

    assert "p1" in out and ORG_A in out and "(global)" in out
    assert "--yes" in out
    policy.delete.assert_not_called()
    audit.assert_not_called()


def test_yes_deletes_and_audits_each_policy(models):
    _, _, audit, qs = models
    org = _org(ORG_A, "homelab")
    policies = [_policy("p1", org, "office"), _policy("p2", org, "vpn")]
    qs.__iter__.return_value = iter(policies)

    out = _run("--yes")

    assert "Deleted 2 policies." in out
    for policy in policies:
        policy.delete.assert_called_once()
    assert audit.call_count == 2
    kwargs = audit.call_args_list[0].kwargs
    assert kwargs["organisation"] is org
    assert kwargs["event_type"] == "D"
    assert kwargs["resource_type"] == "policy"
    assert kwargs["resource_id"] == "p1"
    assert kwargs["actor_type"] == "user" and kwargs["actor_id"] == ""
    assert kwargs["actor_metadata"]["source"] == "management_command"
    assert "Server administrator" in kwargs["actor_metadata"]["username"]
    assert kwargs["resource_metadata"] == {"name": "office"}


def test_organisation_by_id(models):
    _, Org, _, qs = models
    org = _org(ORG_A, "homelab")
    Org.objects.filter.return_value.first.return_value = org
    qs.filter.return_value.__iter__.return_value = iter([])

    _run("--organisation", ORG_A)

    Org.objects.filter.assert_called_once_with(id=ORG_A)
    qs.filter.assert_called_once_with(organisation=org)


def test_organisation_by_name(models):
    _, Org, _, qs = models
    org = _org(ORG_A, "homelab")
    Org.objects.filter.return_value.first.return_value = org
    qs.filter.return_value.__iter__.return_value = iter([])

    _run("--organisation", "homelab")

    Org.objects.filter.assert_called_once_with(name="homelab")
    qs.filter.assert_called_once_with(organisation=org)


def test_unknown_organisation_is_refused(models):
    _, Org, _, _ = models
    Org.objects.filter.return_value.first.return_value = None

    with pytest.raises(CommandError, match="No organisation"):
        _run("--organisation", "nope", "--yes")
