import { useQuery } from '@tanstack/react-query'

import { api } from '../lib/api'

/**
 * Checks whether the current user has any broker accounts.
 * Returns null while loading, then true/false.
 *
 * @param {boolean} fallbackOnError - value to use when the API call fails
 */
export function useHasAccounts(fallbackOnError) {
  const { data, isPending, isError } = useQuery({
    queryKey: ['accounts', 'hasAny'],
    queryFn: async () => {
      const response = await api('/accounts')
      if (!response.ok) throw new Error('Failed to fetch accounts')
      const json = await response.json()
      return json.total > 0
    },
    staleTime: 30000,
    retry: false,
  })

  if (isPending) return null
  if (isError) return fallbackOnError
  return data
}
