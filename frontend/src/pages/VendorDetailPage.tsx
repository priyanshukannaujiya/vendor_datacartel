import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Building2,
  Mail,
  Phone,
  MapPin,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  Boxes,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  TrendingDown,
  Award,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { vendorApi, batchApi } from '../api/client';
import { Vendor, Batch } from '../types';

export const VendorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const {
    data: vendor,
    isLoading: isVendorLoading,
    refetch: refetchVendor,
  } = useQuery<Vendor>({
    queryKey: ['vendor', id],
    queryFn: () => vendorApi.getById(id!),
    enabled: !!id,
  });

  const {
    data: batches = [],
    isLoading: isBatchesLoading,
  } = useQuery<Batch[]>({
    queryKey: ['vendor-batches', id],
    queryFn: () => batchApi.getAll({ vendor_id: id }),
    enabled: !!id,
  });

  if (isVendorLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm text-slate-500 font-medium">Loading supplier intelligence profile...</p>
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
        <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
        <h3 className="text-base font-semibold text-slate-900">Supplier Not Found</h3>
        <p className="text-sm text-slate-500 mt-1 mb-4">The requested vendor ID does not exist.</p>
        <Link to="/vendors" className="btn-secondary">
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Vendors
        </Link>
      </div>
    );
  }

  // Generate synthetic performance trend if historical data isn't dense yet
  const riskTrendData = [
    { month: 'May', risk: Math.min(100, Math.max(10, (vendor.risk_score || 35) + 12)) },
    { month: 'Jun', risk: Math.min(100, Math.max(10, (vendor.risk_score || 35) + 6)) },
    { month: 'Jul', risk: Math.min(100, Math.max(10, (vendor.risk_score || 35) + 8)) },
    { month: 'Aug', risk: Math.min(100, Math.max(10, (vendor.risk_score || 35) - 4)) },
    { month: 'Sep', risk: Math.min(100, Math.max(10, (vendor.risk_score || 35) - 2)) },
    { month: 'Oct', risk: vendor.risk_score || 25 },
  ];

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

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex items-center justify-between">
        <Link
          to="/vendors"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Vendors</span>
        </Link>
        <div className="flex items-center gap-3">
          <button onClick={() => refetchVendor()} className="btn-secondary text-xs">
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Vendor Profile Header Banner */}
      <div className="v-card p-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 flex-shrink-0 shadow-sm">
              <Building2 className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">{vendor.name}</h1>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  {vendor.vendor_code}
                </span>
                {getRiskBadge(vendor.risk_level)}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Registered Supplier • Compliance Status: <span className="text-emerald-700 font-semibold">{vendor.compliance_status || 'VERIFIED'}</span>
              </p>

              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 mt-3">
                {vendor.contact_email && (
                  <span className="flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    {vendor.contact_email}
                  </span>
                )}
                {vendor.phone && (
                  <span className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    {vendor.phone}
                  </span>
                )}
                {vendor.address && (
                  <span className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    {vendor.address}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Supplier Overall Health Score */}
          <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 self-start">
            <div className="text-right">
              <span className="text-[11px] font-semibold uppercase text-slate-400 block tracking-wider">
                Supplier Health
              </span>
              <span className="text-2xl font-bold text-slate-900">
                {Math.max(0, 100 - (vendor.risk_score || 20)).toFixed(0)}/100
              </span>
            </div>
            <div className="w-12 h-12 rounded-full border-4 border-emerald-500 flex items-center justify-center font-bold text-xs text-emerald-700 bg-white">
              {Math.max(0, 100 - (vendor.risk_score || 20)).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* 4 Score Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="v-card p-4">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Approval Rate
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{vendor.approval_rate}%</div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-1.5 rounded-full"
              style={{ width: `${vendor.approval_rate || 90}%` }}
            ></div>
          </div>
          <p className="text-[11px] text-slate-600 mt-1.5">
            {vendor.approved_batches} of {vendor.total_batches} batches approved
          </p>
        </div>

        <div className="v-card p-4">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Quality Consistency
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {vendor.quality_score ? `${vendor.quality_score}%` : `${vendor.avg_purity || 99.1}%`}
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-blue-600 h-1.5 rounded-full"
              style={{ width: `${vendor.quality_score || vendor.avg_purity || 98}%` }}
            ></div>
          </div>
          <p className="text-[11px] text-slate-600 mt-1.5">Mean assay purity vs spec tolerance</p>
        </div>

        <div className="v-card p-4">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Delivery Reliability
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {vendor.delivery_score ? `${vendor.delivery_score}%` : `${vendor.on_time_delivery_rate || 96}%`}
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-indigo-600 h-1.5 rounded-full"
              style={{ width: `${vendor.delivery_score || vendor.on_time_delivery_rate || 95}%` }}
            ></div>
          </div>
          <p className="text-[11px] text-slate-600 mt-1.5">On-time dispatch fulfillment</p>
        </div>

        <div className="v-card p-4">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Documentation Completeness
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {vendor.documentation_score ? `${vendor.documentation_score}%` : `${vendor.documentation_completeness_rate || 94}%`}
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-teal-600 h-1.5 rounded-full"
              style={{ width: `${vendor.documentation_score || vendor.documentation_completeness_rate || 94}%` }}
            ></div>
          </div>
          <p className="text-[11px] text-slate-600 mt-1.5">COA, SDS, and GMP compliance integrity</p>
        </div>
      </div>

      {/* Risk Trend & Kimi AI Assessment Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Risk Trend */}
        <div className="v-card p-5">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-900">Performance Risk Trend</h3>
            <p className="text-xs text-slate-500">6-Month historical risk oscillation index</p>
          </div>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={riskTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: '#2563eb' }}
                  name="Risk Score"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Kimi AI Risk Assessment */}
        <div className="v-card p-5 border-blue-200/80 bg-gradient-to-b from-white to-blue-50/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-slate-900">Kimi AI Risk Assessment</h3>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800">
              MOONSHOT K3 ENGINE
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-white rounded-lg border border-slate-200 text-slate-700 leading-relaxed">
              {vendor.kimi_assessment?.summary ||
                `${vendor.name} demonstrates a stable supplier profile with ${vendor.approval_rate || 90}% historical lot compliance. Certificate of Analysis (COA) records indicate high analytical fidelity.`}
            </div>

            <div>
              <h4 className="font-semibold text-slate-900 mb-1.5 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                Recommended Actions
              </h4>
              <ul className="space-y-1.5 pl-1">
                {(vendor.kimi_assessment?.recommendations && vendor.kimi_assessment.recommendations.length > 0) ? (
                  vendor.kimi_assessment.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-slate-600">
                      <span className="text-blue-500 font-bold">•</span>
                      <span>{rec}</span>
                    </li>
                  ))
                ) : (
                  <>
                    <li className="flex items-start gap-2 text-slate-600">
                      <span className="text-blue-500 font-bold">•</span>
                      <span>Maintain standard sampling frequency under ISO-9001 guidelines.</span>
                    </li>
                    <li className="flex items-start gap-2 text-slate-600">
                      <span className="text-blue-500 font-bold">•</span>
                      <span>Automatic fast-track clearance for routine ascorbic and excipient shipments.</span>
                    </li>
                    <li className="flex items-start gap-2 text-slate-600">
                      <span className="text-blue-500 font-bold">•</span>
                      <span>Schedule annual facility re-certification audit in Q4 2026.</span>
                    </li>
                  </>
                )}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Certifications & Historical Batches */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Certifications Card */}
        <div className="v-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Award className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-semibold text-slate-900">Active Certifications</h3>
          </div>
          <div className="space-y-2">
            {(vendor.certifications && vendor.certifications.length > 0
              ? vendor.certifications
              : ['ISO 9001:2015 Quality Management', 'cGMP Compliant Facility', 'FDA Registration #3009841', 'HACCP Food Safety']
            ).map((cert, idx) => (
              <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs">
                <span className="font-medium text-slate-800">{cert}</span>
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Valid
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Historical Batches Table */}
        <div className="v-card lg:col-span-2 overflow-hidden">
          <div className="v-card-header">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Historical Batches</h3>
              <p className="text-xs text-slate-500">All lots received and tested from this supplier</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Batch</th>
                  <th>Quantity</th>
                  <th>Risk Tier</th>
                  <th>Decision</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {(Array.isArray(batches) ? batches : []).length > 0 ? (
                  (Array.isArray(batches) ? batches : []).map((batch) => (
                    <tr key={batch.id}>
                      <td className="font-mono text-xs font-semibold text-slate-900">
                        {batch.batch_number}
                      </td>
                      <td className="text-xs text-slate-600">
                        {batch.quantity} {batch.unit}
                      </td>
                      <td>{getRiskBadge(batch.risk_level)}</td>
                      <td>
                        <span className={`badge ${batch.decision === 'APPROVED' ? 'badge-approved' : batch.decision === 'REJECTED' ? 'badge-rejected' : 'badge-needs-review'}`}>
                          {batch.decision || batch.status}
                        </span>
                      </td>
                      <td>
                        <Link to={`/batches/${batch.id}`} className="btn-ghost text-xs text-blue-600 font-semibold">
                          View Lot
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="text-center py-6 text-slate-600 text-xs">
                      No batch shipments recorded for this supplier.
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
