import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider, CurrencyProvider, AuthProvider, PortfolioProvider, useAuth } from './contexts'
import { Navbar } from './components/layout'
import ProtectedRoute from './components/ProtectedRoute'

// Pages
import Overview from './pages/Overview'
import Holdings from './pages/Holdings'
import Activity from './pages/Activity'
import Accounts from './pages/Accounts'
import AccountDetail from './pages/AccountDetail'
import Insights from './pages/Insights'
import Assets from './pages/Assets'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Register from './pages/Register'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      refetchOnWindowFocus: false,
    },
  },
})

// Redirect authenticated users away from auth pages
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

// Main app layout with navbar
function AppLayout({ children }) {
  return (
    <div className="min-h-dvh bg-[var(--bg-primary)]">
      <Navbar />
      {children}
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <CurrencyProvider>
          <AuthProvider>
            <PortfolioProvider>
              <Router>
              <Routes>
                {/* Public routes (redirect to home if authenticated) */}
                <Route path="/login" element={
                  <PublicRoute><Login /></PublicRoute>
                } />
                <Route path="/register" element={
                  <PublicRoute><Register /></PublicRoute>
                } />

                {/* Protected routes */}
                <Route path="/" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Overview />
                    </AppLayout>
                  </ProtectedRoute>
                } />
                <Route path="/holdings" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Holdings />
                    </AppLayout>
                  </ProtectedRoute>
                } />
                <Route path="/activity" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Activity />
                    </AppLayout>
                  </ProtectedRoute>
                } />
                <Route path="/insights" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Insights />
                    </AppLayout>
                  </ProtectedRoute>
                } />
                <Route path="/assets" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Assets />
                    </AppLayout>
                  </ProtectedRoute>
                } />
                <Route path="/accounts" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Accounts />
                    </AppLayout>
                  </ProtectedRoute>
                } />
                <Route path="/accounts/:id" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <AccountDetail />
                    </AppLayout>
                  </ProtectedRoute>
                } />
                <Route path="/settings" element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Settings />
                    </AppLayout>
                  </ProtectedRoute>
                } />

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Router>
            </PortfolioProvider>
          </AuthProvider>
        </CurrencyProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
