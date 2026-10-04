'use client'

import { UnavailableFeature } from '@/components/common/UnavailableFeature'

export default function DynamicSecrets() {
  return (
    <UnavailableFeature
      feature="dynamic_secrets"
      title="Dynamic Secrets"
      description="Generate short-lived credentials for third-party services."
    />
  )
}
