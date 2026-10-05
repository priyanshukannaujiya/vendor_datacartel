import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Building2,
  Package,
  ShieldCheck,
  Download,
  ArrowRight,
  Clock,
  Sparkles,
  Check,
} from 'lucide-react';
import { documentApi, batchApi, vendorApi } from '../api/client';
import { DocumentRecord, Batch, Vendor } from '../types';

export const VendorPortalPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const queryClient = useQueryClient();

  const [selectedVendorId, setSelectedVendorId] = useState<string>('');
  const [selectedBatchId, setSelectedBatchId] = useState<string>('');
  const [docType, setDocType] = useState<string>('COA');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);

  // Load vendors & batches
  const { data: vendors = [], isLoading: isVendorsLoading } = useQuery<Vendor[]>({
    queryKey: ['vendors-portal'],
    queryFn: () => vendorApi.getAll(),
  });

  const { data: batches = [], isLoading: isBatchesLoading } = useQuery<Batch[]>({
    queryKey: ['batches-portal'],
    queryFn: () => batchApi.getAll(),
  });

  const { data: allDocs = [], refetch: refetchDocs } = useQuery<DocumentRecord[]>({
    queryKey: ['documents-portal'],
    queryFn: () => documentApi.getAll(),
  });

  // Filter batches for the selected vendor
  const vendorBatches = batches.filter((b) => !selectedVendorId || b.vendor_id === selectedVendorId);

  // Filter documents submitted by or associated with this vendor
  const vendorDocs = allDocs.filter(
    (d) => !selectedVendorId || d.vendor_id === selectedVendorId || (selectedBatchId && d.batch_id === selectedBatchId)
  );

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; meta: { document_type: string; batch_id?: string; vendor_id?: string } }) =>
      documentApi.upload(data.file, data.meta),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['documents-portal'] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      setUploadSuccessMessage(
        `Document "${res.original_filename || res.filename}" successfully uploaded and registered! Automated OCR & assay extraction in progress.`
      );
      setUploadFile(null);
      setTimeout(() => setUploadSuccessMessage(null), 8000);
    },
  });

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    uploadMutation.mutate({
      file: uploadFile,
      meta: {
        document_type: docType,
        batch_id: selectedBatchId || undefined,
        vendor_id: selectedVendorId || undefined,
      },
    });
  };

  const selectedVendor = vendors.find((v) => v.id === selectedVendorId);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 py-4 sticky top-0 z-30 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-black text-white text-base shadow-lg shadow-blue-500/20">
            V
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white tracking-tight text-lg">VendorIQ</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Supplier Intake
              </span>
            </div>
            <p className="text-xs text-slate-400">Secure Document & Compliance Portal</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Link
            to="/login"
            className="text-xs font-semibold text-slate-400 hover:text-white transition-colors"
          >
            Internal Team Sign In &rarr;
          </Link>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 md:p-10 space-y-8">
        {/* Hero Title */}
        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Supplier Compliance & Document Submission
          </h1>
          <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
            Please submit Certificates of Analysis (COA), Safety Data Sheets (SDS), and GMP lot release records for incoming material qualification.
          </p>
        </div>

        {/* Success Alert */}
        {uploadSuccessMessage && (
          <div className="p-4 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-200 text-sm flex items-start gap-3 shadow-lg shadow-emerald-900/20 animate-in fade-in">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">{uploadSuccessMessage}</p>
              <p className="text-xs text-emerald-300/80 mt-1">
                Your file has been cataloged in the repository and linked directly to your quality record.
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Form Card */}
          <div className="lg:col-span-2 rounded-2xl bg-slate-800/80 border border-slate-700/80 p-6 md:p-8 space-y-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-700/80 pb-4">
              <div className="flex items-center gap-2.5">
                <UploadCloud className="w-5 h-5 text-blue-400" />
                <h2 className="text-base font-bold text-white">Upload Compliance Documents</h2>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">PDF, DOCX &bull; Max 25MB</span>
            </div>

            <form onSubmit={handleUpload} className="space-y-5">
              {/* Select Vendor */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Select Your Supplier Organization *
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <select
                    value={selectedVendorId}
                    onChange={(e) => setSelectedVendorId(e.target.value)}
                    required
                    className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 pl-10 text-xs text-white focus:outline-none focus:border-blue-500 transition-colors"
                  >
                    <option value="">Choose Supplier Organization...</option>
                    {vendors.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name || (v as any).vendor_name} ({v.contact_email || (v as any).email || 'No email'})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Select Batch (optional/recommended) */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Associated Lot / Batch Reference (Optional)
                </label>
                <div className="relative">
                  <Package className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <select
                    value={selectedBatchId}
                    onChange={(e) => setSelectedBatchId(e.target.value)}
                    className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 pl-10 text-xs text-white focus:outline-none focus:border-blue-500 transition-colors"
                  >
                    <option value="">General Supplier Monograph (No Specific Lot)</option>
                    {vendorBatches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.batch_number} &bull; {b.raw_material?.name || 'Raw Material'} &bull; Status: {b.decision_status || 'PENDING'}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Document Category */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Document Type *
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'COA', label: 'Certificate of Analysis (COA)' },
                    { id: 'SDS', label: 'Safety Data Sheet (SDS)' },
                    { id: 'GMP', label: 'GMP Certificate' },
                    { id: 'SPECIFICATION', label: 'Product Spec' },
                  ].map((t) => (
                    <button
                      type="button"
                      key={t.id}
                      onClick={() => setDocType(t.id)}
                      className={`p-3 rounded-xl border text-left text-xs font-semibold transition-all ${
                        docType === t.id
                          ? 'bg-blue-600/20 border-blue-500 text-blue-300 ring-1 ring-blue-500'
                          : 'bg-slate-900/50 border-slate-700 text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <div className="font-mono text-[11px] font-bold text-white mb-0.5">{t.id}</div>
                      <div className="text-[10px] text-slate-400 line-clamp-1">{t.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* File Dropzone */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Upload PDF File *
                </label>
                <div className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-2xl p-6 text-center bg-slate-900/40 transition-colors">
                  <input
                    type="file"
                    required
                    accept=".pdf,.docx,.xlsx,.png,.jpg"
                    onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                    className="hidden"
                    id="file-upload-portal"
                  />
                  <label htmlFor="file-upload-portal" className="cursor-pointer block space-y-2">
                    <div className="w-12 h-12 rounded-2xl bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto">
                      <FileText className="w-6 h-6" />
                    </div>
                    {uploadFile ? (
                      <div>
                        <p className="text-sm font-bold text-white">{uploadFile.name}</p>
                        <p className="text-xs text-slate-400 font-mono mt-0.5">
                          {(uploadFile.size / 1024).toFixed(1)} KB &bull; Click to choose another
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm font-semibold text-white">Click or drag & drop PDF attachment here</p>
                        <p className="text-xs text-slate-400 mt-1">Accepts Certificates of Analysis, SDS, and lot records</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={uploadMutation.isPending || !uploadFile || !selectedVendorId}
                  className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-sm shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>
                    {uploadMutation.isPending ? 'Uploading & Parsing Document...' : 'Submit Document for Compliance Verification'}
                  </span>
                </button>
              </div>

              {uploadMutation.isError && (
                <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>
                    {(uploadMutation.error as any)?.response?.data?.detail ||
                      (uploadMutation.error as Error)?.message ||
                      'Upload failed. Please check network connection.'}
                  </span>
                </div>
              )}
            </form>
          </div>

          {/* Supplier Info & Quick Status */}
          <div className="space-y-6">
            <div className="rounded-2xl bg-slate-800/80 border border-slate-700/80 p-6 space-y-4 shadow-xl">
              <div className="flex items-center gap-2 text-slate-300 font-semibold text-xs uppercase tracking-wider">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Verification Requirements</span>
              </div>
              <ul className="text-xs text-slate-400 space-y-2.5">
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span><strong>HPLC / GC Assay:</strong> Purity verification matching raw material specification.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Impurity Limits:</strong> Heavy metals below 5 ppm, residual solvents verified.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span><strong>cGMP Lot Sign-off:</strong> Formal QA laboratory release stamp and sign-off.</span>
                </li>
              </ul>
            </div>

            {/* Recently Submitted by Vendor */}
            <div className="rounded-2xl bg-slate-800/80 border border-slate-700/80 p-6 space-y-3 shadow-xl">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Cataloged Documents ({vendorDocs.length})
              </h3>
              {vendorDocs.length === 0 ? (
                <p className="text-xs text-slate-500 italic">
                  No documents found for this supplier yet. Upload your first PDF to verify compliance.
                </p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {vendorDocs.slice(0, 5).map((doc) => (
                    <div
                      key={doc.id}
                      className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-700/60 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <FileText className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                        <span className="font-semibold text-white truncate max-w-[140px]">
                          {doc.original_filename || doc.filename}
                        </span>
                      </div>
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {doc.document_type}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6 px-6 text-center text-xs text-slate-500">
        VendorIQ Autonomous Supplier Quality & Batch Intelligence System &bull; Secure Encrypted Ingestion
      </footer>
    </div>
  );
};
