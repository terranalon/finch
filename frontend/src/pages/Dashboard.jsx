import { useState, useEffect, useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import HistoricalPerformanceChart from '../components/HistoricalPerformanceChart'

// Colors for industry pie chart
const INDUSTRY_COLORS = [
  '#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8',
  '#82CA9D', '#FFC658', '#FF7C7C', '#8DD1E1', '#A4DE6C',
  '#D0ED57', '#FFA07A', '#20B2AA', '#778899', '#B0C4DE'
]

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null)
  const [historicalData, setHistoricalData] = useState([])
  const [positions, setPositions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshingPrices, setRefreshingPrices] = useState(false)
  const [creatingSnapshot, setCreatingSnapshot] = useState(false)
  const [displayCurrency, setDisplayCurrency] = useState('USD')

  const currencies = [
    { code: 'USD', name: 'US Dollar', symbol: '$' },
    { code: 'ILS', name: 'Israeli Shekel', symbol: '₪' },
    { code: 'CAD', name: 'Canadian Dollar', symbol: 'CA$' },
    { code: 'EUR', name: 'Euro', symbol: '€' },
    { code: 'GBP', name: 'British Pound', symbol: '£' },
  ]

  useEffect(() => {
    fetchDashboardData()
    fetchHistoricalSnapshots()
    fetchPositions()
  }, [displayCurrency])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const response = await fetch(`http://localhost:8000/api/dashboard/summary?display_currency=${displayCurrency}`)
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data')
      }
      const data = await response.json()
      setDashboardData(data)
      setError(null)
    } catch (err) {
      setError(err.message)
      console.error('Error fetching dashboard data:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchHistoricalSnapshots = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/snapshots/portfolio?limit=90&display_currency=${displayCurrency}`)
      if (!response.ok) throw new Error('Failed to fetch historical snapshots')
      const data = await response.json()
      // Reverse to show oldest to newest
      setHistoricalData(data.reverse())
    } catch (err) {
      console.error('Error fetching historical snapshots:', err)
    }
  }

  const fetchPositions = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/positions?display_currency=${displayCurrency}`)
      if (!response.ok) throw new Error('Failed to fetch positions')
      const data = await response.json()
      // Filter out zero-quantity positions
      setPositions(data.filter(p => p.total_quantity !== 0))
    } catch (err) {
      console.error('Error fetching positions:', err)
    }
  }

  // Compute industry allocation data for pie chart (excludes ETFs)
  const industryAllocationData = useMemo(() => {
    const industryMap = {}
    positions.forEach(position => {
      // Only include positions with industry data (excludes ETFs, Cash, etc.)
      if (position.total_market_value && position.total_market_value > 0 && position.industry) {
        if (!industryMap[position.industry]) {
          industryMap[position.industry] = 0
        }
        industryMap[position.industry] += position.total_market_value
      }
    })

    // Convert to array and sort by value descending
    return Object.entries(industryMap)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [positions])

  // Calculate total market value for industry percentages
  const totalIndustryValue = useMemo(() => {
    return industryAllocationData.reduce((sum, item) => sum + item.value, 0)
  }, [industryAllocationData])

  const handleRefreshPrices = async () => {
    try {
      setRefreshingPrices(true)
      const response = await fetch('http://localhost:8000/api/prices/update', {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to refresh prices')
      const data = await response.json()
      alert(`Prices updated! ${data.stats.updated} assets updated, ${data.stats.failed} failed.`)
      // Refresh dashboard data to show new prices
      await fetchDashboardData()
    } catch (err) {
      alert('Error refreshing prices: ' + err.message)
    } finally {
      setRefreshingPrices(false)
    }
  }

  const handleCreateSnapshot = async () => {
    try {
      setCreatingSnapshot(true)
      const response = await fetch('http://localhost:8000/api/snapshots/create', {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to create snapshot')
      const data = await response.json()
      alert(`Snapshot created! ${data.snapshots_created} accounts captured.`)
      // Refresh dashboard to show new snapshot
      await fetchDashboardData()
      await fetchHistoricalSnapshots()
    } catch (err) {
      alert('Error creating snapshot: ' + err.message)
    } finally {
      setCreatingSnapshot(false)
    }
  }

  const formatCurrency = (value, currency = null) => {
    const currencyCode = currency || displayCurrency
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatNumber = (value) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8,
    }).format(value)
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg text-gray-600">Loading dashboard...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">Error loading dashboard</p>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-primary-700">Portfolio Dashboard</h1>
        <div className="flex space-x-3 items-center">
          {/* Currency Selector */}
          <div className="flex items-center space-x-2">
            <label htmlFor="currency-selector" className="text-sm font-medium text-gray-700">
              Currency:
            </label>
            <select
              id="currency-selector"
              value={displayCurrency}
              onChange={(e) => setDisplayCurrency(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {currencies.map((currency) => (
                <option key={currency.code} value={currency.code}>
                  {currency.symbol} {currency.code}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRefreshPrices}
            disabled={refreshingPrices}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {refreshingPrices ? 'Refreshing...' : '🔄 Refresh Prices'}
          </button>
          <button
            onClick={handleCreateSnapshot}
            disabled={creatingSnapshot}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:bg-green-300 disabled:cursor-not-allowed"
          >
            {creatingSnapshot ? 'Creating...' : '📸 Create Snapshot'}
          </button>
        </div>
      </div>

      {/* Total Portfolio Value */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="card bg-gradient-to-br from-primary-500 to-primary-600 text-white">
          <h2 className="text-lg font-semibold mb-2 opacity-90">Total Portfolio Value</h2>
          <p className="text-4xl font-bold">{formatCurrency(dashboardData.total_value)}</p>
          <p className="text-sm opacity-90 mt-1">in {displayCurrency}</p>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4 text-gray-700">Quick Stats</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Accounts:</span>
              <span className="font-semibold">{dashboardData.accounts.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Active Holdings:</span>
              <span className="font-semibold">{dashboardData.top_holdings.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Asset Classes:</span>
              <span className="font-semibold">{dashboardData.asset_allocation.length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Portfolio Performance Chart - Enhanced */}
      <div className="mb-6">
        <HistoricalPerformanceChart displayCurrency={displayCurrency} />
      </div>

      {/* Accounts Breakdown */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Accounts</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {dashboardData.accounts.map((account) => (
            <div key={account.id} className="card hover:shadow-lg transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-gray-800">{account.name}</h3>
                <span className="text-xs bg-primary-100 text-primary-700 px-2 py-1 rounded">
                  {account.type}
                </span>
              </div>
              {account.institution && (
                <p className="text-sm text-gray-500 mb-3">{account.institution}</p>
              )}
              <div className="border-t pt-3">
                <p className="text-2xl font-bold text-gray-800">
                  {formatCurrency(account.value)}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Asset Allocation */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Asset Allocation</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Pie Chart */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 text-gray-700">By Asset Class</h3>
            {dashboardData.asset_allocation.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={dashboardData.asset_allocation}
                    dataKey="total_value"
                    nameKey="asset_class"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ asset_class, percent }) => `${asset_class} ${(percent * 100).toFixed(0)}%`}
                  >
                    {dashboardData.asset_allocation.map((entry, index) => {
                      const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
                      return <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                    })}
                  </Pie>
                  <Tooltip
                    formatter={(value) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '0.5rem',
                      padding: '0.75rem'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-12 text-gray-500">
                No allocation data available
              </div>
            )}
          </div>

          {/* Allocation Details */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 text-gray-700">Breakdown</h3>
            <div className="space-y-3">
              {dashboardData.asset_allocation.map((allocation, index) => {
                const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
                const total = dashboardData.asset_allocation.reduce((sum, a) => sum + parseFloat(a.total_value), 0)
                const percentage = (parseFloat(allocation.total_value) / total * 100).toFixed(1)

                return (
                  <div key={allocation.asset_class} className="border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colors[index % colors.length] }}></div>
                        <h4 className="font-semibold text-gray-700">{allocation.asset_class}</h4>
                      </div>
                      <span className="text-sm font-medium text-gray-600">{percentage}%</span>
                    </div>
                    <p className="text-xl font-bold text-primary-600">
                      {formatCurrency(allocation.total_value)}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {allocation.holding_count} {allocation.holding_count === 1 ? 'holding' : 'holdings'}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Industry Allocation */}
      {industryAllocationData.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Industry Allocation</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pie Chart */}
            <div className="card">
              <h3 className="text-lg font-semibold mb-4 text-gray-700">By Industry</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={industryAllocationData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ percent }) => percent > 0.03 ? `${(percent * 100).toFixed(0)}%` : ''}
                  >
                    {industryAllocationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={INDUSTRY_COLORS[index % INDUSTRY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '0.5rem',
                      padding: '0.75rem'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Industry Breakdown */}
            <div className="card">
              <h3 className="text-lg font-semibold mb-4 text-gray-700">Breakdown</h3>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {industryAllocationData.map((item, index) => {
                  const percentage = ((item.value / totalIndustryValue) * 100).toFixed(1)
                  return (
                    <div key={item.name} className="flex items-center justify-between p-2 border rounded-lg">
                      <div className="flex items-center space-x-2 min-w-0">
                        <div
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: INDUSTRY_COLORS[index % INDUSTRY_COLORS.length] }}
                        />
                        <span className="text-sm text-gray-700 truncate">{item.name}</span>
                      </div>
                      <div className="flex items-center space-x-3 flex-shrink-0">
                        <span className="font-semibold text-gray-800">{formatCurrency(item.value)}</span>
                        <span className="text-sm text-gray-500">{percentage}%</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top Holdings */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Top 10 Holdings by Value</h2>
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Symbol</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Name</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Type</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Account</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Quantity</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Cost Basis</th>
              </tr>
            </thead>
            <tbody>
              {dashboardData.top_holdings.slice(0, 10).map((holding) => (
                <tr key={holding.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 font-mono font-semibold text-primary-600">
                    {holding.symbol}
                  </td>
                  <td className="py-3 px-4 text-gray-800">{holding.name}</td>
                  <td className="py-3 px-4">
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                      {holding.asset_class}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600 text-sm">{holding.account_name}</td>
                  <td className="py-3 px-4 text-right font-mono text-gray-700">
                    {formatNumber(holding.quantity)}
                  </td>
                  <td className="py-3 px-4 text-right font-semibold text-gray-800">
                    {formatCurrency(holding.cost_basis)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Dashboard