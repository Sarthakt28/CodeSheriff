// ── Mirrors FastAPI response shapes exactly ────────────────────────

export interface User {
  id: number
  github_id: number
  username: string
  email: string | null
  avatar_url: string | null
  created_at: string
}

export interface Repository {
  id: number
  full_name: string              // e.g. "octocat/hello-world"
  github_repo_id: number
  is_active: boolean             // CodeSheriff enabled for this repo?
  created_at: string
}

export type ReviewStatus = 'pending' | 'running' | 'completed' | 'failed'
export type Severity = 'error' | 'warning' | 'info'
export type Category = 'syntax' | 'style' | 'security' | 'complexity' | 'documentation'

export interface PRReview {
  id: number
  repo_id: number
  pr_number: number
  pr_title: string | null
  pr_author: string | null
  status: ReviewStatus
  total_issues: number
  created_at: string
  completed_at: string | null
}

export interface ReviewComment {
  id: number
  file_path: string
  line_number: number | null
  severity: Severity
  category: Category
  message: string
  suggestion: string | null
}

// Full detail response (review + all its comments)
export interface ReviewDetail extends PRReview {
  commit_sha: string | null
  summary: string | null
  comments: ReviewComment[]
}

// Auth response from POST /auth/github
export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  user: {
    id: number
    username: string
    avatar_url: string | null
  }
}

// Dashboard stats (computed on frontend from API data)
export interface DashboardStats {
  totalReviews: number
  totalIssues: number
  activeRepos: number
  recentReviews: PRReview[]
}
