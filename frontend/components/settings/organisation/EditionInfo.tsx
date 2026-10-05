import { organisationContext } from '@/contexts/organisationContext'
import { GetOrganisationPlan } from '@/graphql/queries/organisation/getOrganisationPlan.gql'
import { GetLibresealFeatures } from '@/graphql/queries/libreseal/getLibresealFeatures.gql'
import { useQuery } from '@apollo/client'
import { useContext } from 'react'
import Spinner from '@/components/common/Spinner'
import { FaCheckCircle, FaCube, FaTimesCircle, FaUser } from 'react-icons/fa'
import { FaRobot } from 'react-icons/fa6'
import { LogoWordMark } from '@/components/common/LogoWordMark'
import {
  DEFAULT_ENABLED_FEATURES,
  FEATURE_LABELS,
  LibresealFeature,
  isFeatureEnabled,
} from '@/utils/features'

const USER_FACING_FEATURES: LibresealFeature[] = [
  'custom_environments',
  'custom_roles',
  'teams',
  'service_accounts',
  'dynamic_secrets',
  'secret_rotation',
  'log_streams',
  'scim',
  'enterprise_sso',
  'network_policies',
]

/**
 * Organisation overview for a LibreSeal instance: usage counters and the
 * features available in this edition. LibreSeal has no plans or limits.
 */
export const EditionInfo = () => {
  const { activeOrganisation } = useContext(organisationContext)

  const { loading, data } = useQuery(GetOrganisationPlan, {
    variables: { organisationId: activeOrganisation?.id },
    skip: !activeOrganisation,
    fetchPolicy: 'cache-and-network',
  })
  const { data: featuresData } = useQuery(GetLibresealFeatures)
  const enabled: readonly string[] = featuresData?.libresealFeatures ?? DEFAULT_ENABLED_FEATURES

  if (loading || !data?.organisationPlan)
    return (
      <div className="flex items-center justify-center p-8">
        <Spinner size="md" />
      </div>
    )

  const plan = data.organisationPlan

  return (
    <div className="space-y-6 rounded-lg bg-zinc-100 dark:bg-zinc-800 p-4 ring-1 ring-inset ring-neutral-500/20">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <LogoWordMark className="h-8 fill-black dark:fill-white" />
          <p className="text-sm text-neutral-500">
            Self-hosted, free software. No plans, seat limits or license keys.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 text-sm">
        <div className="flex items-center gap-2">
          <FaUser className="text-neutral-500" />
          <span>
            <span className="font-semibold">{plan.seatsUsed?.users ?? 0}</span> members
          </span>
        </div>
        <div className="flex items-center gap-2">
          <FaRobot className="text-neutral-500" />
          <span>
            <span className="font-semibold">{plan.seatsUsed?.serviceAccounts ?? 0}</span> service
            accounts
          </span>
        </div>
        <div className="flex items-center gap-2">
          <FaCube className="text-neutral-500" />
          <span>
            <span className="font-semibold">{plan.appCount ?? 0}</span> apps
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-medium">Features in this edition</h3>
        <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2 text-xs">
          {USER_FACING_FEATURES.map((feature) => {
            const on = isFeatureEnabled(feature, enabled)
            return (
              <li key={feature} className="flex items-center gap-2">
                {on ? (
                  <FaCheckCircle className="text-emerald-500" />
                ) : (
                  <FaTimesCircle className="text-neutral-500" />
                )}
                <span className={on ? '' : 'text-neutral-500'}>
                  {FEATURE_LABELS[feature]}
                  {!on && ' — not available'}
                </span>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
