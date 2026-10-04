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
  CheckCircle,
  XCircle,
  Clock,
  Send,
  AlertCircle,
  X,
  FileCheck2,
} from 'lucide-react';
import { batchApi, vendorApi, rawMaterialApi } from '../api/client';
import { Batch, Vendor, RawMaterial } from '../types';

export const BatchesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // New Batch Form State
  const [formData, setFormData] = useState({
    batch_number: '',
    vendor_id: '',
    raw_material_id: '',
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
  } = useQuery<Batch[]>({
    queryKey: ['batches', statusFilter],
    queryFn: () => batchApi.getAll({ status: statusFilter || undefined }),
  });

  const { data: vendors = [] } = useQuery<Vendor[]>({
    queryKey: ['vendors-list'],
    queryFn: () => vendorApi.getAll(),
  });

  const { data: materials = [] } = useQuery<RawMaterial[]>({
    queryKey: ['raw-materials-list'],
    queryFn: () => rawMaterialApi.getAll(),
  });

  const createBatchMutation = useMutation({
    mutationFn: (newBatch: typeof formData) => batchApi.create(newBatch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      setIsAddModalOpen(false);
      setFormData({
        batch_number: '',
        vendor_id: '',
        raw_material_id: '',
        quantity: 1000,
        unit: 'kg',
        price_per_unit: 18.5,
        manufacturing_date: new Date().toISOString().split('T')[0],
        expiry_date: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
      });
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.batch_number || !formData.vendor_id || !formData.raw_material_id) return;
    createBatchMutation.mutate(formData);
  };

  const batchList = Array.isArray(batches) ? batches : [];
  const vendorList = Array.isArray(vendors) ? vendors : [];
  const materialList = Array.isArray(materials) ? materials : [];

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
        return <span className="badge badge-risk-low">LOW RISK</span>;
      case 'MEDIUM':
        return <span className="badge badge-risk-medium">MEDIUM RISK</span>;
      case 'HIGH':
        return <span className="badge badge-risk-high">HIGH RISK</span>;
      case 'CRITICAL':
        return <span className="badge badge-risk-critical">CRITICAL RISK</span>;
      default:
        return <span className="badge badge-pending">PENDING ML</span>;
    }
  };

  const getStatusBadge = (batch: Batch) => {
    const dec = batch.decision || batch.decision_status;
    if (dec === 'APPROVED') return <span className="badge badge-approved">APPROVED</span>;
    if (dec === 'REJECTED') return <span className="badge badge-rejected">REJECTED</span>;
    if (dec === 'NEEDS_REVIEW') return <span className="badge badge-needs-review">NEEDS REVIEW</span>;

    if (batch.status === 'EVALUATED') return <span className="badge badge-info">EVALUATED</span>;
    if (batch.status === 'VALIDATING' || batch.status === 'ANALYZING') return <span className="badge badge-info">PROCESSING</span>;
    return <span className="badge badge-pending">PENDING</span>;
  };

  const getEmailBadge = (emailStatus?: string) => {
    switch (emailStatus?.toUpperCase()) {
      case 'SENT':
        return (
          <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Send className="w-3 h-3" /> SENT
          </span>
        );
      case 'FAILED':
        return (
          <span className="badge bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3" /> FAILED
          </span>
        );
      default:
        return (
          <span className="badge bg-slate-100 text-slate-600 border border-slate-200">
            <Clock className="w-3 h-3" /> PENDING
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Batch Intelligence & Compliance</h1>
          <p className="text-sm text-slate-500 mt-1">
            Automated multi-stage qualification, ML risk scoring, and automated decision dispatch.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => refetch()} className="btn-secondary" title="Sync batches">
            <RefreshCw className="w-4 h-4 mr-1.5" />
            <span>Sync</span>
          </button>
          <button onClick={() => setIsAddModalOpen(true)} className="btn-primary">
            <Plus className="w-4 h-4 mr-1.5" />
            <span>New Batch Lot</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="v-card p-4 flex flex-col md:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by batch number (e.g. VC-2026-104), supplier, or material..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10"
          />
        </div>

        <div className="w-full md:w-48">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="form-select text-xs"
          >
            <option value="">All Decisions / Status</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="PENDING">Pending Evaluation</option>
          </select>
        </div>
      </div>

      {/* Table: Batch Vendor Material Risk Status Processed Email Action */}
      <div className="v-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Batch</th>
                <th>Vendor</th>
                <th>Material</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Processed</th>
                <th>Email</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="text-center py-10">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
                    <span className="text-xs text-slate-500">Loading batch intelligence records...</span>
                  </td>
                </tr>
              ) : filteredBatches.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-16 px-4">
                    <div className="max-w-md mx-auto text-center space-y-3">
                      <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto shadow-sm">
                        <Boxes className="w-6 h-6" />
                      </div>
                      <h3 className="text-base font-bold text-slate-900">
                        {batchList.length === 0 ? 'No batch lots recorded yet' : 'No matching batches found'}
                      </h3>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        {batchList.length === 0
                          ? 'Register raw material lots to begin automated COA purity checks, ML risk scoring, and email qualification dispatches to suppliers.'
                          : 'Try changing your search terms or status filter.'}
                      </p>
                      {batchList.length === 0 && (
                        <div className="pt-2">
                          <button
                            onClick={() => setIsAddModalOpen(true)}
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
                  <tr key={batch.id}>
                    <td>
                      <div>
                        <Link
                          to={`/batches/${batch.id}`}
                          className="font-mono font-bold text-blue-600 hover:text-blue-800 transition-colors"
                        >
                          {batch.batch_number}
                        </Link>
                        <div className="text-[11px] text-slate-600">
                          Qty: {batch.quantity} {batch.unit}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="font-medium text-slate-900">
                        {batch.vendor?.name || 'Unassigned Supplier'}
                      </span>
                    </td>
                    <td>
                      <span className="text-xs font-semibold text-slate-700">
                        {batch.raw_material?.name || 'Raw Material'}
                      </span>
                    </td>
                    <td>{getRiskBadge(batch.risk_level)}</td>
                    <td>{getStatusBadge(batch)}</td>
                    <td>
                      {batch.processed ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700">
                          <CheckCircle className="w-3.5 h-3.5" /> Done
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600">
                          <Clock className="w-3.5 h-3.5" /> Pending
                        </span>
                      )}
                    </td>
                    <td>{getEmailBadge(batch.email_status)}</td>
                    <td>
                      <Link
                        to={`/batches/${batch.id}`}
                        className="btn-primary text-xs py-1.5 px-3"
                      >
                        Inspect & Demo
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Batch Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in duration-150">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">Register New Batch Lot</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit} className="p-6 space-y-4">
              <div>
                <label className="form-label">Batch Number *</label>
                <input
                  type="text"
                  required
                  value={formData.batch_number}
                  onChange={(e) => setFormData({ ...formData, batch_number: e.target.value })}
                  placeholder="e.g. VC-2026-104"
                  className="form-input font-mono uppercase"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Supplier (Vendor) *</label>
                  <select
                    required
                    value={formData.vendor_id}
                    onChange={(e) => setFormData({ ...formData, vendor_id: e.target.value })}
                    className="form-select"
                  >
                    <option value="">Select Supplier</option>
                    {vendorList.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name || (v as any).vendor_name} ({(v as any).vendor_code || (v as any).code || 'N/A'})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="form-label">Raw Material *</label>
                  <select
                    required
                    value={formData.raw_material_id}
                    onChange={(e) => setFormData({ ...formData, raw_material_id: e.target.value })}
                    className="form-select"
                  >
                    <option value="">Select Material</option>
                    {materialList.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.material_code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
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
                  <input
                    type="text"
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    className="form-input"
                  />
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

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Mfg Date</label>
                  <input
                    type="date"
                    value={formData.manufacturing_date}
                    onChange={(e) => setFormData({ ...formData, manufacturing_date: e.target.value })}
                    className="form-input"
                  />
                </div>
                <div>
                  <label className="form-label">Expiry Date</label>
                  <input
                    type="date"
                    value={formData.expiry_date}
                    onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
                    className="form-input"
                  />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-100">
                <button type="button" onClick={() => setIsAddModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={createBatchMutation.isPending} className="btn-primary">
                  {createBatchMutation.isPending ? 'Saving...' : 'Register Batch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
