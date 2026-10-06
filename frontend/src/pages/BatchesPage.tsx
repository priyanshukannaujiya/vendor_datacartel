import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Boxes,
  Search,
  Filter,
  Plus,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  AlertCircle,
  X,
  FileCheck2,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  ArrowUpRight,
  TrendingUp,
  Layers,
} from 'lucide-react';
import { batchApi, vendorApi } from '../api/client';
import { Batch, Vendor } from '../types';

export const BatchesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // New Batch Form State - Note: Materials section is completely removed as requested
  const [formData, setFormData] = useState({
    batch_number: `VC-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`,
    vendor_id: '',
    quantity: 1000,
    unit: 'kg',
    price_per_unit: 18.5,
    manufacturing_date: new Date().toISOString().split('T')[0],
    expiry_date: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
  });

  const {
    data: batches = [],
    isLoading,
    refetch,
    isFetching,
  } = useQuery<Batch[]>({
    queryKey: ['batches', statusFilter],
    queryFn: () => batchApi.getAll({ status: statusFilter || undefined }),
    staleTime: 10000,
  });

  const { data: vendors = [] } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.getAll(),
    enabled: isAddModalOpen,
    staleTime: 60000,
  });

  const createBatchMutation = useMutation({
    mutationFn: (newBatch: typeof formData) => batchApi.create(newBatch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      setIsAddModalOpen(false);
      setErrorMessage(null);
      setFormData({
        batch_number: `VC-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`,
        vendor_id: '',
        quantity: 1000,
        unit: 'kg',
        price_per_unit: 18.5,
        manufacturing_date: new Date().toISOString().split('T')[0],
        expiry_date: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
      });
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to create batch lot. Please check supplier selection.';
      setErrorMessage(msg);
    },
  });

  const handleGenerateBatchNumber = () => {
    const year = new Date().getFullYear();
    const rand = Math.floor(100 + Math.random() * 900);
    setFormData((prev) => ({ ...prev, batch_number: `VC-${year}-${rand}` }));
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (!formData.batch_number.trim() || !formData.vendor_id) {
      setErrorMessage('Please provide a Batch Number and select a Supplier.');
      return;
    }
    createBatchMutation.mutate(formData);
  };

  const batchList = Array.isArray(batches) ? batches : [];
  const vendorList = Array.isArray(vendors) ? vendors : [];

  // Metrics computation for high-end SaaS feel
  const totalLots = batchList.length;
  const approvedLots = batchList.filter((b) => (b.decision || b.decision_status) === 'APPROVED').length;
  const rejectedLots = batchList.filter((b) => (b.decision || b.decision_status) === 'REJECTED').length;
  const reviewLots = batchList.filter((b) => (b.decision || b.decision_status) === 'NEEDS_REVIEW').length;
  const highRiskLots = batchList.filter((b) => b.risk_level === 'HIGH' || b.risk_level === 'CRITICAL').length;
  const complianceRate = totalLots > 0 ? Math.round((approvedLots / totalLots) * 100) : 100;

  const filteredBatches = batchList.filter((b) => {
    const bNum = b.batch_number || '';
    const vName = b.vendor?.name || (b.vendor as any)?.vendor_name || '';
    const mName = b.raw_material?.name || '';
    const matchesSearch =
      bNum.toLowerCase().includes(searchTerm.toLowerCase()) ||
      vName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      mName.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const getRiskBadge = (level?: string) => {
    switch (level?.toUpperCase()) {
      case 'LOW':
        return (
          <span className="badge badge-risk-low">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Low Risk
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="badge badge-risk-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            Medium
          </span>
        );
      case 'HIGH':
        return (
          <span className="badge badge-risk-high">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
            High Risk
          </span>
        );
      case 'CRITICAL':
        return (
          <span className="badge badge-risk-critical">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
            Critical
          </span>
        );
      default:
        return (
          <span className="badge badge-pending">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            Pending ML
          </span>
        );
    }
  };

  const getStatusBadge = (batch: Batch) => {
    const dec = batch.decision || batch.decision_status;
    if (dec === 'APPROVED') {
      return (
        <span className="badge badge-approved">
          <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Approved
        </span>
      );
    }
    if (dec === 'REJECTED') {
      return (
        <span className="badge badge-rejected">
          <XCircle className="w-3 h-3 text-rose-600" /> Rejected
        </span>
      );
    }
    if (dec === 'NEEDS_REVIEW') {
      return (
        <span className="badge badge-needs-review">
          <Clock className="w-3 h-3 text-amber-600" /> Needs Review
        </span>
      );
    }

    if (batch.status === 'EVALUATED') return <span className="badge badge-info">Evaluated</span>;
    if (batch.status === 'VALIDATING' || batch.status === 'ANALYZING') return <span className="badge badge-info">Processing</span>;
    return <span className="badge badge-pending">Received</span>;
  };

  const getEmailBadge = (emailStatus?: string) => {
    switch (emailStatus?.toUpperCase()) {
      case 'SENT':
        return (
          <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Send className="w-3 h-3" /> Dispatched
          </span>
        );
      case 'FAILED':
        return (
          <span className="badge bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3" /> Failed
          </span>
        );
      default:
        return (
          <span className="badge bg-slate-100 text-slate-600 border border-slate-200">
            <Clock className="w-3 h-3" /> Queued
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Batch Lot Intelligence</h1>
            <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Live Auditing
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Automated multi-stage qualification, chemical COA verification, ML risk scoring, and email dispatch.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="btn-secondary text-xs h-9"
            title="Sync batches"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? 'animate-spin text-blue-600' : ''}`} />
            <span>{isFetching ? 'Syncing...' : 'Sync'}</span>
          </button>
          <button
            onClick={() => {
              setErrorMessage(null);
              setIsAddModalOpen(true);
            }}
            className="btn-primary text-xs h-9 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            <span>New Batch Lot</span>
          </button>
        </div>
      </div>

      {/* Modern KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="v-stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Total Batches</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
              <Boxes className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 font-mono">{totalLots}</span>
            <span className="text-[11px] text-slate-500 font-medium">lots logged</span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Real-time ingestion active</span>
          </div>
        </div>

        <div className="v-stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Compliance Rate</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-600 font-mono">{complianceRate}%</span>
            <span className="text-[11px] text-slate-500 font-medium">({approvedLots} approved)</span>
          </div>
          <div className="mt-3 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${complianceRate}%` }}
            ></div>
          </div>
        </div>

        <div className="v-stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Review Required</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-100">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-600 font-mono">{reviewLots}</span>
            <span className="text-[11px] text-slate-500 font-medium">gated for QA</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500">
            {rejectedLots} rejected batches in isolation
          </div>
        </div>

        <div className="v-stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Critical Risk</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center border border-rose-100">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-600 font-mono">{highRiskLots}</span>
            <span className="text-[11px] text-slate-500 font-medium">flagged by ML</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500">
            Random Forest &amp; Kimi verified
          </div>
        </div>
      </div>

      {/* Filter and Search Bar with Quick Tabs */}
      <div className="v-card p-3.5 space-y-3">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by lot number (e.g. VC-2026-104) or supplier..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input pl-10 text-xs h-9"
            />
          </div>

          {/* Quick status tabs */}
          <div className="flex items-center gap-1.5 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
            {[
              { label: 'All Lots', value: '' },
              { label: 'Approved', value: 'APPROVED' },
              { label: 'Review', value: 'NEEDS_REVIEW' },
              { label: 'Rejected', value: 'REJECTED' },
              { label: 'Pending', value: 'PENDING' },
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => setStatusFilter(tab.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  statusFilter === tab.value
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table: Batch Lots List */}
      <div className="v-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Batch Lot</th>
                <th>Supplier (Vendor)</th>
                <th>Risk Profile</th>
                <th>Decision Status</th>
                <th>Pipeline Phase</th>
                <th>Supplier Email</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
                    <span className="text-xs text-slate-500 font-medium">Loading batch records...</span>
                  </td>
                </tr>
              ) : filteredBatches.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-16 px-4">
                    <div className="max-w-md mx-auto text-center space-y-3">
                      <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto border border-blue-100 shadow-sm">
                        <Boxes className="w-6 h-6" />
                      </div>
                      <h3 className="text-base font-bold text-slate-900">
                        {batchList.length === 0 ? 'No batch lots registered yet' : 'No matching batch lots found'}
                      </h3>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        {batchList.length === 0
                          ? 'Register an incoming lot to run automated document parsing, chemical specification checks, ML risk scoring, and email notifications.'
                          : 'Try adjusting your search query or status filter.'}
                      </p>
                      {batchList.length === 0 && (
                        <div className="pt-2">
                          <button
                            onClick={() => {
                              setErrorMessage(null);
                              setIsAddModalOpen(true);
                            }}
                            className="btn-primary text-xs"
                          >
                            <Plus className="w-3.5 h-3.5 mr-1" />
                            <span>Register First Batch Lot</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredBatches.map((batch) => (
                  <tr key={batch.id} className="group hover:bg-blue-50/20">
                    <td>
                      <div>
                        <Link
                          to={`/batches/${batch.id}`}
                          className="font-mono font-bold text-blue-600 group-hover:text-blue-800 transition-colors flex items-center gap-1.5"
                        >
                          <span>{batch.batch_number}</span>
                          <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </Link>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {batch.quantity} {batch.unit} • ${batch.price_per_unit || (batch as any).price || 0}/unit
                        </div>
                      </div>
                    </td>
                    <td>
                      <div>
                        <span className="font-semibold text-slate-900 block text-xs">
                          {batch.vendor?.name || (batch as any).vendor_name || 'Unassigned Supplier'}
                        </span>
                        <span className="text-[11px] text-slate-500">
                          {batch.vendor?.vendor_code || (batch as any).vendor_code || 'Standard Partner'}
                        </span>
                      </div>
                    </td>
                    <td>{getRiskBadge(batch.risk_level)}</td>
                    <td>{getStatusBadge(batch)}</td>
                    <td>
                      {batch.processed ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" /> Fully Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                          <Clock className="w-3 h-3" /> Intake Received
                        </span>
                      )}
                    </td>
                    <td>{getEmailBadge(batch.email_status)}</td>
                    <td className="text-right">
                      <Link
                        to={`/batches/${batch.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold text-blue-600 hover:text-white hover:bg-blue-600 border border-blue-200 hover:border-blue-600 rounded-lg transition-all"
                      >
                        <span>Audit Lot</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Streamlined Add Batch Modal - Materials section completely removed! */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-sm">
                  <Boxes className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Register New Batch Lot</h3>
                  <p className="text-[11px] text-slate-500">Fast batch intake for qualification &amp; COA analysis</p>
                </div>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-6 space-y-4">
              {errorMessage && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-500" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Batch Number with Auto-generate */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="form-label mb-0">Batch Lot Number *</label>
                  <button
                    type="button"
                    onClick={handleGenerateBatchNumber}
                    className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
                  >
                    <Sparkles className="w-3 h-3" /> Auto Generate
                  </button>
                </div>
                <input
                  type="text"
                  required
                  value={formData.batch_number}
                  onChange={(e) => setFormData({ ...formData, batch_number: e.target.value.toUpperCase() })}
                  placeholder="e.g. VC-2026-104"
                  className="form-input font-mono uppercase text-sm font-semibold"
                />
              </div>

              {/* Supplier Selection (Full Width, No Material Selection) */}
              <div>
                <label className="form-label">Supplier (Vendor) *</label>
                <select
                  required
                  value={formData.vendor_id}
                  onChange={(e) => setFormData({ ...formData, vendor_id: e.target.value })}
                  className="form-select text-sm font-medium"
                >
                  <option value="">Select Registered Supplier</option>
                  {vendorList.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name || (v as any).vendor_name} ({v.vendor_code || (v as any).code || 'SUPPLIER'})
                    </option>
                  ))}
                </select>
                {vendorList.length === 0 && (
                  <p className="text-[11px] text-amber-600 mt-1">
                    No suppliers found. Please register or invite a supplier first.
                  </p>
                )}
              </div>

              {/* Quantity, Unit, and Price */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="form-label">Quantity</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })}
                    className="form-input"
                  />
                </div>
                <div>
                  <label className="form-label">Unit</label>
                  <select
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    className="form-select"
                  >
                    <option value="kg">kg</option>
                    <option value="L">L</option>
                    <option value="tons">tons</option>
                    <option value="units">units</option>
                    <option value="drums">drums</option>
                  </select>
                </div>
                <div>
                  <label className="form-label">Price/Unit ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.price_per_unit}
                    onChange={(e) => setFormData({ ...formData, price_per_unit: parseFloat(e.target.value) || 0 })}
                    className="form-input"
                  />
                </div>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="form-label">Mfg Date</label>
                  <input
                    type="date"
                    value={formData.manufacturing_date}
                    onChange={(e) => setFormData({ ...formData, manufacturing_date: e.target.value })}
                    className="form-input text-xs"
                  />
                </div>
                <div>
                  <label className="form-label">Expiry Date</label>
                  <input
                    type="date"
                    value={formData.expiry_date}
                    onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
                    className="form-input text-xs"
                  />
                </div>
              </div>

              {/* Modal Action Buttons */}
              <div className="pt-4 flex items-center justify-end gap-2.5 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="btn-secondary text-xs h-9 px-4"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createBatchMutation.isPending}
                  className="btn-primary text-xs h-9 px-5 shadow-sm"
                >
                  {createBatchMutation.isPending ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin mr-1.5" />
                      <span>Registering Lot...</span>
                    </>
                  ) : (
                    <span>Register Batch Lot</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
