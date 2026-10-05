from graphql import GraphQLResolveInfo
from graphql import GraphQLError
from graphql.type import GraphQLList, GraphQLNonNull, GraphQLObjectType
from api.models import (
    Organisation,
    OrganisationMember,
    OrganisationMemberInvite,
)

from django.core.cache import cache
from django.utils import timezone

from api.utils.access.ip import get_client_ip
from api.utils.access.network_policies import (
    UNENFORCEABLE_MESSAGE,
    network_access_denied,
)
from backend.edition import Feature, feature_enabled
from api.utils.access.org_resolution import (
    resolve_org_id,
    resolve_orgs_via_model,
    resolve_via_model,
)


def _output_graphene_type(info: GraphQLResolveInfo):
    """Unwrap NonNull/List wrappers from the mutation's return type and
    return the underlying Graphene class (or None)."""
    return_type = info.return_type
    while isinstance(return_type, (GraphQLNonNull, GraphQLList)):
        return_type = return_type.of_type
    if not isinstance(return_type, GraphQLObjectType):
        return None
    return getattr(return_type, "graphene_type", None)


def _bypasses_sso_enforcement(info: GraphQLResolveInfo) -> bool:
    """SSO admin mutations carry `bypass_sso_enforcement = True` so an
    admin locked out by their own require_sso=True config can recover.
    Per-mutation Owner/Admin role gating remains the safety net."""
    graphene_type = _output_graphene_type(info)
    return bool(getattr(graphene_type, "bypass_sso_enforcement", False))


def _model_for_mutation(info: GraphQLResolveInfo):
    """Derive the Django model a mutation operates on for the bare-`id`/
    `ids` case. Reads `org_resource_model` if declared, else picks the
    first `DjangoObjectType`-backed field on the mutation's output."""
    graphene_type = _output_graphene_type(info)
    if graphene_type is None:
        return None

    explicit = getattr(graphene_type, "org_resource_model", None)
    if explicit:
        return explicit

    return_type = info.return_type
    while isinstance(return_type, (GraphQLNonNull, GraphQLList)):
        return_type = return_type.of_type
    for _name, gql_field in return_type.fields.items():
        ftype = gql_field.type
        while isinstance(ftype, (GraphQLNonNull, GraphQLList)):
            ftype = ftype.of_type
        if not isinstance(ftype, GraphQLObjectType):
            continue
        gtype = getattr(ftype, "graphene_type", None)
        meta = getattr(gtype, "_meta", None) if gtype is not None else None
        model = getattr(meta, "model", None) if meta is not None else None
        if model is not None:
            return model.__name__
    return None


class NetworkPolicyUnenforceableError(GraphQLError):
    def __init__(self, organisation_name: str):
        super().__init__(
            message=UNENFORCEABLE_MESSAGE,
            extensions={
                "code": "IP_RESTRICTED",
                "organisation_name": organisation_name,
            },
        )


class IPRestrictedError(GraphQLError):
    def __init__(self, organisation_name: str):
        super().__init__(
            message=f"Your IP address is not allowed to access {organisation_name}",
            extensions={
                "code": "IP_RESTRICTED",
                "organisation_name": organisation_name,
            },
        )


# Invite bootstrap: reading and accepting an invite. Exempted from SSO
# enforcement for the invite holder, because requiring an org-SSO session
# to JOIN is circular — org-SSO login only resolves identities linked to a
# current member, and membership is what acceptance creates. Both resolvers
# independently verify the caller's email matches the invite, so the
# exemption grants exactly one capability: accepting your own invite.
# Matched by ROOT field name (parent type Query/Mutation) — never reuse
# these names for a new field without revisiting this exemption.
INVITE_BOOTSTRAP_FIELDS = frozenset({"validateInvite", "createOrganisationMember"})


def _is_invite_bootstrap_field(info: GraphQLResolveInfo) -> bool:
    return (
        info.field_name in INVITE_BOOTSTRAP_FIELDS
        and getattr(info.parent_type, "name", None) in ("Query", "Mutation")
    )


class SSORequiredError(GraphQLError):
    def __init__(self, organisation_name: str, organisation_id: str):
        super().__init__(
            message=f"{organisation_name} requires Single Sign-On. Please sign in via SSO to continue.",
            extensions={
                "code": "SSO_REQUIRED",
                "organisation_name": organisation_name,
                "organisation_id": organisation_id,
            },
        )


