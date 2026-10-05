import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-key",
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "rest_framework",
        ],
        REST_FRAMEWORK={
            "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
        },
    )
    django.setup()

import unittest
import json
import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from django.test import RequestFactory
from api.views.identities.aws.iam import aws_iam_auth


class TestAwsIamAuth(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # No network access policies apply unless a test says otherwise.
        policy_patch = patch(
            "api.views.identities.aws.iam.network_policy_denial", return_value=None
        )
        self.mock_network_policy = policy_patch.start()
        self.addCleanup(policy_patch.stop)
        self.service_account_id = "12345678-1234-1234-1234-123456789abc"

        # Valid AWS STS response XML
        self.valid_aws_response = """<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetCallerIdentityResult>
    <Arn>arn:aws:iam::123456789012:user/test-user</Arn>
    <UserId>AIDACKCEVSQ6C2EXAMPLE</UserId>
    <Account>123456789012</Account>
  </GetCallerIdentityResult>
  <ResponseMetadata>
    <RequestId>01234567-89ab-cdef-0123-456789abcdef</RequestId>
  </ResponseMetadata>
</GetCallerIdentityResponse>"""

        # Valid request payload
        self.valid_payload = {
            "account": {"type": "service", "id": self.service_account_id},
            "awsIam": {
                "httpRequestMethod": "POST",
                "httpRequestUrl": "aHR0cHM6Ly9zdHMuYXAtc291dGgtMS5hbWF6b25hd3MuY29t",  # https://sts.ap-south-1.amazonaws.com
                "httpRequestHeaders": "eyJDb250ZW50LVR5cGUiOiAiYXBwbGljYXRpb24veC13d3ctZm9ybS11cmxlbmNvZGVkOyBjaGFyc2V0PXV0Zi04IiwgIlgtQW16LURhdGUiOiAiMjAyNTA4MjdUMDgwNzE5WiIsICJBdXRob3JpemF0aW9uIjogIkFXUzQtSE1BQy1TSEEyNTYgQ3JlZGVudGlhbD1BS0lBRVhBTVBMRTEyMzQ1LzIwMjUwODI3L2FwLXNvdXRoLTEvc3RzL2F3czRfcmVxdWVzdCwgU2lnbmVkSGVhZGVycz1jb250ZW50LXR5cGU7aG9zdDt4LWFtei1kYXRlLCBTaWduYXR1cmU9ZXhhbXBsZXNpZ25hdHVyZTEyMzQ1Njc4OTBhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5eiIsICJDb250ZW50LUxlbmd0aCI6ICI0MyJ9",
                "httpRequestBody": "QWN0aW9uPUdldENhbGxlcklkZW50aXR5JlZlcnNpb249MjAxMS0wNi0xNQ==",
            },
            "tokenRequest": {"ttl": 60},
        }

    def make_request(self, payload):
        request = self.factory.post(
            "/api/identities/aws/iam", data=payload, content_type="application/json"
        )
        return request

    def test_invalid_json_payload(self):
        request = self.factory.post(
            "/api/identities/aws/iam",
            data="invalid json",
            content_type="application/json",
        )
        response = aws_iam_auth(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON", response.content.decode())

    @patch("api.views.identities.aws.iam.resolve_service_account")
    def test_service_account_not_found(self, mock_resolve):
        mock_resolve.return_value = None
        request = self.make_request(self.valid_payload)

        response = aws_iam_auth(request)

        self.assertEqual(response.status_code, 404)
        self.assertIn("Service account not found", response.content.decode())

    @patch("api.views.identities.aws.iam.resolve_service_account")
    def test_no_aws_iam_identity_attached(self, mock_resolve):
        mock_sa = MagicMock()
        mock_sa.server_wrapped_keyring = "keyring"
        mock_sa.identities.filter.return_value = []
        mock_resolve.return_value = mock_sa

        request = self.make_request(self.valid_payload)
        response = aws_iam_auth(request)

        self.assertEqual(response.status_code, 404)
        self.assertIn("No AWS IAM identity attached", response.content.decode())

    @patch("api.views.identities.aws.iam.resolve_service_account")
    @patch("django.utils.timezone.now")
    def test_signature_expired(self, mock_now, mock_resolve):
        mock_identity = MagicMock()
        mock_identity.config = {"signatureTtlSeconds": 60}

        mock_sa = MagicMock()
        mock_sa.server_wrapped_keyring = "keyring"
        mock_sa.identities.filter.return_value = [mock_identity]
        mock_resolve.return_value = mock_sa

        # Mock time to be way after X-Amz-Date (2025-08-27T08:07:19Z)
        mock_now.return_value = datetime(2025, 8, 27, 10, 0, 0, tzinfo=timezone.utc)

        request = self.make_request(self.valid_payload)
        response = aws_iam_auth(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn("Signature expired", response.content.decode())

    @patch("api.views.identities.aws.iam.resolve_service_account")
    @patch("django.utils.timezone.now")
    def test_sts_endpoint_mismatch(self, mock_now, mock_resolve):
        mock_identity = MagicMock()
        mock_identity.config = {
            "signatureTtlSeconds": 300,
            "stsEndpoint": "https://sts.us-east-1.amazonaws.com",  # Mismatch
        }

        mock_sa = MagicMock()
        mock_sa.server_wrapped_keyring = "keyring"
        mock_sa.identities.filter.return_value = [mock_identity]
        mock_resolve.return_value = mock_sa

        mock_now.return_value = datetime(2025, 8, 27, 8, 7, 30, tzinfo=timezone.utc)

        request = self.make_request(self.valid_payload)
        response = aws_iam_auth(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("STS endpoint mismatch", response.content.decode())

    @patch("api.views.identities.aws.iam.resolve_service_account")
    @patch("django.utils.timezone.now")
    @patch("requests.request")
    def test_aws_sts_validation_failed(self, mock_requests, mock_now, mock_resolve):
        mock_identity = MagicMock()
        mock_identity.config = {
            "signatureTtlSeconds": 300,
            "stsEndpoint": "https://sts.ap-south-1.amazonaws.com",
        }

        mock_sa = MagicMock()
        mock_sa.server_wrapped_keyring = "keyring"
        mock_sa.identities.filter.return_value = [mock_identity]
        mock_resolve.return_value = mock_sa

        mock_now.return_value = datetime(2025, 8, 27, 8, 7, 30, tzinfo=timezone.utc)

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_requests.return_value = mock_resp

        request = self.make_request(self.valid_payload)
        response = aws_iam_auth(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn("AWS STS validation failed", response.content.decode())

    @patch("api.views.identities.aws.iam.resolve_service_account")
    @patch("django.utils.timezone.now")
    @patch("requests.request")
    @patch("api.views.identities.aws.iam.mint_service_account_token")
    def test_valid_authentication_success(
        self, mock_mint, mock_requests, mock_now, mock_resolve
    ):
        mock_identity = MagicMock()
        mock_identity.config = {
            "signatureTtlSeconds": 300,
            "stsEndpoint": "https://sts.ap-south-1.amazonaws.com",
        }
        mock_identity.default_ttl_seconds = 3600
        mock_identity.max_ttl_seconds = 86400
        mock_identity.get_trusted_list.return_value = [
            "arn:aws:iam::123456789012:user/test-*"
        ]

        mock_sa = MagicMock()
        mock_sa.server_wrapped_keyring = "keyring"
        mock_sa.identities.filter.return_value = [mock_identity]
        mock_resolve.return_value = mock_sa

        mock_now.return_value = datetime(2025, 8, 27, 8, 7, 30, tzinfo=timezone.utc)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self.valid_aws_response
        mock_requests.return_value = mock_resp

        mock_mint.return_value = {"token": "success"}

        request = self.make_request(self.valid_payload)
        response = aws_iam_auth(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("authentication", json.loads(response.content))

    @patch("api.views.identities.aws.iam.resolve_service_account")
    @patch("django.utils.timezone.now")
    @patch("requests.request")
    @patch("api.views.identities.aws.iam.mint_service_account_token")
    def test_multiple_identities_selection(
        self, mock_mint, mock_requests, mock_now, mock_resolve
    ):
        # Identity 1: Wrong endpoint.
        # We use a valid but non-matching pattern to ensure we don't hit the wildcard validation error (400)
        # if this identity were incorrectly selected.
        id1 = MagicMock()
        id1.config = {
            "signatureTtlSeconds": 300,
            "stsEndpoint": "https://sts.us-east-1.amazonaws.com",
        }
        id1.get_trusted_list.return_value = ["arn:aws:iam::111111111111:user/*"]

        # Identity 2: Correct endpoint
        id2 = MagicMock()
        id2.config = {
            "signatureTtlSeconds": 300,
            "stsEndpoint": "https://sts.ap-south-1.amazonaws.com",
        }
        id2.default_ttl_seconds = 3600
        id2.max_ttl_seconds = 86400
        id2.get_trusted_list.return_value = ["arn:aws:iam::123456789012:user/test-*"]

        mock_sa = MagicMock()
        mock_sa.server_wrapped_keyring = "keyring"
        # Return both identities
        mock_sa.identities.filter.return_value = [id1, id2]
        mock_resolve.return_value = mock_sa

        mock_now.return_value = datetime(2025, 8, 27, 8, 7, 30, tzinfo=timezone.utc)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self.valid_aws_response
        mock_requests.return_value = mock_resp

        mock_mint.return_value = {"token": "success"}

        request = self.make_request(self.valid_payload)
        response = aws_iam_auth(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("authentication", json.loads(response.content))

    @patch("api.views.identities.aws.iam.requests.request")
    @patch("api.views.identities.aws.iam.resolve_service_account")
    def test_network_policy_denies_before_external_validation(
        self, mock_resolve, mock_external
    ):
        """A service account whose network policies exclude the client IP
        gets 403 and the external identity provider is never contacted."""
        from django.http import JsonResponse

        mock_resolve.return_value = MagicMock(server_wrapped_keyring="keyring")
        self.mock_network_policy.return_value = JsonResponse(
            {"error": "Access denied: a network access policy restricts access from your IP address."},
            status=403,
        )
        response = aws_iam_auth(self.make_request(self.valid_payload))

        self.assertEqual(response.status_code, 403)
        self.assertIn("network access policy", response.content.decode())
        self.mock_network_policy.assert_called_once()
        self.assertIs(self.mock_network_policy.call_args.args[1], mock_resolve.return_value)
        mock_external.assert_not_called()
