import { useState, useEffect } from 'react'

import { api } from '../lib/api'

/**
 * Checks whether the current user has any broker accounts.
 * Returns null while loading, then true/false.
 *
 * @param {boolean} fallbackOnError - value to use when the API call fails
 */
export function useHasAccounts(fallbackOnError) {
  const [hasAccounts, setHasAccounts] = useState(null)

  useEffect(() => {
    async function checkAccounts() {
      try {
        const response = await api('/accounts')
        if (response.ok) {
          const data = await response.json()
          setHasAccounts(data.total > 0)
        } else {
          setHasAccounts(fallbackOnError)
        }
      } catch {
        setHasAccounts(fallbackOnError)
      }
    }
    checkAccounts()
  }, [fallbackOnError])

  return hasAccounts
}
