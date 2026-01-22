import { useState, useEffect, useMemo } from 'react'

function Positions() {
  const [positions, setPositions] = useState([])
  const [accounts, setAccounts] = useState([])
  const [expandedRows, setExpandedRows] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshingPrices, setRefreshingPrices] = useState(false)

  // Filters
  const [filterAccount, setFilterAccount] = useState('')
  const [filterAssetClass, setFilterAssetClass] = useState('')
  const [filterStrategy, setFilterStrategy] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterIndustry, setFilterIndustry] = useState('')

  // Sorting
  const [sortField, setSortField] = useState('total_market_value')
  const [sortDirection, setSortDirection] = useState('desc')

  // Edit modal state
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingHolding, setEditingHolding] = useState(null)
  const [editingSymbol, setEditingSymbol] = useState('')
  const [editFormData, setEditFormData] = useState({
    quantity: '',
    cost_basis: '',
    strategy_horizon: ''
  })

  useEffect(() => {
    fetchPositions()
    fetchAccounts()
  }, [])

  const fetchPositions = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:8000/api/positions')
      if (!response.ok) throw new Error('Failed to fetch positions')
      const data = await response.json()
      // Filter out zero-quantity positions
      const filteredData = data.filter(p => p.total_quantity !== 0)
      setPositions(filteredData)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchAccounts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/accounts?is_active=true')
      if (!response.ok) throw new Error('Failed to fetch accounts')
      const data = await response.json()
      setAccounts(data)
    } catch (err) {
      console.error('Error fetching accounts:', err)
    }
  }

  const toggleRow = (assetId) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(assetId)) {
      newExpanded.delete(assetId)
    } else {
      newExpanded.add(assetId)
    }
    setExpandedRows(newExpanded)
  }

  const handleRefreshPrices = async () => {
    try {
      setRefreshingPrices(true)
      const response = await fetch('http://localhost:8000/api/prices/update', {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to refresh prices')
      const data = await response.json()
      alert(`Prices updated! ${data.stats.updated} assets updated, ${data.stats.failed} failed.`)
      await fetchPositions()
    } catch (err) {
      alert('Error refreshing prices: ' + err.message)
    } finally {
      setRefreshingPrices(false)
    }
  }

  const handleEditClick = (account, symbol) => {
    setEditingHolding(account)
    setEditingSymbol(symbol)
    setEditFormData({
      quantity: account.quantity,
      cost_basis: account.cost_basis,
      strategy_horizon: account.strategy_horizon || ''
    })
    setShowEditModal(true)
  }

  const handleEditSubmit = async (e) => {
    e.preventDefault()

    try {
      const response = await fetch(
        `http://localhost:8000/api/holdings/${editingHolding.holding_id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            quantity: parseFloat(editFormData.quantity),
            cost_basis: parseFloat(editFormData.cost_basis),
            strategy_horizon: editFormData.strategy_horizon || null
          })
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update holding')
      }

      setShowEditModal(false)
      setEditingHolding(null)
      await fetchPositions()
    } catch (err) {
      alert(`Error updating holding: ${err.message}`)
    }
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  // Filter and sort positions
  const filteredAndSortedPositions = useMemo(() => {
    let result = positions.filter(position => {
      // Account filter - check if any account in the position matches
      if (filterAccount) {
        const hasMatchingAccount = position.accounts.some(
          acc => acc.account_id === parseInt(filterAccount)
        )
        if (!hasMatchingAccount) return false
      }

      // Asset class filter
      if (filterAssetClass && position.asset_class !== filterAssetClass) {
        return false
      }

      // Strategy filter - check if any account has matching strategy
      if (filterStrategy) {
        const hasMatchingStrategy = position.accounts.some(
          acc => acc.strategy_horizon === filterStrategy
        )
        if (!hasMatchingStrategy) return false
      }

      // Category filter
      if (filterCategory && position.category !== filterCategory) {
        return false
      }

      // Industry filter
      if (filterIndustry && position.industry !== filterIndustry) {
        return false
      }

      return true
    })

    // If account filter is active, also filter the accounts array within each position
    if (filterAccount) {
      result = result.map(position => {
        const filteredAccounts = position.accounts.filter(
          acc => acc.account_id === parseInt(filterAccount)
        )
        // Recalculate totals based on filtered accounts
        const totalQuantity = filteredAccounts.reduce((sum, acc) => sum + acc.quantity, 0)
        const totalCostBasis = filteredAccounts.reduce((sum, acc) => sum + acc.cost_basis, 0)
        const totalMarketValue = filteredAccounts.reduce((sum, acc) => sum + (acc.market_value || 0), 0)
        const totalPnl = filteredAccounts.reduce((sum, acc) => sum + (acc.pnl || 0), 0)
        const totalPnlPct = totalCostBasis > 0 ? (totalPnl / totalCostBasis) * 100 : null

        return {
          ...position,
          accounts: filteredAccounts,
          account_count: filteredAccounts.length,
          total_quantity: totalQuantity,
          total_cost_basis: totalCostBasis,
          total_market_value: position.current_price ? totalMarketValue : null,
          total_pnl: position.current_price ? totalPnl : null,
          total_pnl_pct: totalPnlPct
        }
      })
    }

    // Sort
    result.sort((a, b) => {
      let aVal = a[sortField]
      let bVal = b[sortField]

      // Handle null values - sort to end
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1

      // String comparison for text fields
      if (typeof aVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      // Numeric comparison
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })

    return result
  }, [positions, filterAccount, filterAssetClass, filterStrategy, filterCategory, filterIndustry, sortField, sortDirection])

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value)
  }

  const formatQuantity = (quantity, assetClass) => {
    if (assetClass === 'Stock' || assetClass === 'ETF') {
      // Stocks/ETFs: show as integers
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(quantity)
    } else if (assetClass === 'Cash') {
      // Cash: 2 decimal places
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(quantity)
    } else if (assetClass === 'Crypto') {
      // Crypto: up to 8 decimals
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 8,
      }).format(quantity)
    }
    // Default: up to 4 decimals
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    }).format(quantity)
  }

  // Get unique categories and industries for filter dropdowns
  const uniqueCategories = useMemo(() => {
    const categories = new Set()
    positions.forEach(p => {
      if (p.category) categories.add(p.category)
    })
    return Array.from(categories).sort()
  }, [positions])

  const uniqueIndustries = useMemo(() => {
    const industries = new Set()
    positions.forEach(p => {
      if (p.industry) industries.add(p.industry)
    })
    return Array.from(industries).sort()
  }, [positions])

  const SortableHeader = ({ field, label, align = 'left' }) => {
    const isActive = sortField === field
    const alignClass = align === 'right' ? 'text-right justify-end' : 'text-left justify-start'

    return (
      <th
        className={`py-3 px-4 font-semibold text-gray-700 cursor-pointer hover:bg-gray-50 ${align === 'right' ? 'text-right' : 'text-left'}`}
        onClick={() => handleSort(field)}
      >
        <div className={`flex items-center gap-1 ${alignClass}`}>
          {label}
          <span className="text-gray-400 text-xs">
            {isActive ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
          </span>
        </div>
      </th>
    )
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg text-gray-600">Loading holdings...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold text-primary-700">Holdings</h1>
          <p className="text-gray-600 mt-2">
            Aggregated view of your holdings across all accounts. Click any row to see account breakdown.
          </p>
        </div>
        <button
          onClick={handleRefreshPrices}
          disabled={refreshingPrices}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
        >
          {refreshingPrices ? 'Refreshing...' : 'Refresh Prices'}
        </button>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-4 text-gray-700">Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Account</label>
            <select
              value={filterAccount}
              onChange={(e) => setFilterAccount(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Accounts</option>
              {accounts.map(account => (
                <option key={account.id} value={account.id}>{account.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Asset Class</label>
            <select
              value={filterAssetClass}
              onChange={(e) => setFilterAssetClass(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Classes</option>
              <option value="Stock">Stock</option>
              <option value="ETF">ETF</option>
              <option value="Bond">Bond</option>
              <option value="Cash">Cash</option>
              <option value="Crypto">Crypto</option>
              <option value="Commodity">Commodity</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Strategy</label>
            <select
              value={filterStrategy}
              onChange={(e) => setFilterStrategy(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Strategies</option>
              <option value="ShortTerm">Short Term</option>
              <option value="MediumTerm">Medium Term</option>
              <option value="LongTerm">Long Term</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              {uniqueCategories.map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
            <select
              value={filterIndustry}
              onChange={(e) => setFilterIndustry(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Industries</option>
              {uniqueIndustries.map(industry => (
                <option key={industry} value={industry}>{industry}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Error loading holdings</p>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left py-3 px-4 font-semibold text-gray-700 w-8"></th>
              <SortableHeader field="symbol" label="Symbol" />
              <SortableHeader field="name" label="Asset" />
              <SortableHeader field="asset_class" label="Class" />
              <SortableHeader field="current_price_display" label="Current Price" align="right" />
              <SortableHeader field="total_quantity" label="Quantity" align="right" />
              <SortableHeader field="total_cost_basis" label="Cost Basis" align="right" />
              <SortableHeader field="total_market_value" label="Market Value" align="right" />
              <SortableHeader field="total_pnl" label="P&L" align="right" />
              <SortableHeader field="total_pnl_pct" label="P&L %" align="right" />
              <th className="text-center py-3 px-4 font-semibold text-gray-700">Accounts</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedPositions.map((position) => (
              <>
                <tr
                  key={position.asset_id}
                  className="border-b hover:bg-gray-50 cursor-pointer"
                  onClick={() => toggleRow(position.asset_id)}
                >
                  <td className="py-3 px-4">
                    <span className="text-gray-400">
                      {expandedRows.has(position.asset_id) ? '▼' : '▶'}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono font-semibold text-primary-600">
                    {position.symbol}
                  </td>
                  <td className="py-3 px-4">
                    <div>
                      <div className="font-medium text-gray-800">{position.name}</div>
                      {(position.category || position.industry) && (
                        <div className="text-xs text-gray-500">
                          {position.category}{position.category && position.industry ? ' / ' : ''}{position.industry}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                      {position.asset_class}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-gray-700">
                    {position.current_price_display !== null ? formatCurrency(position.current_price_display) : '-'}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-gray-700">
                    {formatQuantity(position.total_quantity, position.asset_class)}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-800">
                    {formatCurrency(position.total_cost_basis)}
                  </td>
                  <td className="py-3 px-4 text-right font-semibold text-gray-800">
                    {position.total_market_value !== null ? formatCurrency(position.total_market_value) : '-'}
                  </td>
                  <td className={'py-3 px-4 text-right font-semibold ' + (position.total_pnl !== null ? (position.total_pnl >= 0 ? 'text-green-600' : 'text-red-600') : 'text-gray-500')}>
                    {position.total_pnl !== null ? formatCurrency(position.total_pnl) : '-'}
                  </td>
                  <td className={'py-3 px-4 text-right font-semibold ' + (position.total_pnl_pct !== null ? (position.total_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600') : 'text-gray-500')}>
                    {position.total_pnl_pct !== null ? `${position.total_pnl_pct >= 0 ? '+' : ''}${position.total_pnl_pct.toFixed(2)}%` : '-'}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="text-xs bg-primary-100 text-primary-700 px-2 py-1 rounded">
                      {position.account_count}
                    </span>
                  </td>
                </tr>

                {expandedRows.has(position.asset_id) && (
                  <tr key={`${position.asset_id}-expanded`}>
                    <td colSpan="11" className="bg-gray-50 p-0">
                      <div className="px-12 py-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-3">
                          Account Breakdown:
                        </h4>
                        <table className="w-full">
                          <thead>
                            <tr className="text-xs text-gray-600">
                              <th className="text-left pb-2">Account</th>
                              <th className="text-left pb-2">Type</th>
                              <th className="text-right pb-2">Quantity</th>
                              <th className="text-right pb-2">Cost Basis</th>
                              <th className="text-right pb-2">Market Value</th>
                              <th className="text-right pb-2">P&L</th>
                              <th className="text-right pb-2">P&L %</th>
                              <th className="text-left pb-2">Strategy</th>
                              <th className="text-center pb-2">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {position.accounts.map((account, idx) => (
                              <tr key={idx} className="text-sm border-t border-gray-200">
                                <td className="py-2">
                                  <div className="font-medium text-gray-800">
                                    {account.account_name}
                                  </div>
                                  {account.institution && (
                                    <div className="text-xs text-gray-500">
                                      {account.institution}
                                    </div>
                                  )}
                                </td>
                                <td className="py-2">
                                  <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                                    {account.account_type}
                                  </span>
                                </td>
                                <td className="py-2 text-right font-mono text-gray-700">
                                  {formatQuantity(account.quantity, position.asset_class)}
                                </td>
                                <td className="py-2 text-right text-gray-800">
                                  {formatCurrency(account.cost_basis)}
                                </td>
                                <td className="py-2 text-right font-semibold text-gray-800">
                                  {account.market_value !== null ? formatCurrency(account.market_value) : '-'}
                                </td>
                                <td className={'py-2 text-right font-semibold ' + (account.pnl !== null ? (account.pnl >= 0 ? 'text-green-600' : 'text-red-600') : 'text-gray-500')}>
                                  {account.pnl !== null ? formatCurrency(account.pnl) : '-'}
                                </td>
                                <td className={'py-2 text-right font-semibold ' + (account.pnl_pct !== null ? (account.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600') : 'text-gray-500')}>
                                  {account.pnl_pct !== null ? `${account.pnl_pct >= 0 ? '+' : ''}${account.pnl_pct.toFixed(2)}%` : '-'}
                                </td>
                                <td className="py-2 text-gray-600">
                                  {account.strategy_horizon || '-'}
                                </td>
                                <td className="py-2 text-center">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleEditClick(account, position.symbol)
                                    }}
                                    className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                                  >
                                    Edit
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>

        {filteredAndSortedPositions.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No holdings found matching your filters.
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {showEditModal && editingHolding && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold mb-2 text-gray-800">
              Edit Holding
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              {editingSymbol} in {editingHolding.account_name}
            </p>

            <form onSubmit={handleEditSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity
                </label>
                <input
                  type="number"
                  step="0.00000001"
                  required
                  value={editFormData.quantity}
                  onChange={(e) => setEditFormData({ ...editFormData, quantity: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="0.00"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cost Basis
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={editFormData.cost_basis}
                  onChange={(e) => setEditFormData({ ...editFormData, cost_basis: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="0.00"
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Strategy Horizon
                </label>
                <select
                  value={editFormData.strategy_horizon}
                  onChange={(e) => setEditFormData({ ...editFormData, strategy_horizon: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">None</option>
                  <option value="ShortTerm">Short Term</option>
                  <option value="MediumTerm">Medium Term</option>
                  <option value="LongTerm">Long Term</option>
                </select>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false)
                    setEditingHolding(null)
                  }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Positions
