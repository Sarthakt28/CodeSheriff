import { useNavigate, NavLink } from 'react-router-dom'
import { Shield, GitPullRequest, Server, LogOut } from 'lucide-react'
import { removeToken } from '@/lib/api'
import type { User } from '@/types'

interface NavbarProps {
  user: User | null
}

// Navigation links for the main dashboard sections
const navLinks = [
  { to: '/dashboard', label: 'Dashboard', icon: Shield },
  { to: '/repositories', label: 'Repositories', icon: Server },
  { to: '/reviews', label: 'Reviews', icon: GitPullRequest },
]

export default function Navbar({ user }: NavbarProps) {
  const navigate = useNavigate()

  const handleLogout = () => {
    removeToken()          // wipe the JWT from localStorage
    navigate('/login')     // send user back to login screen
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-800 bg-gray-950/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">

        {/* ── Brand Logo ─────────────────────────────────────────── */}
        <NavLink to="/dashboard" className="flex items-center gap-2 no-underline">
          <span className="text-2xl">🤠</span>
          <span className="text-lg font-bold text-white">
            Code<span className="text-sheriff-500">Sheriff</span>
          </span>
        </NavLink>

        {/* ── Navigation Links ─────────────────────────────────── */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors no-underline ${
                  isActive
                    ? 'bg-sheriff-600/20 text-sheriff-400'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* ── User Profile + Logout ─────────────────────────────── */}
        <div className="flex items-center gap-3">
          {user && (
            <div className="flex items-center gap-2">
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.username}
                  className="h-8 w-8 rounded-full border border-gray-700"
                />
              ) : (
                <div className="h-8 w-8 rounded-full bg-sheriff-700 flex items-center justify-center text-sm font-bold">
                  {user.username[0].toUpperCase()}
                </div>
              )}
              <span className="hidden sm:block text-sm text-gray-300 font-medium">
                @{user.username}
              </span>
            </div>
          )}

          <button
            onClick={handleLogout}
            className="flex items-center gap-2 rounded-lg border border-gray-700
                       px-3 py-1.5 text-sm text-gray-400 hover:border-red-700
                       hover:text-red-400 transition-colors"
            title="Logout"
          >
            <LogOut size={15} />
            <span className="hidden sm:block">Logout</span>
          </button>
        </div>

      </div>
    </header>
  )
}
