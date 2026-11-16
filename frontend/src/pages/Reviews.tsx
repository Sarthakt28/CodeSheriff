import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  GitPullRequest, ChevronRight, AlertCircle,
  CheckCircle2, Clock, Loader2, XCircle
} from 'lucide-react'
import { reviewsApi } from '@/lib/api'
import type { PRReview, ReviewStatus } from '@/types'

const statusConfig: Record<ReviewStatus, {
  label: string; className: string
  icon: React.ComponentType<{ size?: number; className?: string }>
}> = {
  pending:   { label: 'Pending',   className: 'text-gray-400 bg-gray-800',    icon: Clock },
  running:   { label: 'Reviewing', className: 'text-yellow-400 bg-yellow-950', icon: Loader2 },
  completed: { label: 'Done',      className: 'text-green-400 bg-green-950',   icon: CheckCircle2 },
  failed:    { label: 'Failed',    className: 'text-red-400 bg-red-950',       icon: XCircle },
}

function IssueCount({ count }: { count: number }) {
  if (count === 0)
    return <span className="text-xs text-green-400 font-semibold flex items-center gap-1">
      <CheckCircle2 size={12} /> Clean
    </span>
  if (count <= 5)
    return <span className="text-xs text-yellow-400 font-semibold flex items-center gap-1">
      <AlertCircle size={12} /> {count} issue{count !== 1 ? 's' : ''}
    </span>
  return <span className="text-xs text-red-400 font-semibold flex items-center gap-1">
    <AlertCircle size={12} /> {count} issues
  </span>
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

const PAGE_SIZE = 20

export default function Reviews() {
  const [reviews, setReviews] = useState<PRReview[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(true)

  const loadReviews = (skip: number, append = false) => {
    if (skip === 0) setLoading(true); else setLoadingMore(true)

    reviewsApi.list(skip, PAGE_SIZE)
      .then((res) => {
        const data = res.data
        setReviews((prev) => append ? [...prev, ...data] : data)
        setHasMore(data.length === PAGE_SIZE)
      })
      .finally(() => { setLoading(false); setLoadingMore(false) })
  }

  useEffect(() => { loadReviews(0) }, [])

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 space-y-6">

      <div>
        <h1 className="text-2xl font-bold text-white">Reviews</h1>
        <p className="text-gray-500 text-sm mt-1">All pull request reviews by CodeSheriff</p>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="animate-spin text-sheriff-400" size={28} />
        </div>
      ) : reviews.length === 0 ? (
        <div className="card text-center py-16 space-y-3">
          <GitPullRequest size={40} className="mx-auto text-gray-700" />
          <p className="text-gray-400 font-medium">No reviews yet</p>
          <p className="text-gray-600 text-sm">
            Enable CodeSheriff on a repository and open a pull request.
          </p>
        </div>
      ) : (
        <div className="card divide-y divide-gray-800 p-0 overflow-hidden">
          {reviews.map((review) => {
            const { label, className, icon: Icon } = statusConfig[review.status]
            return (
              <Link
                key={review.id}
                to={`/reviews/${review.id}`}
                className="flex items-center justify-between p-5 hover:bg-gray-800/50
                           transition-colors no-underline group"
              >
                {/* Left: PR info */}
                <div className="space-y-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">
                    {review.pr_title ?? `PR #${review.pr_number}`}
                  </p>
                  <p className="text-xs text-gray-500">
                    PR #{review.pr_number}
                    {review.pr_author && ` · by @${review.pr_author}`}
                    {' · '}{formatDate(review.created_at)}
                  </p>
                </div>

                {/* Right: Status + issues + arrow */}
                <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                  <IssueCount count={review.total_issues} />
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1
                                    rounded-full text-xs font-semibold ${className}`}>
                    <Icon size={11} className={review.status === 'running' ? 'animate-spin' : ''} />
                    {label}
                  </span>
                  <ChevronRight size={14} className="text-gray-600 group-hover:text-gray-400" />
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {/* Load more button */}
      {!loading && hasMore && (
        <div className="text-center">
          <button
            onClick={() => loadReviews(reviews.length, true)}
            disabled={loadingMore}
            className="btn-ghost flex items-center gap-2 mx-auto"
          >
            {loadingMore ? <Loader2 size={14} className="animate-spin" /> : null}
            Load more
          </button>
        </div>
      )}

    </div>
  )
}
