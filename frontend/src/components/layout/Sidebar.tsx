import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  Boxes,
  FileText,
  ShieldAlert,
  BarChart3,
  Cpu,
  Settings,
  LogOut,
  Building,
  UserCheck,
  ChevronRight,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const routePreloaders: Record<string, () => Promise<any>> = {
  '/dashboard': () => import('../../pages/DashboardPage'),
  '/vendors': () => import('../../pages/VendorsPage'),
  '/batches': () => import('../../pages/BatchesPage'),
  '/documents': () => import('../../pages/DocumentsPage'),
  '/predictions': () => import('../../pages/PredictionsPage'),
  '/analytics': () => import('../../pages/AnalyticsPage'),
  '/vendor-portal': () => import('../../pages/VendorPortalPage'),
  '/settings': () => import('../../pages/SettingsPage'),
};

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handlePreload = (path: string) => {
    routePreloaders[path]?.();
  };

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Vendors', path: '/vendors', icon: Building2 },
    { label: 'Batches', path: '/batches', icon: Boxes },
    { label: 'Documents', path: '/documents', icon: FileText },
    { label: 'Risk Predictions', path: '/predictions', icon: ShieldAlert },
    { label: 'Analytics', path: '/analytics', icon: BarChart3 },
    {
      label: 'Supplier Portal',
      path: '/vendor-portal',
      icon: UserCheck,
      badge: 'Portal',
    },
    { label: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 h-screen sticky top-0 border-r border-slate-800/80 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-700 via-blue-600 to-indigo-500 flex items-center justify-center text-white font-black text-lg shadow-md shadow-blue-500/20 border border-blue-400/30">
            <span className="tracking-tight">V</span>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-white text-base tracking-tight">VendorIQ</span>
              <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30">
                PRO
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">Batch Risk &amp; Qualification</p>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Core Workflows
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onMouseEnter={() => handlePreload(item.path)}
              onFocus={() => handlePreload(item.path)}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150 group ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-bold'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 flex-shrink-0 group-hover:scale-110 transition-transform" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Company & User Details */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40 space-y-2">
        {/* Company Card (Dynamic, not hardcoded) */}
        <div className="px-3 py-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 flex-shrink-0">
              <Building className="w-3.5 h-3.5" />
            </div>
            <div className="truncate">
              <p className="text-xs font-bold text-slate-200 truncate">
                {user?.company_name || 'VendorIQ Enterprise'}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                </span>
                <span className="text-[10px] text-slate-400 font-mono">Neon Cloud • Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* User Card & Logout */}
        <div className="flex items-center justify-between px-2 pt-1">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-blue-700 to-indigo-600 border border-blue-400/30 text-white flex items-center justify-center text-xs font-bold shadow-sm">
              {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
            </div>
            <div className="truncate">
              <p className="text-xs font-semibold text-slate-200 truncate">
                {user?.full_name || user?.email?.split('@')[0] || 'Administrator'}
              </p>
              <p className="text-[10px] text-slate-500 truncate">{user?.email || 'admin@vendoriq.com'}</p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log out session"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
