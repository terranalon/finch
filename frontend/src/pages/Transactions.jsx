import { useState, useEffect, useRef } from 'react'

function Transactions() {
  const [activeTab, setActiveTab] = useState('trades')
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Tab-specific data
  const [trades, setTrades] = useState([])
  const [dividends, setDividends] = useState([])
  const [forex, setForex] = useState([])
  const [cashActivity, setCashActivity] = useState([])

  // Filters
  const [filterAccount, setFilterAccount] = useState('')
  const [filterSymbol, setFilterSymbol] = useState('')

  // Modal state (for adding transactions - kept for future use)
  const [showModal, setShowModal] = useState(false)

  // Track initial mount to avoid duplicate fetches
  const isInitialMount = useRef(true)

  // Initial load - fetch all tabs and accounts
  useEffect(() => {
    fetchAccounts()
    fetchAllTabs()
  }, [])

  // Refetch when filters change (skip initial mount to avoid duplicate fetch)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    fetchAllTabs()
  }, [filterAccount, filterSymbol])

  const fetchAccounts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/accounts')
      if (!response.ok) throw new Error('Failed to fetch accounts')
      const data = await response.json()
      setAccounts(data)
    } catch (err) {
      console.error('Error fetching accounts:', err)
    }
  }

  const fetchAllTabs = async () => {
    setLoading(true)
    setError(null)

    try {
      const buildUrl = (tab) => {
        let url = `http://localhost:8000/api/transactions/${tab}?limit=100`
        if (filterAccount) url += `&account_id=${filterAccount}`
        if (filterSymbol && (tab === 'trades' || tab === 'dividends')) {
          url += `&symbol=${encodeURIComponent(filterSymbol)}`
        }
        return url
      }

      const [tradesRes, dividendsRes, forexRes, cashRes] = await Promise.all([
        fetch(buildUrl('trades')),
        fetch(buildUrl('dividends')),
        fetch(buildUrl('forex')),
        fetch(buildUrl('cash')),
      ])

      if (!tradesRes.ok || !dividendsRes.ok || !forexRes.ok || !cashRes.ok) {
        throw new Error('Failed to fetch transaction data')
      }

      const [tradesData, dividendsData, forexData, cashData] = await Promise.all([
        tradesRes.json(),
        dividendsRes.json(),
        forexRes.json(),
        cashRes.json(),
      ])

      setTrades(tradesData)
      setDividends(dividendsData)
      setForex(forexData)
      setCashActivity(cashData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value, currency = 'USD') => {
    if (value === null || value === undefined) return '-'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(value)
  }

  const formatNumber = (value, decimals = 2) => {
    if (value === null || value === undefined) return '-'
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(value)
  }

  const formatQuantity = (quantity, assetClass) => {
    if (quantity === null || quantity === undefined) return '-'
    if (assetClass === 'Stock' || assetClass === 'ETF') {
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(quantity)
    } else if (assetClass === 'Crypto') {
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 8,
      }).format(quantity)
    }
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    }).format(quantity)
  }

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString()
  }

  const getActionColor = (action) => {
    switch (action) {
      case 'Buy': return 'bg-green-100 text-green-700'
      case 'Sell': return 'bg-red-100 text-red-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  const getTypeColor = (type) => {
    switch (type) {
      case 'Dividend':
      case 'Dividend Cash':
        return 'bg-blue-100 text-blue-700'
      case 'Tax':
        return 'bg-orange-100 text-orange-700'
      case 'Interest':
        return 'bg-purple-100 text-purple-700'
      case 'Deposit':
        return 'bg-green-100 text-green-700'
      case 'Withdrawal':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const tabs = [
    { id: 'trades', label: 'Trades', count: trades.length },
    { id: 'dividends', label: 'Dividends', count: dividends.length },
    { id: 'forex', label: 'Currency Conversions', count: forex.length },
    { id: 'cash', label: 'Cash Activity', count: cashActivity.length },
  ]

  const renderTradesTable = () => (
    <table className="w-full">
      <thead>
        <tr className="border-b">
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Symbol</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Asset Type</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Action</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">Quantity</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">Price</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">Fees</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">Total</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Currency</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Account</th>
        </tr>
      </thead>
      <tbody>
        {trades.map((trade) => (
          <tr key={trade.id} className="border-b hover:bg-gray-50">
            <td className="py-3 px-4 text-gray-700">{formatDate(trade.date)}</td>
            <td className="py-3 px-4">
              <div className="font-mono font-semibold text-primary-600">{trade.symbol}</div>
              <div className="text-xs text-gray-500">{trade.asset_name}</div>
            </td>
            <td className="py-3 px-4">
              <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">
                {trade.asset_class}
              </span>
            </td>
            <td className="py-3 px-4">
              <span className={`text-xs px-2 py-1 rounded ${getActionColor(trade.action)}`}>
                {trade.action}
              </span>
            </td>
            <td className="py-3 px-4 text-right font-mono text-gray-700">
              {formatQuantity(trade.quantity, trade.asset_class)}
            </td>
            <td className="py-3 px-4 text-right text-gray-700">
              {formatCurrency(trade.price_per_unit, trade.currency)}
            </td>
            <td className="py-3 px-4 text-right text-gray-600">
              {formatCurrency(trade.fees, trade.currency)}
            </td>
            <td className="py-3 px-4 text-right font-semibold text-gray-800">
              {formatCurrency(trade.total, trade.currency)}
            </td>
            <td className="py-3 px-4 text-gray-600 font-mono text-sm">
              {trade.currency}
            </td>
            <td className="py-3 px-4 text-gray-600 text-sm">{trade.account_name}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  const renderDividendsTable = () => (
    <table className="w-full">
      <thead>
        <tr className="border-b">
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Symbol</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Type</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">Amount</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Currency</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Account</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Notes</th>
        </tr>
      </thead>
      <tbody>
        {dividends.map((div) => (
          <tr key={div.id} className="border-b hover:bg-gray-50">
            <td className="py-3 px-4 text-gray-700">{formatDate(div.date)}</td>
            <td className="py-3 px-4">
              <div className="font-mono font-semibold text-primary-600">{div.symbol}</div>
              <div className="text-xs text-gray-500">{div.asset_name}</div>
            </td>
            <td className="py-3 px-4">
              <span className={`text-xs px-2 py-1 rounded ${getTypeColor(div.type)}`}>
                {div.type}
              </span>
            </td>
            <td className={`py-3 px-4 text-right font-semibold ${parseFloat(div.amount) < 0 ? 'text-red-600' : 'text-green-600'}`}>
              {formatCurrency(div.amount, div.currency)}
            </td>
            <td className="py-3 px-4 text-gray-600 font-mono text-sm">{div.currency}</td>
            <td className="py-3 px-4 text-gray-600 text-sm">{div.account_name}</td>
            <td className="py-3 px-4 text-gray-500 text-sm max-w-xs truncate">{div.notes || '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  const renderForexTable = () => (
    <table className="w-full">
      <thead>
        <tr className="border-b">
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">From</th>
          <th className="text-center py-3 px-4 font-semibold text-gray-700"></th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">To</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">Rate</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Account</th>
        </tr>
      </thead>
      <tbody>
        {forex.map((fx) => (
          <tr key={fx.id} className="border-b hover:bg-gray-50">
            <td className="py-3 px-4 text-gray-700">{formatDate(fx.date)}</td>
            <td className="py-3 px-4 text-right">
              <span className="font-semibold text-red-600">{formatNumber(fx.from_amount, 2)}</span>
              <span className="ml-1 font-mono text-gray-600">{fx.from_currency}</span>
            </td>
            <td className="py-3 px-4 text-center text-gray-400 text-xl">→</td>
            <td className="py-3 px-4">
              <span className="font-semibold text-green-600">{formatNumber(fx.to_amount, 2)}</span>
              <span className="ml-1 font-mono text-gray-600">{fx.to_currency}</span>
            </td>
            <td className="py-3 px-4 text-right font-mono text-gray-700">
              {formatNumber(fx.exchange_rate, 4)}
            </td>
            <td className="py-3 px-4 text-gray-600 text-sm">{fx.account_name}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  const renderCashTable = () => (
    <table className="w-full">
      <thead>
        <tr className="border-b">
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Type</th>
          <th className="text-right py-3 px-4 font-semibold text-gray-700">Amount</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Currency</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Account</th>
          <th className="text-left py-3 px-4 font-semibold text-gray-700">Notes</th>
        </tr>
      </thead>
      <tbody>
        {cashActivity.map((cash) => (
          <tr key={cash.id} className="border-b hover:bg-gray-50">
            <td className="py-3 px-4 text-gray-700">{formatDate(cash.date)}</td>
            <td className="py-3 px-4">
              <span className={`text-xs px-2 py-1 rounded ${getTypeColor(cash.type)}`}>
                {cash.type}
              </span>
            </td>
            <td className={`py-3 px-4 text-right font-semibold ${parseFloat(cash.amount) < 0 ? 'text-red-600' : 'text-green-600'}`}>
              {formatCurrency(cash.amount, cash.currency)}
            </td>
            <td className="py-3 px-4 text-gray-600 font-mono text-sm">{cash.currency}</td>
            <td className="py-3 px-4 text-gray-600 text-sm">{cash.account_name}</td>
            <td className="py-3 px-4 text-gray-500 text-sm max-w-xs truncate">{cash.notes || '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  const renderTable = () => {
    switch (activeTab) {
      case 'trades':
        return renderTradesTable()
      case 'dividends':
        return renderDividendsTable()
      case 'forex':
        return renderForexTable()
      case 'cash':
        return renderCashTable()
      default:
        return null
    }
  }

  const getCurrentData = () => {
    switch (activeTab) {
      case 'trades': return trades
      case 'dividends': return dividends
      case 'forex': return forex
      case 'cash': return cashActivity
      default: return []
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-primary-700">Transactions</h1>
          <p className="text-gray-600 mt-1">View all portfolio transactions by type</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Add Transaction
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
              {!loading && (
                <span className={`ml-2 py-0.5 px-2 rounded-full text-xs ${
                  activeTab === tab.id
                    ? 'bg-primary-100 text-primary-600'
                    : 'bg-gray-100 text-gray-600'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

          {(activeTab === 'trades' || activeTab === 'dividends') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
              <input
                type="text"
                value={filterSymbol}
                onChange={(e) => setFilterSymbol(e.target.value)}
                placeholder="Filter by symbol..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Error loading transactions</p>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-x-auto">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-lg text-gray-600">Loading {activeTab}...</div>
          </div>
        ) : getCurrentData().length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No {activeTab} found.
          </div>
        ) : (
          renderTable()
        )}
      </div>

      {/* Add Transaction Modal - placeholder for now */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 text-gray-800">Add Transaction</h2>
            <p className="text-gray-600 mb-4">
              Transaction creation form will be available here. For now, use the IBKR import feature.
            </p>
            <button
              onClick={() => setShowModal(false)}
              className="w-full bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Transactions