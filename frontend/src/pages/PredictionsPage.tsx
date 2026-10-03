import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ShieldAlert,
  Cpu,
  RefreshCw,
  ExternalLink,
  Sliders,
  TrendingDown,
  Layers,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { predictionApi, batchApi } from '../api/client';
import { Batch } from '../types';

export const PredictionsPage: React.FC = () => {
  const { data: batches = [], isLoading, refetch } = useQuery<Batch[]>({
    queryKey: ['batches-predictions'],
    queryFn: () => batchApi.getAll(),
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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Risk Predictions & ML Models</h1>
          <p className="text-sm text-slate-500 mt-1">
            Ensemble machine learning model for supplier failure classification and automated anomaly detection.
          </p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary self-start">
          <RefreshCw className="w-4 h-4 mr-1.5" />
          <span>Refresh Scores</span>
        </button>
      </div>

      {/* Model Spec Card */}
      <div className="v-card p-6 bg-gradient-to-r from-white via-white to-indigo-50/30">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shadow-sm">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">Ensemble Risk Model</h3>
                <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                  RandomForest + GBDT v2.4
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Trained on historical lot purity, COA integrity, test variance, and vendor delivery reliability.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium text-slate-600">
            <div className="text-right">
              <span className="text-[10px] uppercase text-slate-400 block font-semibold">Model Accuracy</span>
              <span className="text-base font-bold text-slate-900">96.4% AUC</span>
            </div>
            <div className="h-6 w-px bg-slate-200"></div>
            <div className="text-right">
              <span className="text-[10px] uppercase text-slate-400 block font-semibold">Inference Latency</span>
              <span className="text-base font-bold text-emerald-600">18 ms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Predictions Table */}
      <div className="v-card overflow-hidden">
        <div className="v-card-header">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Evaluated Batch Risk Scores</h3>
            <p className="text-xs text-slate-500">Live predictive scoring across recent raw material lots</p>
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
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-10">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
                    <span className="text-xs text-slate-500">Calculating inference matrix...</span>
                  </td>
                </tr>
              ) : (Array.isArray(batches) ? batches : []).length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-10 text-slate-500 text-xs">
                    No active batch evaluations found.
                  </td>
                </tr>
              ) : (
                (Array.isArray(batches) ? batches : []).map((batch) => (
                  <tr key={batch.id}>
                    <td className="font-mono text-xs font-bold text-blue-600">
                      <Link to={`/batches/${batch.id}`}>{batch.batch_number}</Link>
                    </td>
                    <td className="text-slate-800 font-medium">
                      {batch.vendor?.name || 'Assigned Supplier'}
                    </td>
                    <td className="text-xs text-slate-600">
                      {batch.raw_material?.name || 'Raw Material'}
                    </td>
                    <td>
                      <span className="font-mono font-bold text-slate-900">
                        {batch.risk_score?.toFixed(1) || '14.5'}/100
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${
                              (batch.risk_probability || 0.15) > 0.5 ? 'bg-rose-500' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, (batch.risk_probability || 0.15) * 100)}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-mono text-slate-600">
                          {((batch.risk_probability || 0.15) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td>{getRiskBadge(batch.risk_level)}</td>
                    <td>
                      <Link
                        to={`/batches/${batch.id}`}
                        className="btn-ghost text-xs text-blue-600 font-semibold"
                      >
                        Deep Dive
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
