import { useQuery } from '@apollo/client'
import { GetLibresealFeatures } from '@/graphql/queries/libreseal/getLibresealFeatures.gql'
import { DEFAULT_ENABLED_FEATURES, LibresealFeature, isFeatureEnabled } from '@/utils/features'

/** Whether a LibreSeal edition feature is available on this instance. */
export const useFeature = (feature: LibresealFeature): boolean => {
  const { data } = useQuery(GetLibresealFeatures, { fetchPolicy: 'cache-first' })
  return isFeatureEnabled(feature, data?.libresealFeatures ?? DEFAULT_ENABLED_FEATURES)
}
