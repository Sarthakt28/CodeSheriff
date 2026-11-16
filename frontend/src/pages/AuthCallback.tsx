import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2, AlertCircle } from 'lucide-react'
import { authApi, setToken } from '@/lib/api'

export default function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const code = searchParams.get('code')

    if (!code) {
      setError('No authorization code received from GitHub. Please try again.')
      return
    }

    // Exchange the one-time code for a JWT from our backend
    authApi
      .githubCallback(code)
      .then(({ data }) => {
        // Save JWT to localStorage — all future API calls will use this
        setToken(data.access_token)
        // Sync repos automatically after first login for a smooth experience
        navigate('/dashboard', { replace: true })
      })
      .catch((err) => {
        const message =
          err.response?.data?.detail ?? 'Authentication failed. Please try again.'
        setError(message)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Run once on mount — the code is in the URL, not changing

  // ── Loading state ─────────────────────────────────────────────────
  if (!error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-5xl">🤠</div>
          <Loader2 className="mx-auto text-sheriff-400 animate-spin" size={32} />
          <p className="text-gray-400">Signing you in with GitHub…</p>
        </div>
      </div>
    )
  }

  // ── Error state ───────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="card max-w-md w-full space-y-4 text-center">
        <AlertCircle className="mx-auto text-red-400" size={40} />
        <h2 className="text-xl font-bold text-white">Authentication Failed</h2>
        <p className="text-sm text-gray-400">{error}</p>
        <a href="/login" className="btn-primary inline-block no-underline">
          Try Again
        </a>
      </div>
    </div>
  )
}