class OrgSSOEnforcementMiddleware:
    """Enforce per-org SSO requirements on every org-scoped resolver.

    Sessions established via the org-level SSO flow carry
    ``auth_sso_org_id``; sessions from instance-level SSO (Google,
    GitHub, GitLab) don't, so they can't bypass org-level enforcement.
    """

    _DECISION_CACHE_ATTR = "_org_sso_decision_cache"
    _ID_CACHE_ATTR = "_org_sso_id_cache"
    _DECISION_REDIS_TTL = 60

    @staticmethod
    def _decision_redis_key(org_id) -> str:
        return f"org_sso_decision:{org_id}"

    @classmethod
    def invalidate_decision(cls, org_id) -> None:
        """Called when ``require_sso`` flips so the change takes effect
        before the Redis TTL would naturally expire the cached value."""
        try:
            cache.delete(cls._decision_redis_key(org_id))
        except Exception:
            pass

    def resolve(self, next, root, info: GraphQLResolveInfo, **kwargs):
        request = info.context
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return next(root, info, **kwargs)

        # SSO admin mutations carry an opt-in bypass so a misconfigured
        # require_sso=True org isn't a UI dead-end. Per-mutation role
        # checks remain in force.
        if _bypasses_sso_enforcement(info):
            return next(root, info, **kwargs)

        org_id = self._resolve_org_id(request, kwargs, info)
        if not org_id:
            return next(root, info, **kwargs)

        # Skip enforcement when the session is already SSO-bound to this
        # org — it would have been blocked at sign-in otherwise.
        session = getattr(request, "session", None)
        session_method = session.get("auth_method") if session else None
        session_org_id = session.get("auth_sso_org_id") if session else None
        if session_method == "sso" and session_org_id == str(org_id):
            return next(root, info, **kwargs)

        decision = self._get_org_decision(request, org_id)
        if decision is None:
            return next(root, info, **kwargs)

        require_sso, org_name = decision

        # Block on require_sso OR per-member SCIM (IdP is the source of
        # truth for SCIM-provisioned access to this org).
        if not (require_sso or self._is_scim_managed(request, user, org_id)):
            return next(root, info, **kwargs)

        # Invite bootstrap exemption — checked last so the invite query
        # only runs when we would otherwise refuse.
        if _is_invite_bootstrap_field(info) and self._holds_valid_invite(
            request, user, org_id
        ):
            return next(root, info, **kwargs)

        raise SSORequiredError(org_name, str(org_id))

    @classmethod
    def _get_org_decision(cls, request, org_id):
        cache_l1 = getattr(request, cls._DECISION_CACHE_ATTR, None)
        if cache_l1 is None:
            cache_l1 = {}
            setattr(request, cls._DECISION_CACHE_ATTR, cache_l1)

        key = str(org_id)
        if key in cache_l1:
            return cache_l1[key]

        redis_key = cls._decision_redis_key(org_id)
        try:
            cached = cache.get(redis_key)
        except Exception:
            cached = None
        if cached is not None:
            # Sentinel: [False, ""] means "org not loadable"
            if cached == [False, ""]:
                cache_l1[key] = None
                return None
            decision = (bool(cached[0]), cached[1])
            cache_l1[key] = decision
            return decision

        try:
            org = Organisation.objects.only("require_sso", "name").get(id=org_id)
            decision = (bool(org.require_sso), org.name)
        except Organisation.DoesNotExist:
            decision = None

        try:
            cache.set(
                redis_key,
                [decision[0], decision[1]] if decision else [False, ""],
                timeout=cls._DECISION_REDIS_TTL,
            )
        except Exception:
            pass

        cache_l1[key] = decision
        return decision

    @classmethod
    def _is_scim_managed(cls, request, user, org_id):
        """Whether `user` is a SCIM-managed member of `org_id`.
        Cached per-(user, org) within the request scope."""
        cache_attr = "_scim_managed_cache"
        request_cache = getattr(request, cache_attr, None)
        if request_cache is None:
            request_cache = {}
            setattr(request, cache_attr, request_cache)

        user_id = getattr(user, "userId", None) or getattr(user, "id", None) or user
        key = (str(user_id), str(org_id))
        if key in request_cache:
            return request_cache[key]

        result = OrganisationMember.objects.filter(
            organisation_id=org_id,
            user=user,
            deleted_at__isnull=True,
            scimuser__isnull=False,
            scimuser__active=True,
        ).exists()
        request_cache[key] = result
        return result

    @classmethod
    def _holds_valid_invite(cls, request, user, org_id):
        """Whether `user` holds a valid, unexpired invite to `org_id`.
        Cached per-(user, org) within the request scope."""
        cache_attr = "_invite_holder_cache"
        request_cache = getattr(request, cache_attr, None)
        if request_cache is None:
            request_cache = {}
            setattr(request, cache_attr, request_cache)

        email = getattr(user, "email", None)
        if not email:
            return False

        key = (email.lower(), str(org_id))
        if key in request_cache:
            return request_cache[key]

        result = OrganisationMemberInvite.objects.filter(
            organisation_id=org_id,
            invitee_email__iexact=email,
            valid=True,
            expires_at__gt=timezone.now(),
        ).exists()
        request_cache[key] = result
        return result

    @classmethod
    def _request_cache(cls, request):
        request_cache = getattr(request, cls._ID_CACHE_ATTR, None)
        if not isinstance(request_cache, dict):
            request_cache = {}
            setattr(request, cls._ID_CACHE_ATTR, request_cache)
        return request_cache

    @classmethod
    def _resolve_org_id(cls, request, kwargs, info=None):
        """First organisation referenced by the resolver kwargs, or None."""
        return next(cls._iter_org_ids(request, kwargs, info, all_ids=False), None)

    @classmethod
    def resolve_org_ids(cls, request, kwargs, info=None):
        """Every organisation referenced by the resolver kwargs, including
        all items of bulk arguments (`ids`, lists of input objects)."""
        return set(cls._iter_org_ids(request, kwargs, info, all_ids=True))

    @classmethod
    def _iter_org_ids(cls, request, kwargs, info=None, all_ids=False):
        request_cache = cls._request_cache(request)

        for direct in ("organisation_id", "org_id"):
            val = kwargs.get(direct)
            if val:
                yield str(val)

        for name, value in kwargs.items():
            if not value or not isinstance(name, str):
                continue

            # `<model>_id` — FK auto-discovery in org_resolution.
            if name.endswith("_id"):
                if name in ("organisation_id", "org_id", "token_id"):
                    continue
                org_id = resolve_org_id(name, value, request_cache)
                if org_id:
                    yield org_id
                continue

            # Bare `id` / `ids` — model derived from the mutation's
            # return type or an `org_resource_model` class attribute.
            if name in ("id", "ids"):
                model_name = _model_for_mutation(info) if info is not None else None
                if not model_name:
                    continue
                if name == "ids" and all_ids:
                    yield from resolve_orgs_via_model(
                        model_name, list(value), request_cache
                    )
                    continue
                if name == "ids":
                    value = value[0] if value else None
                if isinstance(value, (str, int)):
                    org_id = resolve_via_model(model_name, value, request_cache)
                    if org_id:
                        yield org_id
                continue

            # Input objects (`*_data`, `*_inputs`, `input`) — recurse into
            # their `*_id` fields, and their bare `id` when the mutation's
            # model is known.
            if name.endswith(("_data", "_inputs")) or name == "input":
                model_name = _model_for_mutation(info) if info is not None else None
                yield from cls._iter_input_org_ids(
                    value, request_cache, model_name, all_ids
                )

        token_id = kwargs.get("token_id")
        if token_id:
            org_id = cls._lookup_token_org(request, token_id)
            if org_id:
                yield org_id

    @classmethod
    def _iter_input_org_ids(cls, value, request_cache, model_name=None, all_ids=False):
        """Walk an input object (or list of them) for any `<model>_id`."""
        items = value if isinstance(value, (list, tuple)) else [value]
        for item in items:
            if item is None:
                continue
            try:
                entries = (
                    item.items()
                    if hasattr(item, "items")
                    else getattr(item, "__dict__", {}).items()
                )
            except Exception:
                continue
            found = False
            for key, val in entries:
                if not val or not isinstance(key, str):
                    continue
                org_id = None
                if key in ("organisation_id", "org_id"):
                    org_id = str(val)
                elif key.endswith("_id"):
                    org_id = resolve_org_id(key, val, request_cache)
                elif key == "id" and model_name and isinstance(val, (str, int)):
                    org_id = resolve_via_model(model_name, val, request_cache)
                if org_id:
                    found = True
                    yield org_id
                    if not all_ids:
                        return
            if found and not all_ids:
                return

    @classmethod
    def _resolve_from_input_value(cls, value, request_cache):
        """Walk an input object (or list of them) for any `<model>_id`."""
        return next(cls._iter_input_org_ids(value, request_cache), None)

    @classmethod
    def _lookup_token_org(cls, request, token_id):
        """token_id spans UserToken / ServiceAccountToken /
        EnvironmentToken; probe in order, stop
        on first hit. UUIDs are globally unique so collisions can't
        happen."""
        from api.models import (
            EnvironmentToken,
            ServiceAccountToken,
            UserToken,
        )
        request_cache = cls._request_cache(request)
        cache_key = ("token_id", token_id)
        if cache_key in request_cache:
            return request_cache[cache_key]

        org_id = None
        try:
            # UserToken.user is a FK to OrganisationMember (not CustomUser),
            # so ut.user_id is an OrganisationMember PK. Look up the member
            # by .id, not .user_id (which would compare against CustomUser
            # PKs and never match).
            ut = UserToken.objects.only("user_id").get(id=token_id)
            try:
                member = OrganisationMember.objects.only("organisation_id").get(
                    id=ut.user_id, deleted_at__isnull=True
                )
                org_id = str(member.organisation_id)
            except OrganisationMember.DoesNotExist:
                pass
        except UserToken.DoesNotExist:
            pass

        if not org_id:
            try:
                sat = ServiceAccountToken.objects.only(
                    "service_account_id"
                ).get(id=token_id)
                org_id = resolve_org_id(
                    "service_account_id", sat.service_account_id, request_cache
                )
            except ServiceAccountToken.DoesNotExist:
                pass

        if not org_id:
            try:
                et = EnvironmentToken.objects.only("environment_id").get(id=token_id)
                org_id = resolve_org_id(
                    "environment_id", et.environment_id, request_cache
                )
            except EnvironmentToken.DoesNotExist:
                pass

        request_cache[cache_key] = org_id
        return org_id


