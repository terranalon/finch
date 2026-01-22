import { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'

/**
 * Historical Performance Chart Component
 *
 * Displays portfolio value over time using historical snapshots.
 * Features:
 * - Time range selector (7D, 30D, 90D, 1Y, ALL)
 * - Chart type toggle (Line, Area)
 * - Currency selection
 * - Performance metrics (total return, % change)
 */
function HistoricalPerformanceChart({ accountId = null, displayCurrency = 'USD' }) {
  const [snapshots, setSnapshots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timeRange, setTimeRange] = useState('90D') // 7D, 30D, 90D, 1Y, ALL
  const [chartType, setChartType] = useState('area') // line, area

  const currencies = {
    USD: { symbol: '$', name: 'US Dollar' },
    ILS: { symbol: '₪', name: 'Israeli Shekel' },
    CAD: { symbol: 'CA$', name: 'Canadian Dollar' },
    EUR: { symbol: '€', name: 'Euro' },
    GBP: { symbol: '£', name: 'British Pound' },
  }

  useEffect(() => {
    fetchSnapshots()
  }, [accountId, displayCurrency, timeRange])

  const fetchSnapshots = async () => {
    try {
      setLoading(true)

      // Calculate date range based on selected time range
      const endDate = new Date()
      const startDate = new Date()

      switch (timeRange) {
        case '7D':
          startDate.setDate(endDate.getDate() - 7)
          break
        case '30D':
          startDate.setDate(endDate.getDate() - 30)
          break
        case '90D':
          startDate.setDate(endDate.getDate() - 90)
          break
        case '1Y':
          startDate.setFullYear(endDate.getFullYear() - 1)
          break
        case 'ALL':
          // Don't set start_date to get all snapshots
          break
      }

      const params = new URLSearchParams({
        display_currency: displayCurrency,
        limit: timeRange === 'ALL' ? 1000 : 365,
      })

      if (timeRange !== 'ALL') {
        params.append('start_date', startDate.toISOString().split('T')[0])
      }

      const endpoint = accountId
        ? `http://localhost:8000/api/snapshots/account/${accountId}?${params}`
        : `http://localhost:8000/api/snapshots/portfolio?${params}`

      const response = await fetch(endpoint)
      if (!response.ok) throw new Error('Failed to fetch snapshots')

      const data = await response.json()

      // Sort by date (oldest to newest) for proper chart display
      const sortedData = data.sort((a, b) => new Date(a.date) - new Date(b.date))

      setSnapshots(sortedData)
      setError(null)
    } catch (err) {
      console.error('Error fetching snapshots:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Calculate performance metrics
  const calculateMetrics = () => {
    if (snapshots.length < 2) return null

    const firstSnapshot = snapshots[0]
    const lastSnapshot = snapshots[snapshots.length - 1]

    const initialValue = firstSnapshot.value
    const currentValue = lastSnapshot.value
    const absoluteChange = currentValue - initialValue
    const percentChange = ((currentValue - initialValue) / initialValue) * 100

    return {
      initialValue,
      currentValue,
      absoluteChange,
      percentChange,
      startDate: firstSnapshot.date,
      endDate: lastSnapshot.date,
      dataPoints: snapshots.length
    }
  }

  const metrics = calculateMetrics()

  const formatCurrency = (value) => {
    const symbol = currencies[displayCurrency]?.symbol || '$'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: displayCurrency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    if (timeRange === '7D') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } else if (timeRange === '30D' || timeRange === '90D') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
    }
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const value = payload[0].value
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-700">
            {new Date(label).toLocaleDateString('en-US', {
              month: 'long',
              day: 'numeric',
              year: 'numeric'
            })}
          </p>
          <p className="text-lg font-bold text-primary-600 mt-1">
            {formatCurrency(value)}
          </p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading historical data...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">Error loading chart</p>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  if (snapshots.length === 0) {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Portfolio Performance</h2>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">No historical data available for the selected time range.</p>
          <p className="text-yellow-700 text-sm mt-1">
            Snapshots are created daily. Check back after the next scheduled run.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      {/* Header with controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-700">Portfolio Performance</h2>
          <p className="text-sm text-gray-500 mt-1">{snapshots.length} data points</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {/* Time Range Selector */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            {['7D', '30D', '90D', '1Y', 'ALL'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  timeRange === range
                    ? 'bg-white text-primary-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {range}
              </button>
            ))}
          </div>

          {/* Chart Type Toggle */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setChartType('line')}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                chartType === 'line'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Line
            </button>
            <button
              onClick={() => setChartType('area')}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                chartType === 'area'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Area
            </button>
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 mb-1">Starting Value</p>
            <p className="text-lg font-semibold text-gray-900">
              {formatCurrency(metrics.initialValue)}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 mb-1">Current Value</p>
            <p className="text-lg font-semibold text-gray-900">
              {formatCurrency(metrics.currentValue)}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 mb-1">Total Change</p>
            <p className={`text-lg font-semibold ${
              metrics.absoluteChange >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {metrics.absoluteChange >= 0 ? '+' : ''}{formatCurrency(metrics.absoluteChange)}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600 mb-1">Percent Change</p>
            <p className={`text-lg font-semibold ${
              metrics.percentChange >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {metrics.percentChange >= 0 ? '+' : ''}{metrics.percentChange.toFixed(2)}%
            </p>
          </div>
        </div>
      )}

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        {chartType === 'area' ? (
          <AreaChart data={snapshots} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              tick={{ fontSize: 12 }}
              tickFormatter={formatDate}
              minTickGap={30}
            />
            <YAxis
              stroke="#6b7280"
              tick={{ fontSize: 12 }}
              domain={[
                dataMin => dataMin * 0.995,
                dataMax => dataMax * 1.005
              ]}
              tickFormatter={(value) => {
                const symbol = currencies[displayCurrency]?.symbol || '$'
                if (value >= 1000000) {
                  return `${symbol}${(value / 1000000).toFixed(1)}M`
                } else if (value >= 1000) {
                  return `${symbol}${(value / 1000).toFixed(0)}k`
                }
                return `${symbol}${value}`
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorValue)"
            />
          </AreaChart>
        ) : (
          <LineChart data={snapshots} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              tick={{ fontSize: 12 }}
              tickFormatter={formatDate}
              minTickGap={30}
            />
            <YAxis
              stroke="#6b7280"
              tick={{ fontSize: 12 }}
              domain={[
                dataMin => dataMin * 0.995,
                dataMax => dataMax * 1.005
              ]}
              tickFormatter={(value) => {
                const symbol = currencies[displayCurrency]?.symbol || '$'
                if (value >= 1000000) {
                  return `${symbol}${(value / 1000000).toFixed(1)}M`
                } else if (value >= 1000) {
                  return `${symbol}${(value / 1000).toFixed(0)}k`
                }
                return `${symbol}${value}`
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        )}
      </ResponsiveContainer>

      {/* Data Info */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center text-sm text-gray-600">
          <span>
            {new Date(snapshots[0].date).toLocaleDateString()} - {new Date(snapshots[snapshots.length - 1].date).toLocaleDateString()}
          </span>
          <span>
            {snapshots.length} days of data
          </span>
        </div>
      </div>
    </div>
  )
}

export default HistoricalPerformanceChart
