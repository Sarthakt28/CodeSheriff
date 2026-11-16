import { useEffect, useState } from 'react'
import { Server, RefreshCw, Loader2, ToggleLeft, ToggleRight, GitBranch } from 'lucide-react'
import { reposApi } from '@/lib/api'
import type { Repository } from '@/types'

export default function Repositories() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [togglingId, setTogglingId] = useState<number | null>(null)

  const fetchRepos = () => {
    setLoading(true)
    reposApi.list()
      .then((res) => setRepos(res.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchRepos() }, [])

  // Sync repos from GitHub then refresh the list
  const handleSync = async () => {
    setSyncing(true)
    try {
      await reposApi.sync()
      await fetchRepos()
    } finally {
      setSyncing(false)
    }
  }

  // Toggle CodeSheriff on/off for a repo
  const handleToggle = async (repo: Repository) => {
    setTogglingId(repo.id)

    // Optimistic update — flip immediately in UI before server confirms
    setRepos((prev) =>
      prev.map((r) => (r.id === repo.id ? { ...r, is_active: !r.is_active } : r))
    )

    try {
      const res = await reposApi.toggle(repo.id)
      // Sync with actual server value
      setRepos((prev) =>
        prev.map((r) => (r.id === repo.id ? res.data : r))
      )
    } catch {
      // Revert on failure
      setRepos((prev) =>
        prev.map((r) => (r.id === repo.id ? { ...r, is_active: repo.is_active } : r))
      )
    } finally {
      setTogglingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 space-y-6">

      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Repositories</h1>
          <p className="text-gray-500 text-sm mt-1">
            Manage which repos CodeSheriff monitors
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-primary flex items-center gap-2"
        >
          {syncing
            ? <Loader2 size={15} className="animate-spin" />
            : <RefreshCw size={15} />
          }
          {syncing ? 'Syncing…' : 'Sync from GitHub'}
        </button>
      </div>

      {/* ── Stats bar ──────────────────────────────────────────── */}
      {!loading && (
        <div className="flex gap-4 text-sm text-gray-500">
          <span>{repos.length} repos total</span>
          <span>·</span>
          <span className="text-green-400">{repos.filter((r) => r.is_active).length} active</span>
        </div>
      )}

      {/* ── Repo list ───────────────────────────────────────────── */}
      {loading ? (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="animate-spin text-sheriff-400" size={28} />
        </div>
      ) : repos.length === 0 ? (
        <div className="card text-center py-16 space-y-3">
          <Server size={40} className="mx-auto text-gray-700" />
          <p className="text-gray-400 font-medium">No repositories found</p>
          <p className="text-gray-600 text-sm">
            Click "Sync from GitHub" to import your repositories.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {repos.map((repo) => (
            <div
              key={repo.id}
              className={`card flex items-center justify-between gap-4 transition-opacity ${
                !repo.is_active ? 'opacity-60' : ''
              }`}
            >
              {/* Repo info */}
              <div className="flex items-center gap-3 min-w-0">
                <GitBranch
                  size={18}
                  className={repo.is_active ? 'text-sheriff-400' : 'text-gray-600'}
                />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white truncate">
                    {repo.full_name}
                  </p>
                  <p className="text-xs text-gray-600 mt-0.5">
                    GitHub ID: {repo.github_repo_id}
                  </p>
                </div>
              </div>

              {/* Toggle switch */}
              <button
                onClick={() => handleToggle(repo)}
                disabled={togglingId === repo.id}
                className="flex items-center gap-2 flex-shrink-0 transition-colors"
                title={repo.is_active ? 'Disable CodeSheriff' : 'Enable CodeSheriff'}
              >
                {togglingId === repo.id ? (
                  <Loader2 size={22} className="animate-spin text-gray-500" />
                ) : repo.is_active ? (
                  <ToggleRight size={28} className="text-sheriff-500" />
                ) : (
                  <ToggleLeft size={28} className="text-gray-600" />
                )}
                <span className={`text-xs font-medium ${
                  repo.is_active ? 'text-sheriff-400' : 'text-gray-600'
                }`}>
                  {repo.is_active ? 'Active' : 'Paused'}
                </span>
              </button>
            </div>
          ))}
        </div>
      )}

    </div>
  )
}
