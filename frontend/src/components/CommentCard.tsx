import { AlertCircle, AlertTriangle, Info, FileCode, Lightbulb } from 'lucide-react'
import type { ReviewComment, Severity, Category } from '@/types'

interface CommentCardProps {
  comment: ReviewComment
}

// ── Severity display config ───────────────────────────────────────────
const severityConfig: Record<Severity, {
  icon: React.ComponentType<{ size?: number }>
  badgeClass: string
  label: string
  borderClass: string
}> = {
  error: {
    icon: AlertCircle,
    badgeClass: 'badge-error',
    label: 'ERROR',
    borderClass: 'border-l-red-500',
  },
  warning: {
    icon: AlertTriangle,
    badgeClass: 'badge-warning',
    label: 'WARNING',
    borderClass: 'border-l-yellow-500',
  },
  info: {
    icon: Info,
    badgeClass: 'badge-info',
    label: 'INFO',
    borderClass: 'border-l-blue-500',
  },
}

// ── Category colors ───────────────────────────────────────────────────
const categoryColors: Record<Category, string> = {
  security:      'bg-red-950 text-red-300 border-red-800',
  syntax:        'bg-orange-950 text-orange-300 border-orange-800',
  style:         'bg-purple-950 text-purple-300 border-purple-800',
  complexity:    'bg-cyan-950 text-cyan-300 border-cyan-800',
  documentation: 'bg-green-950 text-green-300 border-green-800',
}

export default function CommentCard({ comment }: CommentCardProps) {
  const { icon: Icon, badgeClass, label, borderClass } = severityConfig[comment.severity]
  const categoryClass = categoryColors[comment.category]

  return (
    <div className={`card border-l-4 ${borderClass} space-y-3`}>

      {/* ── Header: Severity + Category badges ─────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          {/* Severity badge */}
          <span className={badgeClass}>
            <Icon size={11} />
            {label}
          </span>

          {/* Category chip */}
          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs
                            font-semibold border ${categoryClass}`}>
            {comment.category.toUpperCase()}
          </span>
        </div>

        {/* File + line reference */}
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <FileCode size={12} />
          <code className="font-mono text-gray-400">
            {comment.file_path}
            {comment.line_number && (
              <span className="text-gray-600">:{comment.line_number}</span>
            )}
          </code>
        </div>
      </div>

      {/* ── Issue message ────────────────────────────────────────── */}
      <p className="text-sm text-gray-200 leading-relaxed">
        {comment.message}
      </p>

      {/* ── Suggestion (shown only if present) ──────────────────── */}
      {comment.suggestion && (
        <div className="rounded-lg border border-gray-700 bg-gray-950/50 p-3 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs text-sheriff-400 font-medium">
            <Lightbulb size={12} />
            Suggestion
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">
            {comment.suggestion}
          </p>
        </div>
      )}

    </div>
  )
}
