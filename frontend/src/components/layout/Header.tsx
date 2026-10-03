import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Bell, ShieldCheck, CheckCircle2, Plus, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Header: React.FC = () => {
  const location = useLocation();
  const { user } = useAuth();

  const getPageTitle = (pathname: string) => {
    if (pathname.startsWith('/dashboard')) return 'Dashboard';
    if (pathname.startsWith('/vendors/')) return 'Vendor Profile';
    if (pathname.startsWith('/vendors')) return 'Vendor Directory';
    if (pathname.startsWith('/batches/')) return 'Batch Assessment';
    if (pathname.startsWith('/batches')) return 'Batches Compliance';
    if (pathname.startsWith('/documents')) return 'Document Repository';
    if (pathname.startsWith('/predictions')) return 'Risk Predictions';
    if (pathname.startsWith('/analytics')) return 'Analytics & Insights';
    if (pathname.startsWith('/machine-intelligence')) return 'Machine Intelligence';
    if (pathname.startsWith('/settings')) return 'System Settings';
    return 'VendorIQ';
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200/80 px-8 flex items-center justify-between sticky top-0 z-20">
      {/* Title & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
          {getPageTitle(location.pathname)}
        </h1>
        <div className="h-4 w-px bg-slate-200"></div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
          <span>Platform</span>
          <span>/</span>
          <span className="text-slate-800 font-semibold">{getPageTitle(location.pathname)}</span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* System Health Indicators */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-xs text-slate-600">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="font-medium text-slate-700">FastAPI + Neon DB</span>
          <span className="text-slate-300">•</span>
          <span className="text-blue-600 font-semibold">Kimi K3 Online</span>
        </div>

        {/* Quick Batch Assessment Action */}
        <Link
          to="/batches"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Batch</span>
        </Link>
      </div>
    </header>
  );
};
