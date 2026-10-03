import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Cpu,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Mail,
  Send,
  X,
  Check,
  ShieldCheck,
} from 'lucide-react';
import { predictionApi, batchApi } from '../api/client';
import { MLPrediction } from '../types';

export const PredictionsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedPrediction, setSelectedPrediction] = useState<MLPrediction | null>(null);
  const [decisionChoice, setDecisionChoice] = useState<'APPROVED' | 'REJECTED' | 'NEEDS_REVIEW'>('APPROVED');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { data: predictions = [], isLoading, refetch } = useQuery<MLPrediction[]>({
    queryKey: ['predictions'],
    queryFn: () => predictionApi.getAll(),
  });

  const decisionMutation = useMutation({
    mutationFn: (data: { batchId: string; decision: string; notes: string }) =>
      batchApi.makeDecision(data.batchId, {
        manual_override: true,
        decision: data.decision,
        notes: data.notes,
      }),
    onSuccess: (res, variables) => {
      queryClient.invalidateQueries({ queryKey: ['predictions'] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics'] });
      
      const statusText = res.decision_status || variables.decision;
      const emailRecipient = (res as any).email_recipient || (res as any).recipient || 'supplier';
      
      setFeedbackMessage({
        type: 'success',
        text: `Vendor Lot decision set to ${statusText}! Confirmation email dispatched via Google SMTP.`,
      });
      setSelectedPrediction(null);
      setDecisionNotes('');
    },
    onError: (err: any) => {
      setFeedbackMessage({
        type: 'error',
        text: `Decision submission failed: ${err.response?.data?.detail || err.message}`,
      });
    },
  });

  const handleOpenDecisionModal = (pred: MLPrediction, defaultDecision: 'APPROVED' | 'REJECTED') => {
    setSelectedPrediction(pred);
    setDecisionChoice(defaultDecision);
    setDecisionNotes(
      defaultDecision === 'APPROVED'
        ? `Vendor documents and specification validated. Batch approved under QA review.`
        : `Batch rejected due to non-compliant specifications or elevated risk score.`
    );
    setFeedbackMessage(null);
  };

  const handleDecisionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPrediction || !selectedPrediction.batch_id) return;
    decisionMutation.mutate({
      batchId: selectedPrediction.batch_id,
      decision: decisionChoice,
      notes: decisionNotes,
    });
  };

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

  const getStatusBadge = (status?: string) => {
    switch (status?.toUpperCase()) {
      case 'APPROVED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" /> APPROVED
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <XCircle className="w-3 h-3 mr-1 text-rose-600" /> REJECTED
          </span>
        );
      case 'NEEDS_REVIEW':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3 h-3 mr-1 text-amber-600" /> NEEDS REVIEW
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            {status || 'EVALUATED'}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Risk Predictions & Supplier Approvals</h1>
          <p className="text-sm text-slate-500 mt-1">
            Machine learning batch risk scoring, autonomous qualification decisioning, and email dispatch center.
          </p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary self-start">
          <RefreshCw className="w-4 h-4 mr-1.5" />
          <span>Refresh Scores</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedbackMessage && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between text-sm animate-in fade-in duration-200 ${
            feedbackMessage.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <div className="flex items-center gap-3">
            {feedbackMessage.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
            )}
            <div>
              <p className="font-semibold">{feedbackMessage.text}</p>
              {feedbackMessage.type === 'success' && (
                <p className="text-xs text-emerald-700 mt-0.5">
                  The decision record was saved to the audit log and an official certificate/notice was sent via Google SMTP.
                </p>
              )}
            </div>
          </div>
          <button onClick={() => setFeedbackMessage(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Model Spec Card */}
      <div className="v-card p-6 bg-gradient-to-r from-white via-white to-indigo-50/30">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shadow-sm">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">Backend Risk Scoring & QA Decisioning</h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Review machine learning inferences and perform 1-click batch document approvals with automated email confirmations.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Predictions Table */}
      <div className="v-card overflow-hidden">
        <div className="v-card-header flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Evaluated Batch Risk Scores & Vendor Document Approvals</h3>
            <p className="text-xs text-slate-500">Predictive scoring and QA approval dispatch across raw material lots</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Batch Number</th>
                <th>Supplier</th>
                <th>Material</th>
                <th>ML Risk Score</th>
                <th>Failure Probability</th>
                <th>Risk Tier</th>
                <th>Qualification Status</th>
                <th className="text-right">QA Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="text-center py-10">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
                    <span className="text-xs text-slate-500">Calculating inference matrix...</span>
                  </td>
                </tr>
              ) : (Array.isArray(predictions) ? predictions : []).length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-500 text-xs">
                    No active batch evaluations found.
                  </td>
                </tr>
              ) : (
                (Array.isArray(predictions) ? predictions : []).map((prediction, index) => (
                  <tr key={prediction.id || prediction.batch_id || index}>
                    <td className="font-mono text-xs font-bold text-blue-600">
                      {prediction.batch_id ? (
                        <Link to={`/batches/${prediction.batch_id}`}>
                          {prediction.batch_number || prediction.batch_id}
                        </Link>
                      ) : (
                        prediction.batch_number || '—'
                      )}
                    </td>
                    <td className="text-slate-800 font-medium">{prediction.vendor_name || '—'}</td>
                    <td className="text-xs text-slate-600">{prediction.raw_material_name || '—'}</td>
                    <td>
                      <span className="font-mono font-bold text-slate-900">
                        {prediction.risk_score?.toFixed(1) ?? '—'}
                      </span>
                    </td>
                    <td>
                      {prediction.risk_probability == null ? (
                        <span className="text-xs text-slate-500">—</span>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full ${
                                prediction.risk_probability > 0.5 ? 'bg-rose-500' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(100, prediction.risk_probability * 100)}%` }}
                            ></div>
                          </div>
                          <span className="text-xs font-mono text-slate-600">
                            {(prediction.risk_probability * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </td>
                    <td>{getRiskBadge(prediction.risk_level)}</td>
                    <td>{getStatusBadge(prediction.batch_status)}</td>
                    <td className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {prediction.batch_id ? (
                          <>
                            <button
                              onClick={() => handleOpenDecisionModal(prediction, 'APPROVED')}
                              title="Approve Vendor Documents & Send Email Confirmation"
                              className="px-2.5 py-1 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition-colors flex items-center gap-1"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Approve</span>
                            </button>
                            <button
                              onClick={() => handleOpenDecisionModal(prediction, 'REJECTED')}
                              title="Reject Vendor Documents & Send Email Notice"
                              className="px-2.5 py-1 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg transition-colors flex items-center gap-1"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>
                            <Link
                              to={`/batches/${prediction.batch_id}`}
                              className="p-1 text-slate-400 hover:text-blue-600 transition-colors"
                              title="Deep Dive Batch Details"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </Link>
                          </>
                        ) : (
                          <span className="text-xs text-slate-400">Unavailable</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Decision Modal */}
      {selectedPrediction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in duration-150">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-semibold text-slate-900">
                  QA Decision & Email Confirmation
                </h3>
              </div>
              <button
                onClick={() => setSelectedPrediction(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleDecisionSubmit} className="p-6 space-y-4">
              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 text-xs space-y-1">
                <p>
                  <span className="font-semibold text-slate-700">Batch Number:</span>{' '}
                  <span className="font-mono font-bold text-blue-600">{selectedPrediction.batch_number}</span>
                </p>
                <p>
                  <span className="font-semibold text-slate-700">Supplier:</span> {selectedPrediction.vendor_name}
                </p>
                <p>
                  <span className="font-semibold text-slate-700">Material:</span> {selectedPrediction.raw_material_name}
                </p>
                <p>
                  <span className="font-semibold text-slate-700">ML Risk Score:</span>{' '}
                  <span className="font-mono font-bold">{selectedPrediction.risk_score?.toFixed(1)}</span> ({selectedPrediction.risk_level} Risk)
                </p>
              </div>

              <div>
                <label className="form-label">Qualification Decision *</label>
                <div className="grid grid-cols-3 gap-2 mt-1">
                  <button
                    type="button"
                    onClick={() => setDecisionChoice('APPROVED')}
                    className={`py-2 px-3 text-xs font-bold rounded-lg border flex items-center justify-center gap-1.5 transition-all ${
                      decisionChoice === 'APPROVED'
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-200 hover:border-emerald-300'
                    }`}
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>APPROVE</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDecisionChoice('REJECTED')}
                    className={`py-2 px-3 text-xs font-bold rounded-lg border flex items-center justify-center gap-1.5 transition-all ${
                      decisionChoice === 'REJECTED'
                        ? 'bg-rose-600 text-white border-rose-600 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-200 hover:border-rose-300'
                    }`}
                  >
                    <XCircle className="w-4 h-4" />
                    <span>REJECT</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDecisionChoice('NEEDS_REVIEW')}
                    className={`py-2 px-3 text-xs font-bold rounded-lg border flex items-center justify-center gap-1.5 transition-all ${
                      decisionChoice === 'NEEDS_REVIEW'
                        ? 'bg-amber-500 text-white border-amber-500 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-200 hover:border-amber-300'
                    }`}
                  >
                    <AlertTriangle className="w-4 h-4" />
                    <span>NEEDS REVIEW</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="form-label">QA Officer Reason / Audit Notes *</label>
                <textarea
                  required
                  rows={3}
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                  placeholder="Provide technical justification for batch qualification..."
                  className="form-input text-xs"
                />
              </div>

              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-xs text-blue-800 flex items-start gap-2">
                <Mail className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span>
                  <strong className="font-semibold">Automated Email Dispatch:</strong> Submitting this decision will automatically render the official vendor document certificate and dispatch a email confirmation via Google SMTP to the supplier.
                </span>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setSelectedPrediction(null)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={decisionMutation.isPending}
                  className={`btn-primary ${
                    decisionChoice === 'APPROVED'
                      ? 'bg-emerald-600 hover:bg-emerald-700'
                      : decisionChoice === 'REJECTED'
                      ? 'bg-rose-600 hover:bg-rose-700'
                      : 'bg-amber-600 hover:bg-amber-700'
                  }`}
                >
                  {decisionMutation.isPending ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin mr-1.5" />
                      <span>Submitting & Sending Email...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-1.5" />
                      <span>Confirm {decisionChoice} & Send Email</span>
                    </>
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

export default PredictionsPage;
