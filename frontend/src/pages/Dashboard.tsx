import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  GitPullRequest, Shield, Server, AlertCircle,
  CheckCircle2, Clock, Loader2, XCircle, ChevronRight
} from 'lucide-react'
import { reviewsApi, reposApi } from '@/lib/api'
import type { PRReview, Repository, ReviewStatus } from '@/types'

// ── Status badge config ─────────────────────────────────────────────
const statusConfig: Record<ReviewStatus, {
  label: string
  className: string
  icon: React.ComponentType<{ size?: number; className?: string }>
}> = {
  pending:   { label: 'Pending',   className: 'text-gray-400 bg-gray-800',   icon: Clock },
  running:   { label: 'Running',   className: 'text-yellow-400 bg-yellow-950', icon: Loader2 },
  completed: { label: 'Completed', className: 'text-green-400 bg-green-950',  icon: CheckCircle2 },
  failed:    { label: 'Failed',    className: 'text-red-400 bg-red-950',      icon: XCircle },
}

function StatusBadge({ status }: { status: ReviewStatus }) {
  const { label, className, icon: Icon } = statusConfig[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
                      text-xs font-semibold ${className}`}>
      <Icon size={11} className={status === 'running' ? 'animate-spin' : ''} />
      {label}
    </span>
  )
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function Dashboard() {
  const [reviews, setReviews] = useState<PRReview[]>([])
  const [repos, setRepos] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch reviews and repos simultaneously (parallel, not sequential)
    Promise.all([reviewsApi.list(0, 20), reposApi.list()])
      .then(([reviewsRes, reposRes]) => {
        setReviews(reviewsRes.data)
        setRepos(reposRes.data)
      })
      .finally(() => setLoading(false))
  }, [])

  const totalIssues = reviews.reduce((sum, r) => sum + r.total_issues, 0)
  const activeRepos = repos.filter((r) => r.is_active).length
  const recentReviews = reviews.slice(0, 5)

  const stats = [
    { label: 'Total Reviews',  value: reviews.length,  icon: GitPullRequest, color: 'text-sheriff-400' },
    { label: 'Issues Found',   value: totalIssues,      icon: AlertCircle,    color: 'text-red-400' },
    { label: 'Active Repos',   value: activeRepos,      icon: Server,         color: 'text-green-400' },
  ]

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="animate-spin text-sheriff-400" size={32} />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 space-y-8">

      {/* ── Page header ─────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">
          Overview of your CodeSheriff activity
        </p>
      </div>

      {/* ── Stat cards ──────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card flex items-center gap-4">
            <div className={`rounded-xl bg-gray-800 p-3 ${color}`}>
              <Icon size={22} />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Recent reviews table ─────────────────────────────────── */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <GitPullRequest size={18} className="text-sheriff-400" />
            Recent Reviews
          </h2>
          <Link to="/reviews" className="text-xs text-sheriff-400 hover:text-sheriff-500 no-underline">
            View all →
          </Link>
        </div>

        {recentReviews.length === 0 ? (
          <div className="py-10 text-center">
            <Shield size={40} className="mx-auto text-gray-700 mb-3" />
            <p className="text-gray-500 text-sm">No reviews yet.</p>
            <p className="text-gray-600 text-xs mt-1">
              Enable CodeSheriff on a repo and open a PR to get started.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {recentReviews.map((review) => (
              <Link
                key={review.id}
                to={`/reviews/${review.id}`}
                className="flex items-center justify-between py-3 no-underline
                           hover:bg-gray-800/50 -mx-5 px-5 rounded-lg transition-colors group"
              >
                <div className="space-y-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {review.pr_title ?? `PR #${review.pr_number}`}
                  </p>
                  <p className="text-xs text-gray-500">
                    PR #{review.pr_number} · {timeAgo(review.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                  <StatusBadge status={review.status} />
                  {review.total_issues > 0 && (
                    <span className="text-xs text-red-400 font-semibold">
                      {review.total_issues} issue{review.total_issues !== 1 ? 's' : ''}
                    </span>
                  )}
                  <ChevronRight size={14} className="text-gray-600 group-hover:text-gray-400" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

    </div>
  )
}
