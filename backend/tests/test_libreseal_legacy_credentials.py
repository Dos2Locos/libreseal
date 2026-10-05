"""Fail-closed handling of dynamic and rotating secrets migrated from Phase.

LibreSeal cannot serve dynamic secrets nor revoke live provider credentials,
so it refuses to drop their records (directly or through a cascade), returns
explicit errors instead of silently omitting them, and offers an
administrator command to remove them once revoked elsewhere."""

from contextlib import nullcontext
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from graphql import GraphQLError

from backend.edition import Feature, FeatureUnavailable

# ---------------------------------------------------------------------------
# REST secrets: explicit error instead of silently omitting dynamic secrets
# ---------------------------------------------------------------------------


@pytest.fixture
def dynamic_qs():
    with patch("api.models.DynamicSecret") as Model:
        qs = Model.objects.filter.return_value
        qs.filter.return_value = qs
        yield qs


@pytest.mark.parametrize("params", [{}, {"dynamic": "false"}, {"lease": "true"}])
def test_dynamic_not_requested_is_ignored(dynamic_qs, params):
    from api.views.secrets import dynamic_secrets_unavailable_response

    dynamic_qs.exists.return_value = True
    assert dynamic_secrets_unavailable_response(params, MagicMock()) is None


@pytest.mark.parametrize("params", [{"dynamic": "true"}, {"include_dynamic": "True"}])
def test_dynamic_requested_without_records_is_ignored(dynamic_qs, params):
    """The CLI asks for dynamic secrets by default; with none in the
    environment the static secrets are returned as usual."""
    from api.views.secrets import dynamic_secrets_unavailable_response

    dynamic_qs.exists.return_value = False
    assert dynamic_secrets_unavailable_response(params, MagicMock()) is None


def test_dynamic_requested_with_migrated_records_fails_explicitly(dynamic_qs):
    from api.views.secrets import dynamic_secrets_unavailable_response

    dynamic_qs.exists.return_value = True
    response = dynamic_secrets_unavailable_response(
        {"dynamic": "true", "lease": "true"}, MagicMock(), "/db"
    )
    assert response.status_code == 501
    assert "dynamic secrets feature is not available" in response.data["error"]
    assert "libreseal_remove_legacy_credentials" in response.data["error"]
    dynamic_qs.filter.assert_called_with(path="/db")


# ---------------------------------------------------------------------------
# Models and cascade signals refuse to drop live credentials
# ---------------------------------------------------------------------------


def test_dynamic_secret_delete_refused_with_active_leases():
    from api.models import DynamicSecret

    secret = MagicMock()
    secret.leases.filter.return_value.exists.return_value = True
    with pytest.raises(FeatureUnavailable):
        DynamicSecret.delete(secret)
    secret.save.assert_not_called()


def test_rotating_secret_delete_refused_with_live_credentials():
    from api.models import RotatingSecret

    secret = MagicMock()
    secret.has_live_credentials.return_value = True
    with pytest.raises(FeatureUnavailable):
        RotatingSecret.delete(secret)
    secret.save.assert_not_called()


@pytest.mark.parametrize("live", [True, False])
def test_cascade_signals(live):
    from api.signals import _dynamic_secret_pre_delete, _rotating_secret_pre_delete

    dynamic = MagicMock()
    dynamic.leases.filter.return_value.exists.return_value = live
    rotating = MagicMock()
    rotating.has_live_credentials.return_value = live

    for handler, instance, feature in (
        (_dynamic_secret_pre_delete, dynamic, Feature.DYNAMIC_SECRETS),
        (_rotating_secret_pre_delete, rotating, Feature.SECRET_ROTATION),
    ):
        if live:
            with pytest.raises(FeatureUnavailable) as err:
                handler(sender=None, instance=instance)
            assert err.value.feature == feature
        else:
            handler(sender=None, instance=instance)


