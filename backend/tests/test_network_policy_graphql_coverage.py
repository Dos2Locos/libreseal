"""Every GraphQL root field that takes arguments must let the network policy
middleware resolve the organisation it touches, or be explicitly listed as
not organisation-scoped. A new resolver whose arguments cannot be mapped to
an organisation would otherwise silently bypass network access policies."""

from types import SimpleNamespace

import pytest
from graphene.utils.str_converters import to_snake_case
from graphql.type import (
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
)

from api.utils.access.org_resolution import (
    KWARG_MODEL_ALIASES,
    _path_to_organisation,
    _snake_to_pascal,
)
from backend.graphene.middleware import _model_for_mutation
from backend.schema import schema

# Root fields that act on the caller's own account, on instance-level data
# or on resources that do not belong to an organisation.
NOT_ORGANISATION_SCOPED = {
    ("Query", "organisationNameAvailable"),
    ("Query", "verifyPassword"),
    ("Query", "validateAwsAssumeRoleCredentials"),
    ("Mutation", "createOrganisation"),
    ("Mutation", "requestEmailChange"),
    ("Mutation", "confirmEmailChange"),
    ("Mutation", "updateAccountProfile"),
    ("Mutation", "activateMfa"),
    ("Mutation", "disableMfa"),
    ("Mutation", "regenerateRecoveryCodes"),
    ("Mutation", "createLockbox"),
}


def _unwrap(gql_type):
    while isinstance(gql_type, (GraphQLNonNull, GraphQLList)):
        gql_type = gql_type.of_type
    return gql_type


def _id_kwarg_resolvable(name):
    if name in ("organisation_id", "org_id", "token_id"):
        return True
    if not name.endswith("_id"):
        return False
    model = KWARG_MODEL_ALIASES.get(name) or _snake_to_pascal(name[:-3])
    return _path_to_organisation(model) is not None


def _resolvable(field):
    model = _model_for_mutation(SimpleNamespace(return_type=field.type))
    model_resolvable = bool(model) and _path_to_organisation(model) is not None
    for arg_name, arg in field.args.items():
        name = to_snake_case(arg_name)
        if _id_kwarg_resolvable(name):
            return True
        if name in ("id", "ids") and model_resolvable:
            return True
        arg_type = _unwrap(arg.type)
        if isinstance(arg_type, GraphQLInputObjectType) and (
            name.endswith(("_data", "_inputs")) or name == "input"
        ):
            for input_field in arg_type.fields:
                sub = to_snake_case(input_field)
                if _id_kwarg_resolvable(sub) or (sub == "id" and model_resolvable):
                    return True
    return False


def _root_fields_with_args():
    gql = schema.graphql_schema
    for type_name in ("Query", "Mutation"):
        for field_name, field in gql.get_type(type_name).fields.items():
            if field.args:
                yield type_name, field_name, field


@pytest.mark.parametrize(
    "type_name,field_name,field",
    list(_root_fields_with_args()),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_root_field_organisation_is_resolvable(type_name, field_name, field):
    if (type_name, field_name) in NOT_ORGANISATION_SCOPED:
        pytest.skip("not organisation-scoped")
    assert _resolvable(field), (
        f"{type_name}.{field_name}: the network policy middleware cannot resolve "
        "its organisation; add an alias in org_resolution, an "
        "`org_resource_model`, or list it in NOT_ORGANISATION_SCOPED."
    )


def test_allowlist_entries_exist():
    gql = schema.graphql_schema
    for type_name, field_name in NOT_ORGANISATION_SCOPED:
        assert field_name in gql.get_type(type_name).fields
