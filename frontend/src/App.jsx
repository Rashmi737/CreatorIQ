import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import apiClient from './apiClient'
import useAuthStore from './store/authStore'
import { AudiencePage, ContentPage, Layout, RevenuePage, OverviewPage, SocialMediaPage, TrendsPage } from './pages'
import ErrorBoundary from './components/ErrorBoundary'
import AuthPage from './AuthPage'

function WelcomePage({ user }) {
  const [step, setStep] = useState(1)

  return (
    <main className="auth-page welcome-page">
      <div className="auth-glow" />
      <section className="auth-panel welcome-panel">
        <div className="welcome-header">
          <div className="brand-mark large">C</div>
          <h1>Welcome to CreatorIQ, {user.display_name}!</h1>
          <p className="muted">Let's set up your workspace to start analyzing your content performance.</p>
        </div>

        <div className="onboarding-steps">
          <div className={`step ${step >= 1 ? 'active' : ''}`}>
            <div className="step-number">1</div>
            <div className="step-content">
              <h3>Connect Your Primary Account</h3>
              <p>Link YouTube, LinkedIn, Instagram, GitHub, Facebook, or X (Twitter) to start tracking your content performance.</p>
              {step === 1 && (
                <div className="step-actions">
                  <button className="primary-button" onClick={() => setStep(2)}>
                    Next: Choose Content Niche
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className={`step ${step >= 2 ? 'active' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-content">
              <h3>Select Your Content Niche</h3>
              <p>Help us personalize your analytics dashboard by choosing your primary content category.</p>
              {step === 2 && (
                <div className="step-actions">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', marginBottom: '16px' }}>
                    {['Gaming', 'Music', 'Comedy', 'Education', 'Lifestyle', 'Business'].map((niche) => (
                      <button key={niche} className="niche-button" type="button">
                        {niche}
                      </button>
                    ))}
                  </div>
                  <button className="primary-button" onClick={() => setStep(3)}>
                    Next: Go to Dashboard
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className={`step ${step >= 3 ? 'active' : ''}`}>
            <div className="step-number">3</div>
            <div className="step-content">
              <h3>All Set!</h3>
              <p>Your workspace is ready. Head to the dashboard to start tracking your creator metrics.</p>
              {step === 3 && (
                <div className="step-actions">
                  <a href="/dashboard" className="primary-button" style={{ textDecoration: 'none', display: 'inline-block' }}>
                    Go to Dashboard
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="onboarding-progress">
          <div className="progress-bar" style={{ width: `${(step / 3) * 100}%` }} />
        </div>
      </section>
    </main>
  )
}

function App() {
  const { user, token, setSession, clearSession } = useAuthStore()
  const [isCheckingAuth, setIsCheckingAuth] = useState(Boolean(token && !user))
  const [toasts, setToasts] = useState([])
  const [theme, setTheme] = useState(localStorage.getItem('creatoriq:theme') || 'light')

  useEffect(() => {
    const handleToast = (event) => {
      const toast = event.detail
      setToasts((current) => [...current, { id: Date.now() + Math.random(), ...toast }])
    }

    window.addEventListener('creatoriq:toast', handleToast)
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('creatoriq:theme', theme)
    return () => window.removeEventListener('creatoriq:toast', handleToast)
  }, [theme])

  // Check for token in URL (e.g. Google OAuth redirect /dashboard?token=...)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlToken = params.get('token')
    if (urlToken) {
      const cleanToken = urlToken.trim().replace(/^["']|["']$/g, '')
      localStorage.setItem('creatoriq_token', cleanToken)
      localStorage.setItem('token', cleanToken)
      params.delete('token')
      const newSearch = params.toString() ? `?${params.toString()}` : ''
      window.history.replaceState({}, '', `${window.location.pathname}${newSearch}`)
      apiClient
        .get('/auth/me', { headers: { Authorization: `Bearer ${cleanToken}` } })
        .then(({ data }) => setSession(cleanToken, data))
        .catch(() => clearSession())
        .finally(() => setIsCheckingAuth(false))
    }
  }, [clearSession, setSession])

  useEffect(() => {
    if (!token) {
      setIsCheckingAuth(false)
      return
    }
    apiClient
      .get('/auth/me')
      .then(({ data }) => setSession(token, data))
      .catch(() => clearSession())
      .finally(() => setIsCheckingAuth(false))
  }, [clearSession, setSession, token])

  useEffect(() => {
    if (toasts.length === 0) return undefined
    const timeoutId = window.setTimeout(() => {
      setToasts((current) => current.slice(1))
    }, 3600)
    return () => window.clearTimeout(timeoutId)
  }, [toasts])

  function logout() {
    clearSession()
  }

  if (isCheckingAuth) {
    return (
      <main className="auth-page">
        <div className="auth-glow" />
        <section className="auth-panel" style={{ textAlign: 'center', padding: '48px 32px' }}>
          <div className="brand-mark large" style={{ margin: '0 auto 16px' }}>C</div>
          <h2>CreatorIQ</h2>
          <p className="muted">Restoring your workspace session...</p>
          <div className="skeleton-box skeleton-pulse" style={{ height: '4px', width: '120px', margin: '20px auto 0' }} />
        </section>
      </main>
    )
  }

  if (!user) {
    return (
      <>
        <AuthPage />
        <div className="toast-stack">
          {toasts.map((toast) => (
            <div key={toast.id} className={`toast toast-${toast.variant || 'info'}`}>
              <strong>{toast.title}</strong>
              <span>{toast.message}</span>
            </div>
          ))}
        </div>
      </>
    )
  }

  return (
    <>
      <ErrorBoundary>
        <Routes>
          <Route path="/welcome" element={<WelcomePage user={user} />} />
          <Route path="/dashboard" element={<Layout user={user} logout={logout} />}>
            <Route index element={<OverviewPage />} />
            <Route path="overview" element={<OverviewPage />} />
            <Route path="content" element={<ContentPage />} />
            <Route path="trends" element={<TrendsPage />} />
            <Route path="audience" element={<AudiencePage />} />
            <Route path="social" element={<SocialMediaPage />} />
            <Route path="revenue" element={<RevenuePage />} />
            <Route path="monetization" element={<Navigate to="/dashboard/revenue" replace />} />
            <Route path="platforms" element={<Navigate to="/dashboard/social" replace />} />
            <Route path="compare" element={<Navigate to="/dashboard/content" replace />} />
            <Route path="realtime" element={<Navigate to="/dashboard" replace />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/login" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </ErrorBoundary>
      <div className="toast-stack">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.variant || 'info'}`}>
            <strong>{toast.title}</strong>
            <span>{toast.message}</span>
          </div>
        ))}
      </div>
    </>
  )
}

export default App
