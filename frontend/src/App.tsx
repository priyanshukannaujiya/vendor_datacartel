import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { VendorsPage } from './pages/VendorsPage';
import { VendorDetailPage } from './pages/VendorDetailPage';
import { BatchesPage } from './pages/BatchesPage';
import { BatchDetailPage } from './pages/BatchDetailPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { PredictionsPage } from './pages/PredictionsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { MachineIntelligencePage } from './pages/MachineIntelligencePage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <Routes>
      {/* Public Auth Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

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
  );
};

export default App;
