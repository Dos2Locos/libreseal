'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getHealth } from '@/utils/appConfig'

export const LIBRESEAL_RELEASES_URL = 'https://github.com/Dos2Locos/libreseal/releases'

interface HealthData {
  version: string
}

/**
 * Shows the version reported by this instance's backend. LibreSeal does not
 * query third-party services for update checks; the link lets admins compare
 * releases themselves.
 */
export const ReleaseInfo = () => {
  const [healthData, setHealthData] = useState<HealthData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHealth(process.env.NEXT_PUBLIC_BACKEND_API_BASE!)
      .then(setHealthData)
      .catch((err) => setError((err as Error).message))
  }, [])

  if (error) {
    return <div className="text-red-500">Error: {error}</div>
  }

  if (!healthData) {
    return <div className="text-gray-500">Loading...</div>
  }

  return (
    <div className="flex items-center gap-2">
      <span className="font-medium">LibreSeal server version:</span>
      <span className="font-mono">{healthData.version}</span>
      <Link
        href={LIBRESEAL_RELEASES_URL}
        target="_blank"
        rel="noreferrer"
        className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline"
      >
        Releases
      </Link>
    </div>
  )
}
