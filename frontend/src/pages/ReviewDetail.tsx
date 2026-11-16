import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  GitPullRequest, User, GitCommit, ArrowLeft,
  FileCode, AlertCircle, AlertTriangle, Info, Loader2
} from 'lucide-react'
import { reviewsApi } from '@/lib/api'
import CommentCard from '@/components/CommentCard'
import type { ReviewDetail as ReviewDetailType, ReviewComment } from '@/types'

// Group comments by file path
function groupByFile(comments: ReviewComment[]): Record<string, ReviewComment[]> {
  return comments.reduce((acc, comment) => {
    const key = comment.file_path
    if (!acc[key]) acc[key] = []
    acc[key].push(comment)
    return acc
  }, {} as Record<string, ReviewComment[]>)
}

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>()
  const [review, setReview] = useState<ReviewDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    reviewsApi.get(Number(id))
      .then((res) => setReview(res.data))
      .catch(() => setError('Review not found or you do not have access.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="animate-spin text-sheriff-400" size={32} />
      </div>
    )
  }

  if (error || !review) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center space-y-4">
        <AlertCircle size={40} className="mx-auto text-red-400" />
        <p className="text-gray-400">{error ?? 'Something went wrong.'}</p>
        <Link to="/reviews" className="btn-ghost inline-flex items-center gap-2 no-underline">
          <ArrowLeft size={14} /> Back to Reviews
        </Link>
      </div>
    )
  }

  const errors   = review.comments.filter((c) => c.severity === 'error').length
  const warnings = review.comments.filter((c) => c.severity === 'warning').length
  const infos    = review.comments.filter((c) => c.severity === 'info').length
  const fileGroups = groupByFile(review.comments)

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 space-y-6">

      {/* ── Back link ─────────────────────────────────────────────── */}
      <Link to="/reviews" className="inline-flex items-center gap-2 text-sm
                                      text-gray-500 hover:text-white no-underline transition-colors">
        <ArrowLeft size={14} /> Back to Reviews
      </Link>

      {/* ── PR header card ───────────────────────────────────────── */}
      <div className="card space-y-4">
        <div className="flex items-start gap-3">
          <GitPullRequest size={22} className="text-sheriff-400 mt-0.5 flex-shrink-0" />
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-white leading-snug">
              {review.pr_title ?? `PR #${review.pr_number}`}
            </h1>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <GitPullRequest size={11} /> PR #{review.pr_number}
              </span>
              {review.pr_author && (
                <span className="flex items-center gap-1">
                  <User size={11} /> @{review.pr_author}
                </span>
              )}
              {review.commit_sha && (
                <span className="flex items-center gap-1 font-mono">
                  <GitCommit size={11} /> {review.commit_sha.slice(0, 7)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Summary */}
        {review.summary && (
          <p className="text-sm text-gray-300 leading-relaxed border-t border-gray-800 pt-4">
            {review.summary}
          </p>
        )}
      </div>

      {/* ── Issue breakdown stats ────────────────────────────────── */}
      {review.comments.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { count: errors,   label: 'Errors',   icon: AlertCircle,  cls: 'text-red-400 bg-red-950/50 border-red-900' },
            { count: warnings, label: 'Warnings', icon: AlertTriangle, cls: 'text-yellow-400 bg-yellow-950/50 border-yellow-900' },
            { count: infos,    label: 'Info',      icon: Info,         cls: 'text-blue-400 bg-blue-950/50 border-blue-900' },
          ].map(({ count, label, icon: Icon, cls }) => (
            <div key={label} className={`rounded-xl border p-4 text-center ${cls}`}>
              <Icon size={18} className="mx-auto mb-1" />
              <p className="text-2xl font-bold">{count}</p>
              <p className="text-xs opacity-70 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Comments grouped by file ─────────────────────────────── */}
      {review.comments.length === 0 ? (
        <div className="card text-center py-12 space-y-3">
          <span className="text-4xl">✅</span>
          <p className="font-semibold text-white">No issues found!</p>
          <p className="text-sm text-gray-500">This PR passed all CodeSheriff checks.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(fileGroups).map(([filePath, comments]) => (
            <div key={filePath} className="space-y-3">
              {/* File header */}
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-300">
                <FileCode size={15} className="text-sheriff-400" />
                <code className="font-mono">{filePath}</code>
                <span className="text-xs text-gray-600 font-normal">
                  ({comments.length} issue{comments.length !== 1 ? 's' : ''})
                </span>
              </div>

              {/* Comments for this file */}
              <div className="space-y-3 pl-4 border-l border-gray-800">
                {comments.map((comment) => (
                  <CommentCard key={comment.id} comment={comment} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  )
}
