import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { ShieldCheck, Plus, CheckCircle2, Building, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Header: React.FC = () => {
  const location = useLocation();
  const { user } = useAuth();

  const getPageTitle = (pathname: string) => {
    if (pathname.startsWith('/dashboard')) return 'Executive Dashboard';
    if (pathname.startsWith('/vendors/')) return 'Supplier Dossier';
    if (pathname.startsWith('/vendors')) return 'Supplier Directory';
    if (pathname.startsWith('/batches/')) return 'Batch Inspection & Decision';
    if (pathname.startsWith('/batches')) return 'Batch Compliance Lots';
    if (pathname.startsWith('/documents')) return 'Analytical Document Repository';
    if (pathname.startsWith('/predictions')) return 'AI Risk Simulation';
    if (pathname.startsWith('/analytics')) return 'Performance Analytics';
    if (pathname.startsWith('/machine-intelligence')) return 'Scientific Model Engine';
    if (pathname.startsWith('/settings')) return 'Organization Settings';
    return 'VendorIQ';
  };

  return (
    <header className="h-16 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-6 lg:px-8 flex items-center justify-between sticky top-0 z-20 transition-all">
      {/* Title & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <h1 className="text-base font-bold text-slate-900 tracking-tight">
          {getPageTitle(location.pathname)}
        </h1>
        <div className="h-4 w-px bg-slate-200 hidden sm:block"></div>
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500 font-medium">
          <span>VendorIQ</span>
          <span>/</span>
          <span className="text-blue-600 font-semibold">{getPageTitle(location.pathname)}</span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Live Multi-service Status Pill */}
        <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600 shadow-xs">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="font-semibold text-slate-700">API Live</span>
          <span className="text-slate-300">•</span>
          <span className="text-slate-600 font-medium">{user?.company_name || 'Enterprise'}</span>
        </div>

        {/* Quick Batch Assessment Action */}
        <Link
          to="/batches"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-all duration-150 active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Batch</span>
        </Link>
      </div>
    </header>
  );
};
