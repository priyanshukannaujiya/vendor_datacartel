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
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Vendors', path: '/vendors', icon: Building2 },
    { label: 'Batches', path: '/batches', icon: Boxes },
    { label: 'Documents', path: '/documents', icon: FileText },
    { label: 'Risk Predictions', path: '/predictions', icon: ShieldAlert },
    { label: 'Analytics', path: '/analytics', icon: BarChart3 },
    {
      label: 'Machine Intelligence',
      path: '/machine-intelligence',
      icon: Cpu,
      badge: 'BETA',
    },
    { label: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 h-screen sticky top-0 border-r border-slate-800">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
            <span className="tracking-tight">V</span>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-white text-base tracking-tight">VendorIQ</span>
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700/50">
                SaaS
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Batch Intelligence</p>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Core Operations
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                  isActive
                    ? 'bg-blue-600 text-white font-semibold shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Company & User Details */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/30 space-y-2">
        {/* Company Card */}
        <div className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 flex items-center justify-between">
          <div className="flex items-center gap-2 overflow-hidden">
            <Building className="w-4 h-4 text-blue-400 flex-shrink-0" />
            <div className="truncate">
              <p className="text-xs font-medium text-slate-200 truncate">
                BioPharma Core Corp
              </p>
              <p className="text-[10px] text-slate-400">Tenant: US-East-1</p>
            </div>
          </div>
        </div>

        {/* User Card & Logout */}
        <div className="flex items-center justify-between px-2 pt-1">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-7 h-7 rounded-full bg-blue-900/60 border border-blue-500/40 text-blue-300 flex items-center justify-center text-xs font-semibold">
              {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
            </div>
            <div className="truncate">
              <p className="text-xs font-medium text-slate-200 truncate">
                {user?.full_name || user?.email?.split('@')[0] || 'User'}
              </p>
              <p className="text-[10px] text-slate-400 truncate">{user?.email || 'admin@vendoriq.com'}</p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
