import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Boxes,
  Building2,
  Calendar,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Sparkles,
  ShieldCheck,
  Send,
  RotateCw,
  ArrowLeft,
  RefreshCw,
  Activity,
  Check,
  X,
  FileCheck,
  Cpu,
  MailCheck,
  Clock,
  UploadCloud,
  ChevronDown,
  Mail,
} from 'lucide-react';
import { batchApi, emailApi } from '../api/client';
import { BatchDetail, RiskLevel } from '../types';

export const BatchDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [overrideDecision, setOverrideDecision] = useState<string>('');
  const [overrideNotes, setOverrideNotes] = useState<string>('');
  const [showOverrideBox, setShowOverrideBox] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Vendor PDF Upload State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocType, setUploadDocType] = useState<string>('COA');

  const {
    data: batch,
    isLoading,
    refetch,
  } = useQuery<BatchDetail>({
    queryKey: ['batch', id],
    queryFn: () => batchApi.getById(id!),
    enabled: !!id,
  });

  // Action: Request Documents via Google SMTP
  const requestDocMutation = useMutation({
    mutationFn: () => batchApi.requestDocuments(id!),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', id] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      setActionMessage(data.message || `Document request email successfully dispatched to vendor via Google SMTP!`);
      setTimeout(() => setActionMessage(null), 6000);
    },
    onError: (err: any) => {
      setActionMessage(`Document request failed: ${err?.response?.data?.detail || err.message}`);
    },
  });

  // Action: Upload Vendor PDF Document
  const uploadDocMutation = useMutation({
    mutationFn: (file: File) => batchApi.uploadDocument(id!, file, uploadDocType),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['batch', id] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setIsUploadModalOpen(false);
      setUploadFile(null);
      setActionMessage(`Vendor PDF "${res.filename}" uploaded successfully! Triggering extraction & validation...`);
      // Auto-trigger validation
      processMutation.mutate();
    },
    onError: (err: any) => {
      setActionMessage(`Upload failed: ${err?.response?.data?.detail || err.message}`);
    },
  });

  // Action 1: Process Documents & Run Validation
  const processMutation = useMutation({
    mutationFn: () => batchApi.processBatch(id!),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', id] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      setActionMessage(data.message || 'Batch documents processed & validated successfully.');
      setTimeout(() => setActionMessage(null), 5000);
    },
    onError: (err: any) => {
      setActionMessage(`Processing failed: ${err?.response?.data?.detail || err.message}`);
    },
  });

  // Action 2: Run ML Risk Scoring
  const predictMutation = useMutation({
    mutationFn: () => batchApi.predictRisk(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', id] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      setActionMessage('ML Risk Prediction calculated with Random Forest + Gradient Boost models.');
      setTimeout(() => setActionMessage(null), 5000);
    },
    onError: (err: any) => {
      setActionMessage(`Risk prediction failed: ${err?.response?.data?.detail || err.message}`);
    },
  });

  // Action 3: Execute Decision Engine & Google SMTP Dispatch
  const decisionMutation = useMutation({
    mutationFn: (override?: { manual_override: boolean; decision: string; notes: string }) =>
      batchApi.makeDecision(id!, override),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', id] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      setShowOverrideBox(false);
      setActionMessage(`Decision executed: ${data.decision}. Notification status: ${data.email_status}`);
      setTimeout(() => setActionMessage(null), 6000);
    },
    onError: (err: any) => {
      setActionMessage(`Decision execution failed: ${err?.response?.data?.detail || err.message}`);
    },
  });

  // Action 4: Retry SMTP Email
  const retryEmailMutation = useMutation({
    mutationFn: (eventId: string) => emailApi.retryEmail(eventId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', id] });
      setActionMessage(`Email retry completed with status: ${data.status}.`);
      setTimeout(() => setActionMessage(null), 5000);
    },
    onError: (err: any) => {
      setActionMessage(`Email dispatch error: ${err?.response?.data?.detail || err.message}`);
    },
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px]">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm text-slate-500 font-medium">Loading batch intelligence report...</p>
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
        <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
        <h3 className="text-base font-semibold text-slate-900">Batch Not Found</h3>
        <p className="text-sm text-slate-500 mt-1 mb-4">The requested batch lot does not exist.</p>
        <Link to="/batches" className="btn-secondary">
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Batches
        </Link>
      </div>
    );
  }

  const finalDecision = batch.decision || batch.decision_status;
  const isApproved = finalDecision === 'APPROVED';
  const isRejected = finalDecision === 'REJECTED';
  const isReview = finalDecision === 'NEEDS_REVIEW';

  const getRiskColor = (level?: RiskLevel) => {
    switch (level) {
      case 'LOW':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'MEDIUM':
        return 'text-amber-700 bg-amber-50 border-amber-200';
      case 'HIGH':
        return 'text-orange-700 bg-orange-50 border-orange-200';
      case 'CRITICAL':
        return 'text-rose-700 bg-rose-50 border-rose-200';
      default:
        return 'text-slate-700 bg-slate-100 border-slate-200';
    }
  };

  const checks = batch.validation_results?.checks || [];

  return (
    <div className="space-y-6">
      {/* Top Banner / Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <Link
          to="/batches"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Batches Directory</span>
        </Link>

        {/* Live Interactive Action Bar */}
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => refetch()} className="btn-secondary text-xs">
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Sync
          </button>

          <button
            onClick={() => requestDocMutation.mutate()}
            disabled={requestDocMutation.isPending}
            className="btn-secondary text-xs border-blue-300 text-blue-700 hover:bg-blue-50"
            title="Dispatch official document request to vendor email via Google SMTP"
          >
            <Mail className="w-3.5 h-3.5 mr-1 text-blue-600" />
            {requestDocMutation.isPending ? 'Sending Request...' : 'Request Docs (SMTP)'}
          </button>

          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="btn-secondary text-xs border-teal-300 text-teal-700 hover:bg-teal-50"
            title="Upload vendor's submitted PDF document"
          >
            <UploadCloud className="w-3.5 h-3.5 mr-1 text-teal-600" />
            <span>Upload Vendor PDF</span>
          </button>

          <button
            onClick={() => processMutation.mutate()}
            disabled={processMutation.isPending}
            className="btn-secondary text-xs border-blue-300 text-blue-700 hover:bg-blue-50"
          >
            <FileCheck className="w-3.5 h-3.5 mr-1 text-blue-600" />
            {processMutation.isPending ? 'Validating...' : '1. Run Validation'}
          </button>

          <button
            onClick={() => predictMutation.mutate()}
            disabled={predictMutation.isPending}
            className="btn-secondary text-xs border-indigo-300 text-indigo-700 hover:bg-indigo-50"
          >
            <Cpu className="w-3.5 h-3.5 mr-1 text-indigo-600" />
            {predictMutation.isPending ? 'Scoring...' : '2. Predict ML Risk'}
          </button>

          <button
            onClick={() => decisionMutation.mutate(undefined)}
            disabled={decisionMutation.isPending}
            className="btn-primary text-xs bg-emerald-600 hover:bg-emerald-700"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1" />
            {decisionMutation.isPending ? 'Executing...' : '3. Trigger AI Decision & SMTP'}
          </button>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionMessage && (
        <div className="p-3.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-800 text-xs font-medium flex items-center justify-between animate-in fade-in">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-blue-500 hover:text-blue-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Hero Decision Banner */}
      <div
        className={`v-card p-6 border-l-4 ${
          isApproved
            ? 'border-l-emerald-500 bg-emerald-50/20'
            : isRejected
            ? 'border-l-rose-500 bg-rose-50/20'
            : isReview
            ? 'border-l-amber-500 bg-amber-50/20'
            : 'border-l-blue-500 bg-white'
        }`}
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-3">
              <span className="font-mono text-2xl font-extrabold text-slate-900 tracking-tight">
                {batch.batch_number}
              </span>
              <span className={`badge text-xs px-3 py-1 font-bold ${getRiskColor(batch.risk_level)}`}>
                {batch.risk_level ? `${batch.risk_level} RISK` : 'RISK UNKNOWN'}
              </span>
            </div>
            <p className="text-sm text-slate-600">
              Supplier:{' '}
              <Link to={`/vendors/${batch.vendor_id}`} className="font-semibold text-blue-600 hover:underline">
                {batch.vendor?.name || 'Assigned Supplier'}
              </Link>{' '}
              • Material: <span className="font-semibold text-slate-800">{batch.raw_material?.name || 'Cosmetic & Formulation Grade Material'}</span>
            </p>
          </div>

          {/* Final Decision & Email Delivery Pill */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="text-right">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Final Decision</div>
              <div
                className={`text-xl font-black tracking-tight ${
                  isApproved
                    ? 'text-emerald-600'
                    : isRejected
                    ? 'text-rose-600'
                    : isReview
                    ? 'text-amber-600'
                    : 'text-slate-500'
                }`}
              >
                {finalDecision || 'PENDING EVALUATION'}
              </div>
            </div>

            <div className="h-8 w-px bg-slate-200 hidden sm:block"></div>

            <div className="text-right">
              <div className="text-[11px] font-semibold uppercase text-slate-400">Google SMTP</div>
              <div className="flex items-center gap-1.5 justify-end">
                {batch.email_status === 'SENT' ? (
                  <span className="badge badge-approved text-xs font-semibold">
                    <CheckCircle2 className="w-3 h-3" /> EMAIL SENT
                  </span>
                ) : batch.email_status === 'FAILED' ? (
                  <button
                    onClick={() => batch.email_event?.id && retryEmailMutation.mutate(batch.email_event.id)}
                    disabled={!batch.email_event?.id || retryEmailMutation.isPending}
                    className="badge badge-rejected text-xs font-semibold cursor-pointer hover:bg-rose-100 disabled:opacity-50"
                    title="Retry dispatching email"
                  >
                    <RotateCw className="w-3 h-3 mr-1" /> RETRY EMAIL
                  </button>
                ) : (
                  <span className="badge badge-pending text-xs">
                    {batch.email_status === 'NOT_APPLICABLE' ? 'NO VENDOR EMAIL' : 'AWAITING DECISION'}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 1. Batch Information Grid */}
      <div className="v-card p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 mb-4 flex items-center gap-2">
          <Boxes className="w-4 h-4 text-blue-600" />
          Batch Information
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Vendor</span>
            <span className="text-xs font-bold text-slate-800 mt-1 block truncate">
              {batch.vendor?.name}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">{batch.vendor?.contact_email}</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Material</span>
            <span className="text-xs font-bold text-slate-800 mt-1 block truncate">
              {batch.raw_material?.name || 'Cosmetic & Formulation Grade Material'}
            </span>
            <span className="text-[10px] text-slate-500">
              {batch.raw_material?.required_purity != null
                ? `Spec: ≥${batch.raw_material.required_purity}%`
                : 'Purity Spec: ≥95.0%'}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Batch Number</span>
            <span className="font-mono text-xs font-bold text-blue-700 mt-1 block">
              {batch.batch_number}
            </span>
            <span className="text-[10px] text-slate-500">Internal Lot ID</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Quantity</span>
            <span className="text-xs font-bold text-slate-800 mt-1 block">
              {batch.quantity} {batch.unit}
            </span>
            <span className="text-[10px] text-slate-500">
              {batch.price_per_unit != null ? `Unit: $${batch.price_per_unit}` : 'Unit price not recorded'}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Mfg Date</span>
            <span className="text-xs font-bold text-slate-800 mt-1 block">
              {batch.manufacturing_date || 'Not recorded'}
            </span>
            <span className="text-[10px] text-slate-500">Production Lot</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase block">Expiry Date</span>
            <span className="text-xs font-bold text-slate-800 mt-1 block">
              {batch.expiry_date || 'Not recorded'}
            </span>
            {batch.expiry_date && (
              <span className="text-[10px] text-slate-500 font-semibold">
                {new Date(batch.expiry_date) < new Date() ? 'Expired' : 'Expiry date recorded'}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 2. Quality Checks Table */}
      <div className="v-card overflow-hidden">
        <div className="v-card-header">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Quality Checks & Specification Verification</h3>
            <p className="text-xs text-slate-500">Checks and thresholds stored by the validation service</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Quality Check</th>
                <th>Category</th>
                <th>Required Specification</th>
                <th>Actual Extracted Value</th>
                <th>Compliance Status</th>
              </tr>
            </thead>
            <tbody>
              {checks.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-xs text-slate-500">
                    No validation checks are stored yet. Run validation to populate this section.
                  </td>
                </tr>
              ) : checks.map((chk, i) => (
                <tr key={i}>
                  <td className="font-semibold text-slate-800">{chk.name}</td>
                  <td>
                    <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded text-slate-700">
                      {chk.category}
                    </span>
                  </td>
                  <td className="font-medium text-slate-700">{chk.required}</td>
                  <td className="font-mono text-slate-900 font-semibold">{chk.actual}</td>
                  <td>
                    {chk.status === 'PASSED' ? (
                      <span className="badge badge-approved text-xs font-semibold">
                        <Check className="w-3 h-3" /> PASSED
                      </span>
                    ) : chk.status === 'WARNING' ? (
                      <span className="badge badge-needs-review text-xs font-semibold">
                        <AlertTriangle className="w-3 h-3" /> ATTENTION
                      </span>
                    ) : chk.status === 'PENDING' ? (
                      <span className="badge badge-pending text-xs font-semibold">NOT RUN</span>
                    ) : chk.status === 'FAILED' ? (
                      <span className="badge badge-rejected text-xs font-semibold">
                        <X className="w-3 h-3" /> FAILED
                      </span>
                    ) : (
                      <span className="badge badge-needs-review text-xs font-semibold">
                        <AlertTriangle className="w-3 h-3" /> REVIEW
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Historical Comparison & ML Risk Prediction */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Historical Comparison */}
        <div className="v-card p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Historical Supplier Comparison</h3>
            <p className="text-xs text-slate-500 mb-4">Stored supplier history for this batch</p>

            <div className="space-y-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-center justify-between text-xs">
                <span className="text-slate-600">Supplier Previous Lots</span>
                <span className="font-bold text-slate-900">
                  {batch.historical_comparison?.previous_batches_count ?? '—'} Lots
                </span>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-center justify-between text-xs">
                <span className="text-slate-600">Historical Approval Rate</span>
                <span className="font-bold text-emerald-600">
                  {batch.vendor?.approval_rate ?? '—'}% (
                  {batch.historical_comparison?.approved_count ?? '—'} Approved /{' '}
                  {batch.historical_comparison?.rejected_count ?? '—'} Rejected)
                </span>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-center justify-between text-xs">
                <span className="text-slate-600">Historical Average Purity</span>
                <span className="font-bold text-slate-900">
                  {batch.historical_comparison?.vendor_average_purity ?? '—'}%
                </span>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-center justify-between text-xs">
                <span className="text-slate-600">On-Time Fulfillment History</span>
                <span className="font-bold text-blue-700">
                  {batch.historical_comparison?.on_time_rate ?? '—'}%
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
            Statistical Purity Variance:{' '}
            <span className="font-semibold text-slate-800">
              {batch.historical_comparison?.variance || 'Not available'}
            </span>
          </div>
        </div>

        {/* ML Risk Prediction */}
        <div className="v-card p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">ML Risk Prediction Model</h3>
              <p className="text-xs text-slate-500">Random Forest Ensemble + Gradient Boosting</p>
            </div>
            {batch.prediction?.model_version && (
              <span className="font-mono text-[10px] bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                {batch.prediction.model_version}
              </span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-center">
              <span className="text-[10px] font-semibold text-slate-400 uppercase block">Risk Score</span>
              <span className="text-2xl font-black text-slate-900 mt-1 block">
                {batch.risk_score?.toFixed(1) ?? '—'}
              </span>
              <span className="text-[10px] text-slate-500">Scale: 0-100</span>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-center">
              <span className="text-[10px] font-semibold text-slate-400 uppercase block">Probability</span>
              <span className="text-2xl font-black text-slate-900 mt-1 block">
                {batch.risk_probability != null ? `${(batch.risk_probability * 100).toFixed(0)}%` : '—'}
              </span>
              <span className="text-[10px] text-slate-500">Lot Failure Chance</span>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-center flex flex-col justify-center">
              <span className="text-[10px] font-semibold text-slate-400 uppercase block">Risk Level</span>
              <div className="mt-1">
                <span className={`badge font-bold text-xs ${getRiskColor(batch.risk_level)}`}>
                  {batch.risk_level || 'UNKNOWN'}
                </span>
              </div>
            </div>
          </div>

          {/* Stored model feature importance */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-700 block">Top Predictive Features</span>
            {batch.prediction?.top_risk_factors?.length ? (
              <ul className="space-y-1.5 text-xs text-slate-600 list-disc pl-4">
                {batch.prediction.top_risk_factors.map((factor, index) => (
                  <li key={`${factor}-${index}`}>{factor}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">
                No feature explanation is available for this prediction.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 4. Kimi K3 AI Intelligence Section */}
      <div className="v-card p-6 border-blue-200/90 bg-gradient-to-br from-white via-white to-blue-50/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-sm">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Kimi K3 Batch Intelligence Report</h3>
              <p className="text-xs text-slate-500">Autonomous scientific reasoning and compliance synthesis</p>
            </div>
          </div>
          <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-blue-100 text-blue-800 tracking-wider">
            K3 ADVANCED REASONING
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
          {/* Left: Summary & Key Findings */}
          <div className="space-y-4">
            <div>
              <h4 className="font-bold text-slate-900 mb-1.5 uppercase tracking-wider text-[11px]">
                Executive Summary
              </h4>
              <div className="p-3.5 bg-white rounded-lg border border-slate-200 text-slate-700 leading-relaxed shadow-sm">
                {batch.kimi_intelligence?.summary || 'No AI assessment has been stored for this batch.'}
              </div>
            </div>

            <div>
              <h4 className="font-bold text-slate-900 mb-1.5 uppercase tracking-wider text-[11px]">
                Key Scientific Findings
              </h4>
              <ul className="space-y-2">
                {batch.kimi_intelligence?.key_findings?.length ? batch.kimi_intelligence.key_findings.map((finding, idx) => (
                  <li key={idx} className="flex items-start gap-2 p-2 rounded bg-slate-50 border border-slate-200/60 text-slate-700">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <span>{finding}</span>
                  </li>
                )) : (
                  <li className="text-xs text-slate-500">No findings are available.</li>
                )}
              </ul>
            </div>
          </div>

          {/* Right: Risk Factors, Business Impact, Recommended Actions */}
          <div className="space-y-4">
            <div>
              <h4 className="font-bold text-slate-900 mb-1.5 uppercase tracking-wider text-[11px]">
                Risk Factors & Business Impact
              </h4>
              <div className="p-3.5 bg-white rounded-lg border border-slate-200 space-y-2 text-slate-700 leading-relaxed shadow-sm">
                <p>
                  <strong className="text-slate-900">Business Impact:</strong>{' '}
                  {batch.kimi_intelligence?.business_impact || 'No business impact assessment is available.'}
                </p>
                <div>
                  <strong className="text-slate-900">Identified Risk Factors:</strong>
                  <ul className="list-disc pl-4 mt-1 space-y-1 text-slate-600">
                    {batch.kimi_intelligence?.risk_factors?.length ? batch.kimi_intelligence.risk_factors.map((rf, idx) => (
                      <li key={idx}>{rf}</li>
                    )) : <li>No risk factors are available.</li>}
                  </ul>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-bold text-slate-900 mb-1.5 uppercase tracking-wider text-[11px]">
                Recommended Actions
              </h4>
              <ul className="space-y-1.5">
                {batch.kimi_intelligence?.recommended_actions?.length ? batch.kimi_intelligence.recommended_actions.map((act, idx) => (
                  <li key={idx} className="flex items-start gap-2 p-2 rounded bg-blue-50/70 border border-blue-200/60 text-slate-700">
                    <span className="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">
                      {idx + 1}
                    </span>
                    <span>{act}</span>
                  </li>
                )) : <li className="text-xs text-slate-500">No actions are available.</li>}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Final Decision Controls & Email Status */}
      <div className="v-card p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">Decision & Dispatch Controls</h3>
            <p className="text-xs text-slate-500">
              Autonomous or human-in-the-loop sign-off with automated Google SMTP notification.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setShowOverrideBox(!showOverrideBox)}
              className="btn-secondary text-xs"
            >
              <span>Manual Override</span>
              <ChevronDown className="w-3.5 h-3.5 ml-1" />
            </button>

            <button
              onClick={() => {
                setOverrideDecision('APPROVED');
                setOverrideNotes('');
                setShowOverrideBox(true);
              }}
              disabled={decisionMutation.isPending}
              className="btn-primary bg-emerald-600 hover:bg-emerald-700 text-xs"
            >
              <Check className="w-3.5 h-3.5 mr-1" />
              Approve Lot
            </button>

            <button
              onClick={() => {
                setOverrideDecision('REJECTED');
                setOverrideNotes('');
                setShowOverrideBox(true);
              }}
              disabled={decisionMutation.isPending}
              className="btn-danger text-xs"
            >
              <X className="w-3.5 h-3.5 mr-1" />
              Reject Lot
            </button>
          </div>
        </div>

        {/* Override Drawer */}
        {showOverrideBox && (
          <div className="mt-4 p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-3">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Human Override Specification
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="form-label">Override Decision</label>
                <select
                  value={overrideDecision}
                  onChange={(e) => setOverrideDecision(e.target.value)}
                  className="form-select text-xs"
                >
                  <option value="">Select Decision</option>
                  <option value="APPROVED">APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                  <option value="NEEDS_REVIEW">NEEDS REVIEW</option>
                </select>
              </div>
              <div>
                <label className="form-label">Override Justification / Audit Notes</label>
                <input
                  type="text"
                  value={overrideNotes}
                  onChange={(e) => setOverrideNotes(e.target.value)}
                  placeholder="e.g. Authorized under deviation protocol DEV-2026-081"
                  className="form-input text-xs"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowOverrideBox(false)}
                className="btn-ghost text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!overrideDecision || !overrideNotes.trim() || decisionMutation.isPending}
                onClick={() =>
                  decisionMutation.mutate({
                    manual_override: true,
                    decision: overrideDecision,
                    notes: overrideNotes,
                  })
                }
                className="btn-primary text-xs"
              >
                Apply Override & Dispatch Email
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 6. Audit Timeline */}
      {/* Required Sequence: Email Received ↓ Documents Processed ↓ Validation Completed ↓ Risk Predicted ↓ Kimi Assessment ↓ Decision ↓ Email Sent */}
      <div className="v-card p-6">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-6 flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-600" />
          End-to-End Audit Trail Timeline
        </h3>

        <div className="space-y-3">
          {batch.timeline?.length ? (
            batch.timeline.map((event) => (
              <div key={event.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-900">{event.label}</span>
                  {event.timestamp && (
                    <time className="text-[11px] text-slate-500">
                      {new Date(event.timestamp).toLocaleString()}
                    </time>
                  )}
                </div>
                {event.details && Object.keys(event.details).length > 0 && (
                  <pre className="mt-2 whitespace-pre-wrap break-words text-[11px] text-slate-600">
                    {JSON.stringify(event.details, null, 2)}
                  </pre>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500">No audit events have been recorded for this batch.</p>
          )}
        </div>

        {false && (
        <div className="relative pl-6 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          {/* Step 1: Email Received */}
          <div className="relative flex items-start gap-4">
            <div className="absolute -left-6 top-1 w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center text-xs font-bold shadow-sm">
              <Check className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Email Received</span>
                <span className="text-[10px] text-slate-600">Automatic Ingestion</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Inbound shipment payload received from {batch.vendor?.name} for Batch {batch.batch_number}.
              </p>
            </div>
          </div>

          {/* Step 2: Documents Processed */}
          <div className="relative flex items-start gap-4">
            <div
              className={`absolute -left-6 top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-sm ${
                batch.documents?.length > 0 || batch.processed
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-300 text-white'
              }`}
            >
              {batch.documents?.length > 0 || batch.processed ? <Check className="w-3.5 h-3.5" /> : '2'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Documents Processed</span>
                <span className="text-[10px] text-slate-600">COA & SDS Extraction</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Extracted analytical assay, batch lot stamps, and chemical monograph records.
              </p>
            </div>
          </div>

          {/* Step 3: Validation Completed */}
          <div className="relative flex items-start gap-4">
            <div
              className={`absolute -left-6 top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-sm ${
                batch.validation_status || batch.processed
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-300 text-white'
              }`}
            >
              {batch.validation_status || batch.processed ? <Check className="w-3.5 h-3.5" /> : '3'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Validation Completed</span>
                <span className="text-[10px] text-slate-600">Deterministic Checks</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Evaluated against USP/EP purity requirements and facility GMP compliance.
              </p>
            </div>
          </div>

          {/* Step 4: Risk Predicted */}
          <div className="relative flex items-start gap-4">
            <div
              className={`absolute -left-6 top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-sm ${
                batch.risk_score !== undefined
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-300 text-white'
              }`}
            >
              {batch.risk_score !== undefined ? <Check className="w-3.5 h-3.5" /> : '4'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Risk Predicted</span>
                <span className="text-[10px] text-slate-600">ML Scoring Ensemble</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Calculated failure probability ({batch.risk_probability ? `${(batch.risk_probability * 100).toFixed(0)}%` : '15%'}) and risk level: {batch.risk_level || 'LOW'}.
              </p>
            </div>
          </div>

          {/* Step 5: Kimi Assessment */}
          <div className="relative flex items-start gap-4">
            <div
              className={`absolute -left-6 top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-sm ${
                batch.kimi_intelligence
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-300 text-white'
              }`}
            >
              {batch.kimi_intelligence ? <Check className="w-3.5 h-3.5" /> : '5'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Kimi Assessment</span>
                <span className="text-[10px] text-slate-600">Moonshot K3 Synthesis</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Generated contextual scientific synthesis, risk mitigation, and operational impact report.
              </p>
            </div>
          </div>

          {/* Step 6: Decision */}
          <div className="relative flex items-start gap-4">
            <div
              className={`absolute -left-6 top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-sm ${
                finalDecision ? 'bg-emerald-500 text-white' : 'bg-slate-300 text-white'
              }`}
            >
              {finalDecision ? <Check className="w-3.5 h-3.5" /> : '6'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Decision</span>
                <span className="text-[10px] text-slate-600">Autonomous Gate</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Final Lot Decision evaluated:{' '}
                <strong className={isApproved ? 'text-emerald-700' : isRejected ? 'text-rose-700' : 'text-amber-700'}>
                  {finalDecision || 'Awaiting Execution'}
                </strong>.
              </p>
            </div>
          </div>

          {/* Step 7: Email Sent */}
          <div className="relative flex items-start gap-4">
            <div
              className={`absolute -left-6 top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-sm ${
                batch.email_status === 'SENT' ? 'bg-emerald-500 text-white' : 'bg-slate-300 text-white'
              }`}
            >
              {batch.email_status === 'SENT' ? <Check className="w-3.5 h-3.5" /> : '7'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">Email Sent</span>
                <span className="text-[10px] text-slate-600">Google SMTP Dispatch</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Formal notification dispatched to {batch.vendor?.contact_email || 'vendor quality desk'}. Status:{' '}
                <span className="font-semibold text-slate-800">{batch.email_status}</span>.
              </p>
            </div>
          </div>
        </div>
        )}
      </div>

      {/* Upload Vendor PDF Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">Upload Vendor PDF Documentation</h3>
              </div>
              <button
                onClick={() => setIsUploadModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (uploadFile) uploadDocMutation.mutate(uploadFile);
              }}
              className="p-6 space-y-4"
            >
              <div>
                <label className="form-label">Vendor PDF File (COA / SDS / GMP) *</label>
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
                  <option value="SPECIFICATION">Material Specification Monograph</option>
                </select>
              </div>

              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
                <strong>Intake Pipeline:</strong> Uploading this document automatically extracts the analytical assay, verifies purity against material requirements, recalculates ML risk, and prepares the Moonshot Kimi K3 qualification report.
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
                  {uploadDocMutation.isPending ? 'Uploading & Extracting...' : 'Upload & Process Batch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
