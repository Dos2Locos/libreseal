import { LIBRESEAL_REPO_URL, LIBRESEAL_UPSTREAM_URL } from '@/utils/links'

/** Identifies LibreSeal as an independent fork with no affiliation to Phase. */
export const ForkNotice = () => (
  <p className="text-neutral-500 text-xs max-w-md" data-testid="fork-notice">
    <a href={LIBRESEAL_REPO_URL} target="_blank" rel="noreferrer" className="font-medium hover:underline">
      LibreSeal
    </a>{' '}
    is an independent community fork of{' '}
    <a href={LIBRESEAL_UPSTREAM_URL} target="_blank" rel="noreferrer" className="hover:underline">
      Phase Console
    </a>
    . It is not affiliated with or endorsed by Phase or Phi Security Inc.
  </p>
)
