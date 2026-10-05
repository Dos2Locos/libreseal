'use client'

import { UnavailableFeature } from '@/components/common/UnavailableFeature'

export default function LogStreams() {
  return (
    <UnavailableFeature
      feature="log_streams"
      title="Log Streams"
      description="Stream audit logs and secret events to your SIEM or log management platform."
    />
  )
}
