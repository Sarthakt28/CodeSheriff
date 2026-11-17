import axios from 'axios'

// ── Token helpers ───────────────────────────────────────────────────
const TOKEN_KEY = 'codesheriff_token'

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string): void => localStorage.setItem(TOKEN_KEY, token)
export const removeToken = (): void => localStorage.removeItem(TOKEN_KEY)

export const isAuthenticated = (): boolean => !!getToken()

// ── Axios instance ──────────────────────────────────────────────────
// Base URL: uses VITE_API_URL if set, or defaults to production backend on Render
// when deployed, or falls back to '' for local dev (Vite proxy forwards /api and /auth).
const rawApiUrl =
  import.meta.env.VITE_API_URL ||
  (typeof window !== 'undefined' &&
  !window.location.hostname.includes('localhost') &&
  !window.location.hostname.includes('127.0.0.1')
    ? 'https://codesheriff-api-wgg8.onrender.com'
    : '')

const API_BASE_URL = rawApiUrl
  ? rawApiUrl.startsWith('http')
    ? rawApiUrl
    : `https://${rawApiUrl}`
  : ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000, // 15s timeout — prevents hanging requests
})

// ── Request interceptor ─────────────────────────────────────────────
// Runs BEFORE every API call. Injects the JWT automatically.
api.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── Response interceptor ────────────────────────────────────────────
// Runs AFTER every response. Handles auth errors globally.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear auth state and redirect to login
      removeToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default api

// ── Typed API calls ─────────────────────────────────────────────────
// These are thin wrappers that provide type safety on return values.

import type { AuthResponse, Repository, PRReview, ReviewDetail, User } from '@/types'

export const authApi = {
  githubCallback: (code: string) =>
    api.get<AuthResponse>(`/auth/github?code=${code}`),
  me: () => api.get<User>('/auth/me'),
}

export const reposApi = {
  list: () => api.get<Repository[]>('/api/repos'),
  sync: () => api.post<{ synced: number; repos: string[] }>('/api/repos/sync'),
  toggle: (repoId: number) =>
    api.patch<Repository>(`/api/repos/${repoId}/toggle`),
}

export const reviewsApi = {
  list: (skip = 0, limit = 20) =>
    api.get<PRReview[]>(`/api/reviews?skip=${skip}&limit=${limit}`),
  get: (reviewId: number) =>
    api.get<ReviewDetail>(`/api/reviews/${reviewId}`),
}
