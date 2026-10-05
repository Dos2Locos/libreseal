"""Schema-shape guards for fields with withholding resolvers."""

from graphql import GraphQLNonNull

from backend.schema import schema


def test_provider_credentials_field_is_nullable():
    """resolve_credentials returns None for users without
    IntegrationCredentials read — the field must stay nullable, or the
    withholding becomes a hard GraphQL error that nulls the surrounding
    payload."""
    field = schema.graphql_schema.type_map["ProviderCredentialsType"].fields[
        "credentials"
    ]
    assert not isinstance(field.type, GraphQLNonNull)


def test_create_environment_key_mutation_is_not_exposed():
    """The legacy mutation granted environment access without authorisation.

    Environment grants must go through the permission-checked member-scope
    mutations instead.
    """
    mutation_fields = schema.graphql_schema.mutation_type.fields

    assert "createEnvironmentKey" not in mutation_fields


def test_libreseal_features_query_lists_enabled_features():
    from unittest.mock import MagicMock

    result = schema.execute(
        "{ libresealFeatures }", context_value=MagicMock()
    )
    assert result.errors is None
    assert result.data["libresealFeatures"] == [
        "custom_environments",
        "custom_roles",
        "network_policies",
        "service_accounts",
        "teams",
    ]


def test_enterprise_only_fields_are_not_exposed():
    query_fields = schema.graphql_schema.query_type.fields
    mutation_fields = schema.graphql_schema.mutation_type.fields

    for name in (
        "dynamicSecrets",
        "rotatingSecrets",
        "logStreams",
        "scimTokens",
        "license",
        "organisationLicense",
        "stripeCheckoutDetails",
    ):
        assert name not in query_fields
    for name in (
        "createAwsDynamicSecret",
        "createRotatingSecret",
        "createLogStream",
        "createScimToken",
        "createSubscriptionCheckoutSession",
    ):
        assert name not in mutation_fields
