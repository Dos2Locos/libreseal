'use client'

import { UnavailableFeature } from '@/components/common/UnavailableFeature'

export default function SCIMLayout(_props: { children: React.ReactNode }) {
  return (
    <section className="px-3 sm:px-4 lg:px-6">
      <UnavailableFeature
        feature="scim"
        title="SCIM Provisioning"
        description="Automatic user and group provisioning from your identity provider."
      />
    </section>
  )
}
