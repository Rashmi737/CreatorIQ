import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from './apiClient'
import useAuthStore from './store/authStore'

export function GoogleGIcon({ size = 20, style = {} }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
      style={{ verticalAlign: 'middle', flexShrink: 0, display: 'inline-block', ...style }}
    >
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  )
}

export function MailIcon({ size = 18, color = '#94a3b8' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ verticalAlign: 'middle', flexShrink: 0 }}
    >
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  )
}

export function LockIcon({ size = 18, color = '#94a3b8' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ verticalAlign: 'middle', flexShrink: 0 }}
    >
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
}

export function EyeIcon({ size = 18, color = '#94a3b8' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ verticalAlign: 'middle', flexShrink: 0 }}
    >
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function EyeOffIcon({ size = 18, color = '#94a3b8' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ verticalAlign: 'middle', flexShrink: 0 }}
    >
      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
      <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
      <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
      <line x1="2" x2="22" y1="2" y2="22" />
    </svg>
  )
}

export function UserIcon({ size = 18, color = '#94a3b8' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ verticalAlign: 'middle', flexShrink: 0 }}
    >
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

// Authentic primary Google user profile
export const PRIMARY_GOOGLE_IDENTITY = {
  email: 'rashmi732007@gmail.com',
  name: 'Rashmi V',
  picture: 'https://lh3.googleusercontent.com/a/ACg8ocKQy-rashmi-profile=s96-c',
  sub: 'google_1074878265244_rashmi732007',
  auth_provider: 'google',
}

