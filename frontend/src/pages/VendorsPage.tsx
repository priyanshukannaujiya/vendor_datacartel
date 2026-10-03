import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Building2,
  Search,
  Filter,
  Plus,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  CheckCircle,
  XCircle,
  AlertTriangle,
  X,
  Mail,
  Send,
  UploadCloud,
  FileText,
  FileCheck2,
  Check,
} from 'lucide-react';
import { vendorApi, batchApi } from '../api/client';
import { Vendor, Batch } from '../types';

export const VendorsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [activeTab, setActiveTab] = useState<'directory' | 'emails'>('directory');

  // New Vendor Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    vendor_code: '',
    contact_name: '',
    contact_email: '',
    phone: '',
    address: '',
    status: 'ACTIVE',
  });

  // Request Document Email Modal State
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [selectedVendorForEmail, setSelectedVendorForEmail] = useState<Vendor | null>(null);
  const [targetBatchId, setTargetBatchId] = useState('');
  const [customEmailAddress, setCustomEmailAddress] = useState('');
  const [dispatchStatus, setDispatchStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Upload PDF for Batch State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadBatchId, setUploadBatchId] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocType, setUploadDocType] = useState('COA');
  const [uploadStatusMessage, setUploadStatusMessage] = useState<string | null>(null);

  const {
    data: vendors = [],
    isLoading,
    refetch,
  } = useQuery<Vendor[]>({
    queryKey: ['vendors', riskFilter, statusFilter],
    queryFn: () => vendorApi.getAll({ risk_level: riskFilter || undefined, status: statusFilter || undefined }),
  });

  const { data: batches = [] } = useQuery<Batch[]>({
    queryKey: ['all-batches'],
    queryFn: () => batchApi.getAll(),
  });

  const createVendorMutation = useMutation({
    mutationFn: (newVendor: Partial<Vendor>) => vendorApi.create(newVendor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      setIsAddModalOpen(false);
      setFormData({
        name: '',
        vendor_code: '',
        contact_name: '',
        contact_email: '',
        phone: '',
        address: '',
        status: 'ACTIVE',
      });
    },
  });

  // Document Request Email Mutation
  const sendEmailMutation = useMutation({
    mutationFn: (data: { batchId: string; email: string }) =>
      batchApi.requestDocuments(data.batchId, data.email),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      setDispatchStatus({
        type: res.success ? 'success' : 'error',
        message: res.message || (
          res.success
            ? `Request email sent to ${res.recipient} via Google SMTP!`
            : `Email delivery failed for ${res.recipient}.`
        ),
      });
    },
    onError: (err: any) => {
      setDispatchStatus({
        type: 'error',
        message: err.response?.data?.detail || err.message || 'Failed to dispatch email. Check SMTP credentials in Settings.',
      });
    },
  });

  // Upload PDF Document Mutation
  const uploadDocMutation = useMutation({
    mutationFn: (data: { batchId: string; file: File; type: string }) =>
      batchApi.uploadDocument(data.batchId, data.file, data.type),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setUploadStatusMessage(`Document "${res.filename}" uploaded successfully! Batch pipeline updated.`);
      setTimeout(() => {
        setIsUploadModalOpen(false);
        setUploadStatusMessage(null);
        setUploadFile(null);
      }, 2500);
    },
    onError: (err: any) => {
      setUploadStatusMessage(`Upload failed: ${err.response?.data?.detail || err.message}`);
    },
  });

  const handleOpenEmailModal = (vendor: Vendor) => {
    setSelectedVendorForEmail(vendor);
    setCustomEmailAddress(vendor.contact_email || '');
    // Pre-select first batch for this vendor if available
    const vendorBatches = batches.filter((b) => b.vendor_id === vendor.id);
    if (vendorBatches.length > 0) {
      setTargetBatchId(vendorBatches[0].id);
    } else {
      setTargetBatchId('');
    }
    setDispatchStatus(null);
    setIsEmailModalOpen(true);
  };

  const handleSendEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetBatchId || !customEmailAddress) return;
    sendEmailMutation.mutate({
      batchId: targetBatchId,
      email: customEmailAddress,
    });
  };

  const handleOpenUploadModal = (batchId: string) => {
    setUploadBatchId(batchId);
    setUploadFile(null);
    setUploadStatusMessage(null);
    setIsUploadModalOpen(true);
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadBatchId || !uploadFile) return;
    uploadDocMutation.mutate({
      batchId: uploadBatchId,
      file: uploadFile,
      type: uploadDocType,
    });
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.vendor_code) return;
    createVendorMutation.mutate(formData);
  };

  const vendorList = Array.isArray(vendors) ? vendors : [];
  const filteredVendors = vendorList.filter((v) => {
    const vName = v.name || (v as any).vendor_name || '';
    const vCode = v.vendor_code || (v as any).code || '';
    const vEmail = v.contact_email || (v as any).email || '';
    const matchesSearch =
      vName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      vCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      vEmail.toLowerCase().includes(searchTerm.toLowerCase());
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
        return <span className="badge badge-pending">PENDING</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Suppliers & Communications</h1>
          <p className="text-sm text-slate-500 mt-1">
            Supplier qualification records, email communication directory, and batch document intake.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => refetch()} className="btn-secondary" title="Reload vendors">
            <RefreshCw className="w-4 h-4 mr-1.5" />
            <span>Sync</span>
          </button>
          <button onClick={() => setIsAddModalOpen(true)} className="btn-primary">
            <Plus className="w-4 h-4 mr-1.5" />
            <span>Add Supplier</span>
          </button>
        </div>
      </div>

      {/* Tabs: Supplier Directory vs Email Communications */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('directory')}
          className={`py-3 px-5 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'directory'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Supplier Portfolio ({vendorList.length})
        </button>
        <button
          onClick={() => setActiveTab('emails')}
          className={`py-3 px-5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'emails'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Mail className="w-4 h-4" />
          <span>Vendor Email Directory & Document Request Center</span>
        </button>
      </div>

      {/* Global Filter Bar */}
      <div className="v-card p-4 flex flex-col md:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by vendor name, code, or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="w-full md:w-44">
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="form-select text-xs"
            >
              <option value="">All Risk Tiers</option>
              <option value="LOW">Low Risk</option>
              <option value="MEDIUM">Medium Risk</option>
              <option value="HIGH">High Risk</option>
              <option value="CRITICAL">Critical Risk</option>
            </select>
          </div>

          <div className="w-full md:w-40">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="form-select text-xs"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="PENDING">Pending Audit</option>
              <option value="SUSPENDED">Suspended</option>
            </select>
          </div>
        </div>
      </div>

      {/* TAB 1: Main Supplier Directory Table */}
      {activeTab === 'directory' && (
        <div className="v-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Vendor</th>
                  <th>Industry</th>
                  <th>Risk Score</th>
                  <th>Approval Rate</th>
                  <th>Quality</th>
                  <th>Delivery</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-10">
                      <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
                      <span className="text-xs text-slate-500">Loading supplier registry...</span>
                    </td>
                  </tr>
                ) : filteredVendors.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-slate-500">
                      <Building2 className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                      <p className="text-sm font-medium text-slate-700">No vendors found</p>
                    </td>
                  </tr>
                ) : (
                  filteredVendors.map((vendor) => (
                    <tr key={vendor.id}>
                      <td>
                        <div>
                          <Link
                            to={`/vendors/${vendor.id}`}
                            className="font-semibold text-slate-900 hover:text-blue-600 transition-colors"
                          >
                            {vendor.name}
                          </Link>
                          <div className="text-xs text-slate-600 flex items-center gap-2 mt-0.5">
                            <span className="font-mono">{vendor.vendor_code}</span>
                            <span>•</span>
                            <span>{vendor.contact_email || 'No email provided'}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="text-xs font-medium text-slate-600">
                          {vendor.industry || 'Not recorded'}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900">
                            {vendor.risk_score?.toFixed(1) || '—'}
                          </span>
                          {getRiskBadge(vendor.risk_level)}
                        </div>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full ${
                                vendor.approval_rate >= 80 ? 'bg-emerald-500' : 'bg-rose-500'
                              }`}
                              style={{ width: `${vendor.approval_rate || 0}%` }}
                            ></div>
                          </div>
                          <span className="text-xs font-medium text-slate-700">
                            {vendor.approval_rate}%
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="text-xs font-semibold text-slate-800">
                          {(vendor.quality_score ?? vendor.avg_purity) == null
                            ? '—'
                            : `${vendor.quality_score ?? vendor.avg_purity}%`}
                        </span>
                      </td>
                      <td>
                        <span className="text-xs font-semibold text-slate-800">
                          {vendor.delivery_score == null ? '—' : `${vendor.delivery_score}%`}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${vendor.status === 'ACTIVE' ? 'badge-approved' : 'badge-pending'}`}>
                          {vendor.status}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleOpenEmailModal(vendor)}
                            className="btn-secondary text-xs py-1 px-2.5 flex items-center gap-1 border-blue-200 text-blue-700 hover:bg-blue-50"
                            title="Send batch document request email"
                          >
                            <Mail className="w-3.5 h-3.5" />
                            <span>Request Docs</span>
                          </button>
                          <Link
                            to={`/vendors/${vendor.id}`}
                            className="btn-ghost text-xs text-slate-600 font-semibold"
                          >
                            Profile
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: Vendor Email Directory & Document Request Center */}
      {activeTab === 'emails' && (
        <div className="space-y-4">
          <div className="v-card p-5 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 border-blue-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Mail className="w-4 h-4 text-blue-600" />
                  Supplier Email Communication & Intake Center
                </h3>
                <p className="text-xs text-slate-600 mt-1">
                  Click <strong>"Submit / Send Request"</strong> to dispatch official PDF document requirements (COA, SDS, GMP) directly to the supplier's contact email via Google SMTP. When the vendor replies with their PDF files, upload them below to run the AI qualification pipeline.
                </p>
              </div>
              <Link to="/settings" className="btn-secondary text-xs whitespace-nowrap">
                <span>Configure Google SMTP</span>
              </Link>
            </div>
          </div>

          <div className="v-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Contact Person</th>
                    <th>Supplier Email</th>
                    <th>Active Batch Lots</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVendors.map((vendor) => {
                    const vendorBatches = batches.filter((b) => b.vendor_id === vendor.id);
                    return (
                      <tr key={vendor.id}>
                        <td>
                          <div className="font-semibold text-slate-900">{vendor.name}</div>
                          <span className="font-mono text-[11px] text-slate-500">{vendor.vendor_code}</span>
                        </td>
                        <td>
                          <span className="text-xs text-slate-700">{vendor.contact_name || 'QA Compliance Desk'}</span>
                        </td>
                        <td>
                          <span className="font-mono text-xs text-blue-700 font-semibold">
                            {vendor.contact_email || 'Not Configured'}
                          </span>
                        </td>
                        <td>
                          <div className="flex flex-wrap gap-1.5">
                            {vendorBatches.length > 0 ? (
                              vendorBatches.map((b) => (
                                <span
                                  key={b.id}
                                  className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200"
                                >
                                  {b.batch_number} ({b.decision || b.status})
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-400">No active batches</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleOpenEmailModal(vendor)}
                              className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
                            >
                              <Send className="w-3.5 h-3.5" />
                              <span>Submit & Send Email</span>
                            </button>

                            {vendorBatches.length > 0 && (
                              <button
                                onClick={() => handleOpenUploadModal(vendorBatches[0].id)}
                                className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
                                title="Upload vendor returned PDF document"
                              >
                                <UploadCloud className="w-3.5 h-3.5 text-blue-600" />
                                <span>Upload Returned PDF</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: Document Request Email Submission Modal */}
      {isEmailModalOpen && selectedVendorForEmail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">Send Document Request to Vendor</h3>
              </div>
              <button
                onClick={() => setIsEmailModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSendEmailSubmit} className="p-6 space-y-4">
              {dispatchStatus && (
                <div
                  className={`p-3.5 rounded-lg text-xs font-medium flex items-start gap-2 ${
                    dispatchStatus.type === 'success'
                      ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                      : 'bg-rose-50 border border-rose-200 text-rose-800'
                  }`}
                >
                  {dispatchStatus.type === 'success' ? (
                    <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-600" />
                  )}
                  <span>{dispatchStatus.message}</span>
                </div>
              )}

              <div>
                <label className="form-label">Vendor / Supplier</label>
                <input
                  type="text"
                  readOnly
                  value={`${selectedVendorForEmail.name} (${selectedVendorForEmail.vendor_code})`}
                  className="form-input bg-slate-50"
                />
              </div>

              <div>
                <label className="form-label">Recipient Email Address *</label>
                <input
                  type="email"
                  required
                  value={customEmailAddress}
                  onChange={(e) => setCustomEmailAddress(e.target.value)}
                  placeholder="quality@supplier.com"
                  className="form-input"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  You can edit this to test sending to your own email address.
                </span>
              </div>

              <div>
                <label className="form-label">Select Associated Batch Lot *</label>
                <select
                  required
                  value={targetBatchId}
                  onChange={(e) => setTargetBatchId(e.target.value)}
                  className="form-select text-xs"
                >
                  <option value="">Select Batch</option>
                  {batches
                    .filter((b) => b.vendor_id === selectedVendorForEmail.id)
                    .map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.batch_number} — {b.raw_material?.name} ({b.quantity} {b.unit})
                      </option>
                    ))}
                </select>
                {!batches.some((b) => b.vendor_id === selectedVendorForEmail.id) && (
                  <span className="text-[11px] text-amber-700 mt-1 block">
                    This supplier has no associated batch. Create a batch before sending a document request.
                  </span>
                )}
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 space-y-1">
                <span className="font-bold text-slate-900 block">Requested Documentation:</span>
                <p>• Certificate of Analysis (COA) with HPLC assay purity</p>
                <p>• Safety Data Sheet (SDS) 16-section compliance</p>
                <p>• cGMP cleanroom lot release authorization</p>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsEmailModalOpen(false)}
                  className="btn-secondary"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={sendEmailMutation.isPending || !targetBatchId || !customEmailAddress}
                  className="btn-primary"
                >
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  {sendEmailMutation.isPending ? 'Sending via Google SMTP...' : 'Submit & Send Email'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Upload Vendor PDF Document Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">Upload Vendor PDF Document</h3>
              </div>
              <button
                onClick={() => setIsUploadModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="p-6 space-y-4">
              {uploadStatusMessage && (
                <div className="p-3.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-800 text-xs font-medium">
                  {uploadStatusMessage}
                </div>
              )}

              <div>
                <label className="form-label">Vendor Document PDF / File *</label>
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.xlsx,.png,.jpg"
                  onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                  className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>

              <div>
                <label className="form-label">Document Category *</label>
                <select
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value)}
                  className="form-select text-xs"
                >
                  <option value="COA">Certificate of Analysis (COA)</option>
                  <option value="SDS">Safety Data Sheet (SDS)</option>
                  <option value="GMP">GMP Certificate</option>
                  <option value="SPECIFICATION">Raw Material Specification</option>
                </select>
              </div>

              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
                <span className="font-bold">Automated Pipeline:</span> Uploading this PDF triggers text extraction, deterministic purity validation against specifications, ML risk prediction, and Moonshot Kimi K3 AI qualification.
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadDocMutation.isPending || !uploadFile}
                  className="btn-primary"
                >
                  {uploadDocMutation.isPending ? 'Processing & Extracting...' : 'Upload & Process Batch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Vendor Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in duration-150">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">Add New Supplier</h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit} className="p-6 space-y-4">
              <div>
                <label className="form-label">Vendor Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Apex BioSciences Ltd"
                  className="form-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Vendor Code *</label>
                  <input
                    type="text"
                    required
                    value={formData.vendor_code}
                    onChange={(e) => setFormData({ ...formData, vendor_code: e.target.value })}
                    placeholder="e.g. VEN-APEX-01"
                    className="form-input font-mono uppercase"
                  />
                </div>
                <div>
                  <label className="form-label">Contact Name</label>
                  <input
                    type="text"
                    value={formData.contact_name}
                    onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                    placeholder="e.g. Sarah Jenkins"
                    className="form-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Contact Email</label>
                  <input
                    type="email"
                    value={formData.contact_email}
                    onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                    placeholder="quality@supplier.com"
                    className="form-input"
                  />
                </div>
                <div>
                  <label className="form-label">Phone</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+1 (555) 234-5678"
                    className="form-input"
                  />
                </div>
              </div>

              <div>
                <label className="form-label">Facility Address</label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="e.g. 104 Industrial Way, Cambridge, MA"
                  className="form-input"
                />
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createVendorMutation.isPending}
                  className="btn-primary"
                >
                  {createVendorMutation.isPending ? 'Saving...' : 'Register Vendor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
