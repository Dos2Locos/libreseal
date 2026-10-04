import { getHealth } from '@/utils/appConfig'
import Link from 'next/link'

export const VersionLabel = async () => {
  const healthData = await getHealth(process.env.BACKEND_API_BASE!)

  return (
    <Link
      href={`https://github.com/Dos2Locos/libreseal/releases/tag/${healthData.version}`}
      target="_blank"
      rel="noreferrer"
      className="font-mono text-neutral-500 hover:text-neutral-400 transition ease text-sm"
    >
      {healthData.version}
    </Link>
  )
}
