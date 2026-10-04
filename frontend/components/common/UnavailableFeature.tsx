import { FaBan } from 'react-icons/fa'
import { EmptyState } from '@/components/common/EmptyState'
import { FEATURE_LABELS, LibresealFeature } from '@/utils/features'

export const UNAVAILABLE_FEATURE_DOCS_URL =
  'https://github.com/Dos2Locos/libreseal#compatibility-and-limitations'

/**
 * Shown in place of features whose upstream implementation is only available
 * under the Phase Enterprise License, which LibreSeal does not ship.
 */
export const UnavailableFeature = (props: {
  feature: LibresealFeature
  title?: string
  description?: string
}) => {
  const label = FEATURE_LABELS[props.feature]
  return (
    <div className="w-full space-y-6 text-zinc-900 dark:text-zinc-100">
      {props.title && (
        <div>
          <h2 className="text-base font-medium">{props.title}</h2>
          {props.description && <p className="text-neutral-500 text-sm">{props.description}</p>}
        </div>
      )}
      <EmptyState
        title={`${label} is not available in LibreSeal`}
        subtitle="This feature is only implemented upstream under a proprietary license that LibreSeal does not ship."
        graphic={
          <div className="text-neutral-300 dark:text-neutral-700 text-7xl text-center">
            <FaBan />
          </div>
        }
      >
        <a
          href={UNAVAILABLE_FEATURE_DOCS_URL}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-emerald-600 dark:text-emerald-400 hover:underline"
        >
          Learn about LibreSeal limitations
        </a>
      </EmptyState>
    </div>
  )
}

export const UnavailableBadge = () => (
  <span className="rounded-full border border-neutral-500/40 px-2 py-0.5 text-2xs uppercase tracking-wide text-neutral-500">
    Not available
  </span>
)
