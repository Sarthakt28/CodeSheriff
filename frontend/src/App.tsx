import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { isAuthenticated, authApi } from '@/lib/api'
import Navbar from '@/components/Navbar'
import Login from '@/pages/Login'
import AuthCallback from '@/pages/AuthCallback'
import Dashboard from '@/pages/Dashboard'
import Repositories from '@/pages/Repositories'
import Reviews from '@/pages/Reviews'
import ReviewDetail from '@/pages/ReviewDetail'
import type { User } from '@/types'

// ── Protected Route Guard ───────────────────────────────────────────
// Wraps protected pages. If no JWT token → redirect to /login.
// Uses <Outlet /> to render child routes when authenticated.
function ProtectedRoute() {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

// ── Dashboard Layout ────────────────────────────────────────────────
// Wraps all protected pages with the Navbar + main content area.
function DashboardLayout({ user }: { user: User | null }) {
  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar user={user} />
      <main className="pb-16">
        <Outlet />
      </main>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)

  // Fetch authenticated user profile once on app load
  useEffect(() => {
    if (isAuthenticated()) {
      authApi.me()
        .then((res) => setUser(res.data))
        .catch(() => {
          // Token invalid/expired — the response interceptor in api.ts
          // will handle the 401 by clearing token and redirecting to /login
        })
    }
  }, [])

  return (
    <BrowserRouter>
      <Routes>

        {/* ── Public routes ────────────────────────────────────── */}
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />

        {/* ── Protected routes (require JWT) ───────────────────── */}
        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardLayout user={user} />}>
            <Route path="/dashboard"       element={<Dashboard />} />
            <Route path="/repositories"    element={<Repositories />} />
            <Route path="/reviews"         element={<Reviews />} />
            <Route path="/reviews/:id"     element={<ReviewDetail />} />
          </Route>
        </Route>

        {/* ── Catch-all: redirect to dashboard or login ─────────── */}
        <Route
          path="*"
          element={<Navigate to={isAuthenticated() ? '/dashboard' : '/login'} replace />}
        />

      </Routes>
    </BrowserRouter>
  )
}