def test_account_deletion_with_active_leases_refused():
    from backend.graphene.mutations.account import revoke_lease_now

    with pytest.raises(GraphQLError, match="libreseal_remove_legacy_credentials"):
        revoke_lease_now(MagicMock())


@patch("backend.graphene.mutations.environment.transaction.atomic", return_value=nullcontext())
@patch("backend.graphene.mutations.environment.can_use_custom_envs", return_value=True)
@patch("backend.graphene.mutations.environment.RotatingSecret")
@patch("backend.graphene.mutations.environment.user_has_permission", return_value=True)
@patch("backend.graphene.mutations.environment.Environment")
def test_graphql_environment_delete_blocked_cascade(MockEnv, _perm, MockRotating, _custom, _atomic):
    from backend.graphene.mutations.environment import DeleteEnvironmentMutation

    MockRotating.objects.filter.return_value.exists.return_value = False
    env = MockEnv.objects.get.return_value
    env.delete.side_effect = FeatureUnavailable(Feature.DYNAMIC_SECRETS)

    with patch("backend.graphene.mutations.environment.log_audit_event") as audit:
        with pytest.raises(GraphQLError, match="libreseal_remove_legacy_credentials"):
            DeleteEnvironmentMutation.mutate(None, MagicMock(), "env-1")
    audit.assert_not_called()


# ---------------------------------------------------------------------------
# Administrator command
# ---------------------------------------------------------------------------

CMD = "api.management.commands.libreseal_remove_legacy_credentials"


def _record(rid, live_count):
    record = MagicMock(id=rid, path="/")
    record.name = rid
    record.environment.name = "prod"
    record.environment.app.name = "api"
    record.environment.app.organisation.name = "homelab"
    live = MagicMock()
    live.count.return_value = live_count
    live.exists.return_value = bool(live_count)
    record.leases.filter.return_value = live
    record.credentials.filter.return_value = live
    return record, live


@pytest.fixture
def records():
    dyn_free, _ = _record("dyn-free", 0)
    dyn_live, dyn_live_qs = _record("dyn-live", 2)
    rot_live, rot_live_qs = _record("rot-live", 1)
    with patch(f"{CMD}.DynamicSecret") as Dyn, patch(f"{CMD}.RotatingSecret") as Rot:
        Dyn.objects.filter.return_value.select_related.return_value = [dyn_free, dyn_live]
        Rot.objects.filter.return_value.select_related.return_value = [rot_live]
        yield dyn_free, dyn_live, dyn_live_qs, rot_live, rot_live_qs


def _run(*args):
    out = StringIO()
    call_command("libreseal_remove_legacy_credentials", *args, stdout=out)
    return out.getvalue()


def test_command_lists_only(records):
    dyn_free, dyn_live, _, rot_live, _ = records
    out = _run()
    assert "dynamic  dyn-live  homelab/api/prod/  dyn-live  live credentials: 2" in out
    assert "rotating  rot-live" in out
    for record in (dyn_free, dyn_live, rot_live):
        record.delete.assert_not_called()


def test_command_removes_only_records_without_live_credentials(records):
    dyn_free, dyn_live, dyn_live_qs, rot_live, _ = records
    out = _run("--yes")
    assert "Removed 1 records." in out
    assert "--credentials-revoked" in out
    dyn_free.delete.assert_called_once()
    dyn_live.delete.assert_not_called()
    rot_live.delete.assert_not_called()
    dyn_live_qs.update.assert_not_called()


def test_command_marks_revoked_and_removes_when_confirmed(records):
    dyn_free, dyn_live, dyn_live_qs, rot_live, rot_live_qs = records
    out = _run("--yes", "--credentials-revoked")
    assert "Removed 3 records." in out
    for qs in (dyn_live_qs, rot_live_qs):
        assert qs.update.call_args.kwargs["status"] == "revoked"
    for record in (dyn_free, dyn_live, rot_live):
        record.delete.assert_called_once()
