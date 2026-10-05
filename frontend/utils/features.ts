/**
 * LibreSeal edition features. Availability is a property of the edition, not
 * of an organisation's plan (LibreSeal has no plans). The backend exposes the
 * enabled set through the `libresealFeatures` query; this list mirrors
 * backend/backend/edition.py so the UI can render without a round trip.
 */
export type LibresealFeature =
  | 'custom_roles'
  | 'teams'
  | 'custom_environments'
  | 'service_accounts'
  | 'dynamic_secrets'
  | 'secret_rotation'
  | 'log_streams'
  | 'scim'
  | 'enterprise_sso'
  | 'network_policies'
  | 'billing'
  | 'licensing'

export const DEFAULT_ENABLED_FEATURES: readonly LibresealFeature[] = [
  'custom_environments',
  'custom_roles',
  'service_accounts',
  'teams',
]

export const FEATURE_LABELS: Record<LibresealFeature, string> = {
  custom_roles: 'Custom roles',
  teams: 'Teams',
  custom_environments: 'Custom environments',
  service_accounts: 'Service accounts',
  dynamic_secrets: 'Dynamic secrets',
  secret_rotation: 'Secret rotation',
  log_streams: 'Log streams',
  scim: 'SCIM provisioning',
  enterprise_sso: 'Organisation SSO (OIDC)',
  network_policies: 'Network access policies',
  billing: 'Billing',
  licensing: 'Licensing',
}

export const isFeatureEnabled = (
  feature: LibresealFeature,
  enabled: readonly string[] = DEFAULT_ENABLED_FEATURES
): boolean => enabled.includes(feature)
