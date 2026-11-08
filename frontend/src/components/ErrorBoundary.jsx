import React from 'react'

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div style={{
          padding: '32px',
          margin: '24px auto',
          maxWidth: '800px',
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '16px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
          color: '#0f172a',
          fontFamily: 'system-ui, -apple-system, sans-serif'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <span style={{ fontSize: '28px' }}>⚠️</span>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                Something went wrong in this section
              </h2>
              <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.9rem' }}>
                An unexpected error occurred while rendering the dashboard.
              </p>
            </div>
          </div>

          <div style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '10px',
            padding: '14px',
            color: '#991b1b',
            fontSize: '0.88rem',
            marginBottom: '16px',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}>
            {this.state.error?.toString() || 'Unknown runtime error'}
          </div>

          {this.state.errorInfo?.componentStack && (
            <details style={{ marginBottom: '20px', fontSize: '0.82rem', color: '#64748b' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: '8px' }}>
                Component Stack Trace
              </summary>
              <pre style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '12px',
                overflowX: 'auto'
              }}>
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              type="button"
              onClick={this.handleReset}
              style={{
                background: '#0284c7',
                color: '#ffffff',
                border: 'none',
                borderRadius: '10px',
                padding: '9px 18px',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              Try Again
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{
                background: '#ffffff',
                color: '#334155',
                border: '1px solid #cbd5e1',
                borderRadius: '10px',
                padding: '9px 18px',
                fontWeight: 500,
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              Reload Page
            </button>
            <a
              href="/dashboard"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                background: '#f1f5f9',
                color: '#334155',
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                padding: '9px 18px',
                fontWeight: 500,
                fontSize: '0.9rem',
                textDecoration: 'none'
              }}
            >
              Go to Overview
            </a>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
