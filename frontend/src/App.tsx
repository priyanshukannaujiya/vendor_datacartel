import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { ProtectedRoute } from './components/common/ProtectedRoute';

// Lazy-loaded pages for optimized code splitting and instant initial loading
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then(m => ({ default: m.RegisterPage })));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage').then(m => ({ default: m.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage').then(m => ({ default: m.ResetPasswordPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const VendorsPage = lazy(() => import('./pages/VendorsPage').then(m => ({ default: m.VendorsPage })));
const VendorDetailPage = lazy(() => import('./pages/VendorDetailPage').then(m => ({ default: m.VendorDetailPage })));
const BatchesPage = lazy(() => import('./pages/BatchesPage').then(m => ({ default: m.BatchesPage })));
const BatchDetailPage = lazy(() => import('./pages/BatchDetailPage').then(m => ({ default: m.BatchDetailPage })));
const DocumentsPage = lazy(() => import('./pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })));
const PredictionsPage = lazy(() => import('./pages/PredictionsPage').then(m => ({ default: m.PredictionsPage })));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage').then(m => ({ default: m.AnalyticsPage })));
const MachineIntelligencePage = lazy(() => import('./pages/MachineIntelligencePage').then(m => ({ default: m.MachineIntelligencePage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const VendorPortalPage = lazy(() => import('./pages/VendorPortalPage').then(m => ({ default: m.VendorPortalPage })));

// Sleek fallback loader while route chunk is downloaded
const PageLoadingFallback: React.FC = () => (
  <div className="flex h-[60vh] w-full flex-col items-center justify-center gap-3">
    <div className="h-9 w-9 animate-spin rounded-full border-3 border-brand-500 border-t-transparent shadow-sm" />
    <span className="text-xs font-medium uppercase tracking-wider text-slate-400">Loading module...</span>
  </div>
);

export const App: React.FC = () => {
  return (
    <Suspense fallback={<PageLoadingFallback />}>
      <Routes>
        {/* Public Auth & Portal Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/vendor-portal" element={<VendorPortalPage />} />

        {/* Protected App Routes */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/vendors" element={<VendorsPage />} />
            <Route path="/vendors/:id" element={<VendorDetailPage />} />
            <Route path="/batches" element={<BatchesPage />} />
            <Route path="/batches/:id" element={<BatchDetailPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/predictions" element={<PredictionsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/machine-intelligence" element={<MachineIntelligencePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
};

export default App;