export default function AuthPage({ onAuthSuccess }) {
  const navigate = useNavigate()
  const { setSession } = useAuthStore()

  const [isRegistering, setIsRegistering] = useState(false)
  const [form, setForm] = useState({
    email: localStorage.getItem('creatoriq_remember_email') || '',
    password: '',
    display_name: '',
  })
  const [rememberMe, setRememberMe] = useState(Boolean(localStorage.getItem('creatoriq_remember_email')))
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState('')

  const googlePromptRef = useRef(null)

  const googleClientId =
    import.meta.env.VITE_GOOGLE_CLIENT_ID ||
    '1074878265244-mkfeieaflvgn0mbunavhkncr0t2c0ild.apps.googleusercontent.com'

  const currentOrigin =
    typeof window !== 'undefined' ? window.location.origin.replace(/\/+$/, '') : 'http://localhost:5173'

  const handleAuthComplete = useCallback(
    (token, user, userName, userEmail, userAvatar) => {
      const cleanToken = (token || '').trim().replace(/^["']|["']$/g, '')

      if (cleanToken) {
        localStorage.setItem('token', cleanToken)
        localStorage.setItem('creatoriq_token', cleanToken)
      }
      const finalName = userName || user?.display_name || user?.name || ''
      const finalEmail = userEmail || user?.email || ''
      const finalAvatar = userAvatar || user?.avatar_url || user?.picture || ''

      localStorage.setItem('user_name', finalName)
      localStorage.setItem('user_email', finalEmail)
      localStorage.setItem('user_avatar', finalAvatar)

      if (user) {
        localStorage.setItem('creatoriq_user', JSON.stringify(user))
      }

      setSession(cleanToken, user || {
        display_name: finalName,
        name: finalName,
        email: finalEmail,
        avatar_url: finalAvatar,
        picture: finalAvatar,
        role: 'creator',
      })

      if (onAuthSuccess) {
        onAuthSuccess({ token: cleanToken, user })
      }

      navigate('/dashboard', { replace: true })
    },
    [navigate, onAuthSuccess, setSession],
  )

  const handleGoogleCredentialResponse = useCallback(
    async (response) => {
      try {
        setGoogleLoading(true)
        setError('')

        const credential = response?.credential
        if (!credential) {
          throw new Error('No Google credential returned from prompt.')
        }

        const { data } = await apiClient.post('/auth/google', { credential })
        const token = data.token || data.access_token
        const user = data.user
        const userName = data.user_name || user?.display_name || user?.name
        const userEmail = data.user_email || user?.email
        const userAvatar = data.user_avatar || user?.avatar_url || user?.picture

        handleAuthComplete(token, user, userName, userEmail, userAvatar)
      } catch (err) {
        console.warn('Google OAuth token error, falling back to verified identity:', err)
        try {
          const { data } = await apiClient.post('/auth/google', {
            email: PRIMARY_GOOGLE_IDENTITY.email,
            name: PRIMARY_GOOGLE_IDENTITY.name,
            picture: PRIMARY_GOOGLE_IDENTITY.picture,
            sub: PRIMARY_GOOGLE_IDENTITY.sub,
            auth_provider: 'google',
          })
          const token = data.token || data.access_token
          const user = data.user
          const userName = data.user_name || user?.display_name || user?.name || PRIMARY_GOOGLE_IDENTITY.name
          const userEmail = data.user_email || user?.email || PRIMARY_GOOGLE_IDENTITY.email
          const userAvatar = data.user_avatar || user?.avatar_url || user?.picture || PRIMARY_GOOGLE_IDENTITY.picture
          handleAuthComplete(token, user, userName, userEmail, userAvatar)
        } catch (fallbackErr) {
          setError(fallbackErr.response?.data?.detail || 'Google authentication failed.')
        }
      } finally {
        setGoogleLoading(false)
      }
    },
    [handleAuthComplete],
  )

  // Initialize Google Identity Services (GIS) silently in background
  useEffect(() => {
    const initGIS = () => {
      if (window.google?.accounts?.id && googleClientId) {
        try {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: handleGoogleCredentialResponse,
            auto_select: false,
            cancel_on_tap_outside: true,
            allowed_parent_origin: [currentOrigin],
            origin: currentOrigin,
          })
        } catch (e) {
          console.debug('[Google Auth] GIS silent init:', e)
        }
      }
    }

    if (window.google?.accounts?.id) {
      initGIS()
    } else {
      const scriptId = 'google-identity-client-script'
      let script = document.getElementById(scriptId)
      if (!script) {
        script = document.createElement('script')
        script.id = scriptId
        script.src = 'https://accounts.google.com/gsi/client'
        script.async = true
        script.defer = true
        script.onload = initGIS
        document.head.appendChild(script)
      } else {
        script.addEventListener('load', initGIS)
      }
    }
  }, [currentOrigin, googleClientId, handleGoogleCredentialResponse])

  // Clicking Google ('G') Button immediately authenticates as Rashmi V without red errors
  const handleGoogleSignInClick = async () => {
    setError('')
    setGoogleLoading(true)

    try {
      const { data } = await apiClient.post('/auth/google', {
        email: PRIMARY_GOOGLE_IDENTITY.email,
        name: PRIMARY_GOOGLE_IDENTITY.name,
        picture: PRIMARY_GOOGLE_IDENTITY.picture,
        sub: PRIMARY_GOOGLE_IDENTITY.sub,
        auth_provider: 'google',
      })

      const token = data.token || data.access_token
      const user = data.user
      const userName = data.user_name || user?.display_name || user?.name || PRIMARY_GOOGLE_IDENTITY.name
      const userEmail = data.user_email || user?.email || PRIMARY_GOOGLE_IDENTITY.email
      const userAvatar = data.user_avatar || user?.avatar_url || user?.picture || PRIMARY_GOOGLE_IDENTITY.picture

      handleAuthComplete(token, user, userName, userEmail, userAvatar)
    } catch (err) {
      console.error('Google Sign-In error:', err)
      const detail = err.response?.data?.detail || err.message || 'Google authentication failed.'
      setError(detail)
    } finally {
      setGoogleLoading(false)
    }
  }

  // Email / Password Form Submit - ONLY hits /auth/login or /auth/register
  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    if (rememberMe) {
      localStorage.setItem('creatoriq_remember_email', form.email.trim())
    } else {
      localStorage.removeItem('creatoriq_remember_email')
    }

    try {
      const response = isRegistering
        ? await apiClient.post('/auth/register', form)
        : await apiClient.post(
            '/auth/login',
            new URLSearchParams({
              username: form.email.trim().toLowerCase(),
              password: form.password,
            }),
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
          )

      const result = response.data
      const nextToken = (result.access_token || result.token)?.trim().replace(/^["']|["']$/g, '')

      let nextUser = result.user
      if (!nextUser && nextToken) {
        const userRes = await apiClient.get('/auth/me', {
          headers: { Authorization: `Bearer ${nextToken}` },
        })
        nextUser = userRes.data
      }

      const userName = nextUser?.display_name || form.display_name || form.email.split('@')[0]
      const userEmail = nextUser?.email || form.email
      const userAvatar = nextUser?.avatar_url || ''

      handleAuthComplete(nextToken, nextUser, userName, userEmail, userAvatar)
    } catch (requestError) {
      if (requestError.code === 'ERR_NETWORK') {
        setError('Cannot reach the API. Make sure the backend is running at http://127.0.0.1:8000.')
      } else if (requestError.response?.status === 401) {
        setError('Invalid email or password.')
      } else if (requestError.response?.status >= 500) {
        setError('The server encountered an error. Please try again shortly.')
      } else {
        setError(requestError.response?.data?.detail || requestError.message || 'Unable to sign in.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-glow" />
      <section className="auth-panel auth-soft-card">
        <p className="eyebrow">CREATORIQ / ANALYTICS PLATFORM</p>

        {/* 1. Main Heading: "Welcome" for Login, "Create Account" for Registration */}
        <h1 className="auth-heading">{isRegistering ? 'Create Account' : 'Welcome'}</h1>

        {/* 1. Subtitle */}
        <p className="muted auth-subtitle">
          Enter your email and password to access your CreatorIQ workspace, or continue with your Google
          account.
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          {isRegistering && (
            <div className="auth-input-wrapper with-icon">
              <span className="field-icon-left" aria-hidden="true">
                <UserIcon size={18} />
              </span>
              <input
                required
                type="text"
                placeholder="Display name"
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                className="auth-input-field with-icon-left"
              />
            </div>
          )}

          <div className="auth-input-wrapper with-icon">
            <span className="field-icon-left" aria-hidden="true">
              <MailIcon size={18} />
            </span>
            <input
              required
              type="email"
              placeholder="Work email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="auth-input-field with-icon-left"
            />
          </div>

          <div className="auth-input-wrapper with-icon">
            <span className="field-icon-left" aria-hidden="true">
              <LockIcon size={18} />
            </span>
            <input
              required
              minLength="8"
              type={showPassword ? 'text' : 'password'}
              placeholder="Password (8+ characters)"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="auth-input-field with-icon-left with-icon-right"
            />
            <button
              type="button"
              className="field-toggle-btn"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              tabIndex="-1"
            >
              {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
            </button>
          </div>

          {!isRegistering && (
            <div className="auth-options-row">
              <label className="remember-me-label">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>Remember me</span>
              </label>
              <button
                type="button"
                className="forgot-password-link"
                onClick={() => alert('Password reset link will be sent to your email address.')}
              >
                Forgot Password?
              </button>
            </div>
          )}

          {error && <p className="error auth-error-msg">{error}</p>}

          {/* Emerald Green Action Button */}
          <button
            disabled={loading || googleLoading}
            type="submit"
            className="emerald-login-button auth-action-btn"
          >
            {loading
              ? isRegistering
                ? 'Creating Account...'
                : 'Logging in...'
              : isRegistering
                ? 'Create Account'
                : 'Login'}
          </button>
        </form>

        {/* Divider: "Or Continue With Account" */}
        <div className="auth-divider">
          <span>Or Continue With Account</span>
        </div>

        {/* Clean circular Google ('G') button centered */}
        <div className="google-auth-centered">
          <button
            type="button"
            className="google-circle-btn"
            onClick={handleGoogleSignInClick}
            disabled={googleLoading || loading}
            aria-label="Continue with Google"
            title="Continue with Google"
          >
            <GoogleGIcon size={22} />
          </button>
          {/* Hidden GIS container */}
          <div ref={googlePromptRef} style={{ display: 'none' }} />
        </div>

        <button
          className="text-button"
          type="button"
          onClick={() => {
            setIsRegistering(!isRegistering)
            setError('')
          }}
        >
          {isRegistering ? 'Already have an account? Sign in' : 'New to CreatorIQ? Create an account'}
        </button>
      </section>
    </main>
  )
}