class IPWhitelistMiddleware:
    """
    Graphene middleware enforcing network access policies on every resolver
    that references an organisation's resources.

    The organisations are resolved from the resolver arguments with the same
    auto-discovery used for SSO enforcement (``organisation_id``, any
    ``<model>_id``, bare ``id``/``ids``, input objects, ``token_id``), and
    every referenced organisation is checked, so bulk arguments cannot mix
    resources from an organisation whose policies deny the caller. Decisions
    are cached per request and organisation.
    """

    _DECISION_CACHE_ATTR = "_network_policy_decision_cache"

    def resolve(self, next, root, info: GraphQLResolveInfo, **kwargs):
        request = info.context
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise GraphQLError("Authentication required")

        if kwargs:
            org_ids = OrgSSOEnforcementMiddleware.resolve_org_ids(
                request, kwargs, info
            )
            for org_id in sorted(org_ids):
                self._enforce(request, user, org_id)

        return next(root, info, **kwargs)

    def _enforce(self, request, user, organisation_id):
        cache_l1 = getattr(request, self._DECISION_CACHE_ATTR, None)
        if not isinstance(cache_l1, dict):
            cache_l1 = {}
            setattr(request, self._DECISION_CACHE_ATTR, cache_l1)

        key = str(organisation_id)
        if key not in cache_l1:
            org = Organisation.objects.filter(id=organisation_id).first()
            if org is None:
                # Unknown organisation: nothing to protect; resolvers reject it.
                cache_l1[key] = None
            else:
                org_member = OrganisationMember.objects.filter(
                    organisation_id=organisation_id,
                    user_id=user.userId,
                    deleted_at__isnull=True,
                ).first()
                # Non-members are rejected by the resolvers' own permission
                # checks; organisation-global policies still apply to them.
                denied = network_access_denied(
                    org, org_member, self.get_client_ip(request)
                )
                cache_l1[key] = org.name if denied else None

        denied_org_name = cache_l1[key]
        if denied_org_name is not None:
            if feature_enabled(Feature.NETWORK_POLICIES):
                raise IPRestrictedError(denied_org_name)
            raise NetworkPolicyUnenforceableError(denied_org_name)

    def get_client_ip(self, request):
        return get_client_ip(request)
