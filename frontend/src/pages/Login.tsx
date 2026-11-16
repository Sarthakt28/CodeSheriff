import { Github, Shield, Zap, Eye } from 'lucide-react'

// GitHub OAuth authorization URL — redirects user to GitHub's permission screen
const GITHUB_OAUTH_URL = `https://github.com/login/oauth/authorize?client_id=${
  import.meta.env.VITE_GITHUB_CLIENT_ID ?? ''
}&scope=repo,read:user&allow_signup=true`

// Feature highlights shown on the login page
const features = [
  {
    icon: Zap,
    title: 'Instant Reviews',
    description: 'Get automated PR reviews seconds after pushing code',
  },
  {
    icon: Shield,
    title: 'Security Scanning',
    description: 'Catch hardcoded secrets, API keys, and vulnerabilities',
  },
  {
    icon: Eye,
    title: 'Smart Analysis',
    description: 'Rules-based + ML-powered analysis across 500+ languages',
  },
]

export default function Login() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">

        {/* ── Brand Header ───────────────────────────────────────── */}
        <div className="text-center space-y-3">
          <div className="text-6xl">🤠</div>
          <h1 className="text-4xl font-bold text-white">
            Code<span className="text-sheriff-500">Sheriff</span>
          </h1>
          <p className="text-gray-400 text-lg">
            Automated AI code review for GitHub pull requests
          </p>
        </div>

        {/* ── Login Card ─────────────────────────────────────────── */}
        <div className="card space-y-6">
          <a
            href={GITHUB_OAUTH_URL}
            className="flex items-center justify-center gap-3 w-full
                       bg-white hover:bg-gray-100 text-gray-900
                       font-semibold py-3 px-6 rounded-xl transition-colors
                       no-underline text-base"
          >
            <Github size={20} />
            Sign in with GitHub
          </a>

          <p className="text-center text-xs text-gray-600">
            By signing in, you authorize CodeSheriff to read your repositories
            and post review comments on pull requests.
          </p>
        </div>

        {/* ── Feature Highlights ─────────────────────────────────── */}
        <div className="grid gap-4">
          {features.map(({ icon: Icon, title, description }) => (
            <div key={title} className="flex items-start gap-3">
              <div className="mt-0.5 flex-shrink-0 rounded-lg bg-sheriff-600/20 p-2">
                <Icon size={16} className="text-sheriff-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">{title}</p>
                <p className="text-xs text-gray-500 mt-0.5">{description}</p>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}
