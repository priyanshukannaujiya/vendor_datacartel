import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Users,
  Boxes,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  ArrowRight,
  TrendingUp,
  RefreshCw,
  ExternalLink,
  Mail,
  Sparkles,
  Building2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
  LineChart,
  Line,
} from 'recharts';
import { analyticsApi, batchApi, vendorApi } from '../api/client';
import { DashboardAnalytics, Batch, Vendor } from '../types';

export const DashboardPage: React.FC = () => {
  const {
    data: analytics,
    isLoading,
    isError,
    refetch,
  } = useQuery<DashboardAnalytics>({
    queryKey: ['dashboard-analytics'],
    queryFn: () => analyticsApi.getDashboardAnalytics(),
    refetchInterval: 15000,
  });

  const getRiskBadge = (level?: string) => {
    switch (level?.toUpperCase()) {
      case 'LOW':
        return <span className="badge badge-risk-low">LOW RISK</span>;
      case 'MEDIUM':
        return <span className="badge badge-risk-medium">MEDIUM RISK</span>;
      case 'HIGH':
        return <span className="badge badge-risk-high">HIGH RISK</span>;
      case 'CRITICAL':
        return <span className="badge badge-risk-critical">CRITICAL RISK</span>;
      default:
        return <span className="badge badge-pending">PENDING</span>;
    }
  };

  const getDecisionBadge = (decision?: string) => {
    switch (decision?.toUpperCase()) {
      case 'APPROVED':
        return <span className="badge badge-approved">APPROVED</span>;
      case 'REJECTED':
        return <span className="badge badge-rejected">REJECTED</span>;
      case 'NEEDS_REVIEW':
        return <span className="badge badge-needs-review">NEEDS REVIEW</span>;
      default:
        return <span className="badge badge-pending">PENDING</span>;
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px]">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm text-slate-500 font-medium">Aggregating live vendor & batch intelligence...</p>
      </div>
    );
  }

  if (isError || !analytics) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-rose-200 shadow-subtle">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-900">Failed to load analytics</h3>
        <p className="text-sm text-slate-500 mt-1 mb-4">
          Ensure the FastAPI backend is running and the database is accessible.
        </p>
        <button onClick={() => refetch()} className="btn-primary">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry Connection
        </button>
      </div>
    );
  }

  const kpis = [
    {
      title: 'Total Vendors',
      value: analytics.total_vendors,
      icon: Users,
      trend: 'Registered supplier records',
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      title: 'Batches Processed',
      value: analytics.batches_processed,
      icon: Boxes,
      trend: 'Recorded batch assessments',
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
    },
    {
      title: 'Approved Batches',
      value: analytics.approved_batches,
      icon: CheckCircle,
      trend: analytics.batches_processed > 0
        ? `${((analytics.approved_batches / analytics.batches_processed) * 100).toFixed(0)}% approval rate`
        : 'No batch assessments recorded',
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
    },
    {
      title: 'Rejected Batches',
      value: analytics.rejected_batches,
      icon: XCircle,
      trend: 'Recorded rejected decisions',
      color: 'text-rose-600',
      bg: 'bg-rose-50',
    },
    {
      title: 'High Risk Vendors',
      value: analytics.high_risk_vendors,
      icon: AlertTriangle,
      trend: 'Based on available risk scores',
      color: 'text-orange-600',
      bg: 'bg-orange-50',
    },
    {
      title: 'Pending Reviews',
      value: analytics.pending_reviews,
      icon: Clock,
      trend: 'Awaiting assessment or decision',
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Vendor Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Monitor supplier quality, batch compliance and vendor risk.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="btn-secondary"
            title="Refresh dashboard metrics"
          >
            <RefreshCw className="w-4 h-4 mr-1.5" />
            <span>Sync Live</span>
          </button>
          <Link to="/batches" className="btn-primary">
            <span>View All Batches</span>
            <ArrowRight className="w-4 h-4 ml-1.5" />
          </Link>
        </div>
      </div>

      {/* Onboarding Guide Card when tenant has no data yet */}
      {analytics.total_vendors === 0 && analytics.batches_processed === 0 && (
        <div className="v-card p-6 bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-white border-blue-200 shadow-subtle">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-1.5 max-w-2xl">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Welcome to VendorIQ Intelligence</span>
              </div>
              <h2 className="text-lg font-bold text-slate-900">
                Start Qualifying Raw Material Batches
              </h2>
              <p className="text-xs text-slate-600 leading-relaxed">
                VendorIQ streamlines vendor qualification without requiring suppliers to log into any portal. Suppliers receive document requests via Google SMTP email and can reply with attachments (CoAs, SDS, ISO certifications) that are automatically ingested into your database.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link to="/vendors" className="btn-primary bg-indigo-600 hover:bg-indigo-700 text-xs whitespace-nowrap">
                <Mail className="w-3.5 h-3.5 mr-1.5" />
                <span>Invite Supplier via Email</span>
              </Link>
              <Link to="/batches" className="btn-secondary text-xs whitespace-nowrap">
                <Boxes className="w-3.5 h-3.5 mr-1.5" />
                <span>Register Batch Lot</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div key={idx} className="v-card p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-600 tracking-wider">
                  {kpi.title}
                </span>
                <div className={`p-2 rounded-lg ${kpi.bg} ${kpi.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-slate-900 tracking-tight">{kpi.value}</div>
                <div className="text-[11px] text-slate-600 mt-0.5 font-medium">{kpi.trend}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Section: 4 Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Vendor Risk Distribution */}
        <div className="v-card p-5">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Vendor Risk Distribution</h3>
              <p className="text-xs text-slate-500">Breakdown of supplier portfolio risk tiers</p>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100/80 text-slate-700 text-xs font-semibold border border-slate-200/60">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>
                {(analytics.vendor_risk_distribution || []).reduce((sum, item) => sum + (item.value || 0), 0)} Suppliers
              </span>
            </div>
          </div>

          <div className="relative h-60 w-full flex items-center justify-center mt-1">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={analytics.vendor_risk_distribution || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={92}
                  paddingAngle={(analytics.vendor_risk_distribution || []).some((item) => (item.value || 0) > 0) ? 3 : 0}
                  cornerRadius={4}
                  dataKey="value"
                  stroke="#ffffff"
                  strokeWidth={2}
                >
                  {(analytics.vendor_risk_distribution || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: any, name: any) => {
                    const total = (analytics.vendor_risk_distribution || []).reduce(
                      (sum, item) => sum + (item.value || 0),
                      0
                    );
                    const pct = total > 0 ? Math.round((Number(value) / total) * 100) : 0;
                    return [`${value} Vendors (${pct}%)`, name];
                  }}
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '10px',
                    border: '1px solid #1e293b',
                    color: '#fff',
                    fontSize: '12px',
                    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.3)',
                    padding: '8px 12px',
                  }}
                  itemStyle={{ color: '#f8fafc', fontWeight: 500 }}
                />
              </PieChart>
            </ResponsiveContainer>

            {/* Centered Total Display in the Donut Hole */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-1">
              <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                {(analytics.vendor_risk_distribution || []).reduce((sum, item) => sum + (item.value || 0), 0)}
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mt-0.5">
                Total Vendors
              </span>
            </div>
          </div>

          {/* Structured Modern Legend Grid */}
          <div className="grid grid-cols-2 gap-2 mt-2 pt-3 border-t border-slate-100">
            {(analytics.vendor_risk_distribution || []).map((item, idx) => {
              const total = (analytics.vendor_risk_distribution || []).reduce(
                (sum, it) => sum + (it.value || 0),
                0
              );
              const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
              return (
                <div
                  key={idx}
                  className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-50/80 hover:bg-slate-100/90 transition-colors border border-slate-100"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-xs font-medium text-slate-700 truncate" title={item.name}>
                      {item.name.replace(' Risk', '')}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 pl-1.5">
                    <span className="text-xs font-bold text-slate-900">{item.value}</span>
                    <span className="text-[10px] font-semibold text-slate-500 bg-white px-1.5 py-0.5 rounded border border-slate-200/70">
                      {pct}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Risk Trend */}
        <div className="v-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Risk Trend</h3>
              <p className="text-xs text-slate-500">Historical vendor risk index across batches</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={analytics.risk_trend || []}>
                <defs>
                  <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                <Area type="monotone" dataKey="avg_risk" stroke="#2563eb" strokeWidth={2} fillOpacity={1} fill="url(#riskGradient)" name="Avg Risk Score" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. Batch Approval Trend */}
        <div className="v-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Batch Approval Trend</h3>
              <p className="text-xs text-slate-500">Approved vs rejected vs needs review batches</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.batch_approval_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
                <Bar dataKey="approved" fill="#10b981" name="Approved" radius={[4, 4, 0, 0]} />
                <Bar dataKey="rejected" fill="#ef4444" name="Rejected" radius={[4, 4, 0, 0]} />
                <Bar dataKey="review" fill="#f59e0b" name="Needs Review" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Quality Trend */}
        <div className="v-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Quality Trend</h3>
              <p className="text-xs text-slate-500">Average material purity and compliance rate</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.quality_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[90, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
                <Line type="monotone" dataKey="average_purity" stroke="#3b82f6" strokeWidth={2} name="Avg Purity (%)" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="compliance_rate" stroke="#10b981" strokeWidth={2} name="Compliance Rate (%)" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Tables Section: High Risk Vendors & Recent Batch Assessments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* High Risk Vendors Table */}
        <div className="v-card overflow-hidden">
          <div className="v-card-header">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">High Risk Vendors</h3>
              <p className="text-xs text-slate-500">Suppliers requiring immediate qualification audit</p>
            </div>
            <Link to="/vendors" className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Vendor</th>
                  <th>Risk Score</th>
                  <th>Approval Rate</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {((analytics.high_risk_vendors_list || []).length > 0) ? (
                  (analytics.high_risk_vendors_list || []).map((vendor) => (
                    <tr key={vendor.id}>
                      <td className="font-medium text-slate-900">
                        <div>{vendor.name}</div>
                        <div className="text-xs text-slate-600">{vendor.vendor_code}</div>
                      </td>
                      <td>
                        <span className="font-semibold text-rose-600">{vendor.risk_score?.toFixed(1) ?? '—'}</span>
                      </td>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-rose-500 h-1.5 rounded-full"
                              style={{ width: `${vendor.approval_rate ?? 0}%` }}
                            ></div>
                          </div>
                          <span className="text-xs text-slate-600">{vendor.approval_rate == null ? '—' : `${vendor.approval_rate}%`}</span>
                        </div>
                      </td>
                      <td>{getRiskBadge(vendor.risk_level)}</td>
                      <td>
                        <Link
                          to={`/vendors/${vendor.id}`}
                          className="btn-ghost text-xs"
                        >
                          Audit Profile
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="text-center py-6 text-slate-600">
                      No high-risk vendors flagged currently.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Batch Assessments Table */}
        <div className="v-card overflow-hidden">
          <div className="v-card-header">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Recent Batch Assessments</h3>
              <p className="text-xs text-slate-500">Live feed of batch evaluations and AI decisions</p>
            </div>
            <Link to="/batches" className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Batch Number</th>
                  <th>Vendor</th>
                  <th>ML Risk</th>
                  <th>Decision</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {((analytics.recent_batches_list || []).length > 0) ? (
                  (analytics.recent_batches_list || []).map((batch) => (
                    <tr key={batch.id}>
                      <td className="font-mono text-xs font-semibold text-slate-900">
                        {batch.batch_number}
                      </td>
                      <td className="text-slate-700">
                        {batch.vendor?.name || 'Vendor not recorded'}
                      </td>
                      <td>{getRiskBadge(batch.risk_level)}</td>
                      <td>{getDecisionBadge(batch.decision || batch.decision_status)}</td>
                      <td>
                        <Link
                          to={`/batches/${batch.id}`}
                          className="btn-ghost text-xs text-blue-600 font-semibold"
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="text-center py-6 text-slate-600">
                      No batches assessed yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
