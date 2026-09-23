import { Navigate, Route, Routes } from 'react-router-dom'

import { Footer } from '@/components/layout/Footer'
import { Header } from '@/components/layout/Header'
import { ScrollToTop } from '@/components/layout/ScrollToTop'
import { AppShell } from '@/components/app/AppShell'
import { ProtectedRoute } from '@/components/app/ProtectedRoute'
import { AboutPage } from '@/pages/AboutPage'
import { CaseDetailPage } from '@/pages/app/CaseDetailPage'
import { CasesQueuePage } from '@/pages/app/CasesQueuePage'
import { NewCasePage } from '@/pages/app/NewCasePage'
import { UsersAdminPage } from '@/pages/app/UsersAdminPage'
import { ContactPage } from '@/pages/ContactPage'
import { HomePage } from '@/pages/HomePage'
import { HowItWorksPage } from '@/pages/HowItWorksPage'
import { LoginPage } from '@/pages/LoginPage'
import { SecurityPage } from '@/pages/SecurityPage'
import { SolutionsPage } from '@/pages/SolutionsPage'

function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}

function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <SiteLayout>
              <HomePage />
            </SiteLayout>
          }
        />
        <Route
          path="/solutions"
          element={
            <SiteLayout>
              <SolutionsPage />
            </SiteLayout>
          }
        />
        <Route
          path="/how-it-works"
          element={
            <SiteLayout>
              <HowItWorksPage />
            </SiteLayout>
          }
        />
        <Route
          path="/security"
          element={
            <SiteLayout>
              <SecurityPage />
            </SiteLayout>
          }
        />
        <Route
          path="/about"
          element={
            <SiteLayout>
              <AboutPage />
            </SiteLayout>
          }
        />
        <Route
          path="/contact"
          element={
            <SiteLayout>
              <ContactPage />
            </SiteLayout>
          }
        />

        {/* Authenticated underwriting application */}
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <AppShell>
                <Navigate to="/app/cases" replace />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/cases"
          element={
            <ProtectedRoute>
              <AppShell>
                <CasesQueuePage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/cases/new"
          element={
            <ProtectedRoute roles={['loan_officer', 'admin']}>
              <AppShell>
                <NewCasePage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/cases/:caseId"
          element={
            <ProtectedRoute>
              <AppShell>
                <CaseDetailPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/users"
          element={
            <ProtectedRoute roles={['admin']}>
              <AppShell>
                <UsersAdminPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  )
}

export default App
