import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  TrendingUp,
  PieChart as PieIcon,
  ShieldCheck,
  RefreshCw,
  Award,
  Layers,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
} from 'recharts';
import { analyticsApi } from '../api/client';
import { DashboardAnalytics } from '../types';

export const AnalyticsPage: React.FC = () => {
  const { data: analytics, isLoading, refetch } = useQuery<DashboardAnalytics>({
    queryKey: ['analytics-full'],
    queryFn: () => analyticsApi.getDashboardAnalytics(),
  });

  if (isLoading || !analytics) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm text-slate-500 font-medium">Synthesizing platform analytics...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Quality & Compliance Analytics</h1>
          <p className="text-sm text-slate-500 mt-1">
            Supplier portfolio benchmarking, historical purity drift, and compliance trajectory.
          </p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary self-start">
          <RefreshCw className="w-4 h-4 mr-1.5" />
          <span>Sync Analytics</span>
        </button>
      </div>

      {/* Top 3 Analytical Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="v-card p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Portfolio Health Index
          </span>
          <div className="text-3xl font-extrabold text-slate-900 mt-2">87.4 / 100</div>
          <p className="text-xs text-emerald-600 mt-1 font-medium">
            +3.2% vs previous quarter across all suppliers
          </p>
        </div>

        <div className="v-card p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Average Assay Purity
          </span>
          <div className="text-3xl font-extrabold text-slate-900 mt-2">99.18%</div>
          <p className="text-xs text-blue-600 mt-1 font-medium">
            Benchmark threshold requirement: ≥99.00%
          </p>
        </div>

        <div className="v-card p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Automated Clearance Rate
          </span>
          <div className="text-3xl font-extrabold text-slate-900 mt-2">91.7%</div>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Batches approved autonomously without human override
          </p>
        </div>
      </div>

      {/* Detailed Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="v-card p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">Batch Approval Trend</h3>
          <p className="text-xs text-slate-500 mb-4">Historical resolution breakdown</p>
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

        <div className="v-card p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">Monthly Purity & Compliance Trajectory</h3>
          <p className="text-xs text-slate-500 mb-4">Mean purity versus regulatory baseline</p>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.quality_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[90, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
                <Line type="monotone" dataKey="average_purity" stroke="#2563eb" strokeWidth={2.5} name="Average Purity (%)" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="compliance_rate" stroke="#10b981" strokeWidth={2.5} name="Compliance Rate (%)" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
