import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FileText,
  UploadCloud,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  RefreshCw,
  ExternalLink,
  Download,
  Trash2,
  Building2,
  Package,
  X,
  Mail,
} from 'lucide-react';
import { documentApi, batchApi, vendorApi } from '../api/client';
import { DocumentRecord, Batch, Vendor } from '../types';

export const DocumentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentRecord | null>(null);
  const [syncStatusMsg, setSyncStatusMsg] = useState<{ text: string; isError?: boolean } | null>(null);

  // Upload Form
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [selectedBatchId, setSelectedBatchId] = useState('');
  const [selectedVendorId, setSelectedVendorId] = useState('');
  const [docType, setDocType] = useState('COA');

  const { data: documents = [], isLoading, refetch } = useQuery<DocumentRecord[]>({
    queryKey: ['documents'],
    queryFn: () => documentApi.getAll(),
  });

  const { data: batches = [] } = useQuery<Batch[]>({
    queryKey: ['batches-list'],
    queryFn: () => batchApi.getAll(),
  });

  const { data: vendors = [] } = useQuery<Vendor[]>({
    queryKey: ['vendors-list'],
    queryFn: () => vendorApi.getAll(),
  });

  const syncMutation = useMutation({
    mutationFn: () => documentApi.syncInbox(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      if (data.new_documents_count > 0) {
        setSyncStatusMsg({
          text: `Inbox checked! Imported ${data.new_documents_count} new document attachment(s) from vendor email replies.`,
        });
      } else {
        setSyncStatusMsg({
          text: data.message || 'Mailbox checked. All vendor document replies are up to date.',
        });
      }
      setTimeout(() => setSyncStatusMsg(null), 8000);
    },
    onError: (err: any) => {
      setSyncStatusMsg({
        text: `Mailbox check failed: ${err?.response?.data?.message || err.message}`,
        isError: true,
      });
      setTimeout(() => setSyncStatusMsg(null), 8000);
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; meta: { document_type: string; batch_id?: string; vendor_id?: string } }) =>
      documentApi.upload(data.file, data.meta),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      if (variables.meta.batch_id) {
        queryClient.invalidateQueries({ queryKey: ['batch', variables.meta.batch_id] });
      }
      setIsUploadModalOpen(false);
      setUploadFile(null);
      setSelectedBatchId('');
      setSelectedVendorId('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleUploadSubmit = (e: React.FormEvent) => {
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

  const handleBatchChange = (batchId: string) => {
    setSelectedBatchId(batchId);
    if (batchId) {
      const b = (batches as Batch[]).find((item) => item.id === batchId);
      if (b && b.vendor_id) {
        setSelectedVendorId(b.vendor_id);
      }
    }
  };

  const docList = Array.isArray(documents) ? documents : [];
  const batchList = Array.isArray(batches) ? batches : [];
  const vendorList = Array.isArray(vendors) ? vendors : [];

  const filteredDocs = docList.filter((doc) => {
    const filename = doc.filename || '';
    const origFilename = doc.original_filename || '';
    const docType = doc.document_type || '';
    const vendorName = doc.vendor_name || '';
    const batchNumber = doc.batch_number || '';
    const matchesSearch =
      filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      origFilename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      docType.toLowerCase().includes(searchTerm.toLowerCase()) ||
      vendorName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      batchNumber.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = !docTypeFilter || doc.document_type === docTypeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Document Repository & OCR</h1>
          <p className="text-sm text-slate-500 mt-1">
            Certificates of Analysis (COA), Safety Data Sheets (SDS), and GMP lot monographs submitted by vendors or uploaded for lot compliance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="btn-secondary"
            title="Poll Gmail inbox for supplier email replies with PDF attachments"
          >
            <RefreshCw className={`w-4 h-4 mr-1.5 ${syncMutation.isPending ? 'animate-spin text-teal-600' : ''}`} />
            <span>{syncMutation.isPending ? 'Checking Emails...' : 'Sync Vendor Emails'}</span>
          </button>
          <button onClick={() => setIsUploadModalOpen(true)} className="btn-primary">
            <UploadCloud className="w-4 h-4 mr-1.5" />
            <span>Upload Document</span>
          </button>
        </div>
      </div>

      {/* Sync Status Banner */}
      {syncStatusMsg && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between transition-all shadow-sm ${
            syncStatusMsg.isError
              ? 'bg-rose-50 border-rose-200 text-rose-900'
              : 'bg-emerald-50 border-emerald-200 text-emerald-900'
          }`}
        >
          <div className="flex items-center gap-3">
            <Mail className={`w-5 h-5 shrink-0 ${syncStatusMsg.isError ? 'text-rose-600' : 'text-emerald-600'}`} />
            <span className="text-sm font-medium">{syncStatusMsg.text}</span>
          </div>
          <button
            onClick={() => setSyncStatusMsg(null)}
            className="text-slate-400 hover:text-slate-600 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search and Filters */}
      <div className="v-card p-4 flex flex-col md:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by filename, vendor name, batch number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10"
          />
        </div>

        <div className="w-full md:w-56">
          <select
            value={docTypeFilter}
            onChange={(e) => setDocTypeFilter(e.target.value)}
            className="form-select text-xs"
          >
            <option value="">All Document Types</option>
            <option value="COA">Certificate of Analysis (COA)</option>
            <option value="SDS">Safety Data Sheet (SDS)</option>
            <option value="GMP">GMP Certificate</option>
            <option value="SPECIFICATION">Raw Material Spec</option>
            <option value="OTHER">Other Documents</option>
          </select>
        </div>
      </div>

      {/* Documents Table */}
      <div className="v-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Type</th>
                <th>Vendor / Supplier</th>
                <th>Linked Batch</th>
                <th>File Size</th>
                <th>Extraction Status</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="text-center py-10">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
                    <span className="text-xs text-slate-500">Scanning repository...</span>
                  </td>
                </tr>
              ) : filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-16 px-4">
                    <div className="max-w-md mx-auto text-center space-y-3">
                      <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto shadow-sm">
                        <FileText className="w-6 h-6" />
                      </div>
                      <h3 className="text-base font-bold text-slate-900">
                        {docList.length === 0 ? 'No compliance documents cataloged yet' : 'No matching documents found'}
                      </h3>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        {docList.length === 0
                          ? 'Documents appear here automatically when suppliers email their Certificates of Analysis (COA) and SDS attachments, when vendors submit files via their portal, or when you upload files manually.'
                          : 'Try adjusting your search query or document type filter.'}
                      </p>
                      {docList.length === 0 && (
                        <div className="pt-2">
                          <button
                            onClick={() => setIsUploadModalOpen(true)}
                            className="btn-primary text-xs"
                          >
                            <UploadCloud className="w-3.5 h-3.5 mr-1" />
                            <span>Upload First Document</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-slate-900 text-xs">
                            {doc.original_filename || doc.filename}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono truncate max-w-[180px]">
                            {doc.filename}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800">
                        {doc.document_type}
                      </span>
                    </td>
                    <td>
                      {doc.vendor_name ? (
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
                          <Building2 className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                          <span className="truncate max-w-[140px]">{doc.vendor_name}</span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td>
                      {doc.batch_number ? (
                        doc.batch_id ? (
                          <Link
                            to={`/batches/${doc.batch_id}`}
                            className="inline-flex items-center gap-1 text-xs font-mono font-semibold text-blue-600 hover:underline"
                          >
                            <Package className="w-3 h-3 text-blue-500" />
                            <span>{doc.batch_number}</span>
                          </Link>
                        ) : (
                          <span className="font-mono text-xs font-semibold text-slate-700">{doc.batch_number}</span>
                        )
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td>
                      <span className="text-xs text-slate-600 font-mono">
                        {doc.file_size != null ? `${(doc.file_size / 1024).toFixed(1)} KB` : '—'}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge text-xs ${
                          ['PROCESSED', 'EXTRACTED', 'COMPLETED'].includes(doc.extraction_status?.toUpperCase() || '')
                            ? 'badge-approved'
                            : 'badge-pending'
                        }`}
                      >
                        {doc.extraction_status || 'UPLOADED'}
                      </span>
                    </td>
                    <td>
                      <span className="text-xs text-slate-600">
                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => setSelectedDoc(doc)}
                          className="btn-ghost text-xs text-blue-600 font-semibold px-2 py-1"
                          title="Inspect Extracted OCR Data"
                        >
                          Inspect
                        </button>
                        <a
                          href={documentApi.downloadUrl(doc.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-ghost text-xs text-slate-600 hover:text-blue-600 p-1.5"
                          title="Download Document"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                        <button
                          onClick={() => {
                            if (window.confirm(`Delete document "${doc.original_filename || doc.filename}"?`)) {
                              deleteMutation.mutate(doc.id);
                            }
                          }}
                          disabled={deleteMutation.isPending}
                          className="btn-ghost text-xs text-slate-400 hover:text-rose-600 p-1.5"
                          title="Delete Document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document Data Inspector Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-xl overflow-hidden animate-in fade-in">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-blue-600" />
                <h3 className="text-sm font-semibold text-slate-900">Extracted Document Metadata</h3>
              </div>
              <button onClick={() => setSelectedDoc(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 text-xs space-y-1.5">
                <p>
                  <strong className="text-slate-900">Filename:</strong> {selectedDoc.original_filename || selectedDoc.filename}
                </p>
                <p>
                  <strong className="text-slate-900">Document Type:</strong> {selectedDoc.document_type}
                </p>
                {selectedDoc.vendor_name && (
                  <p>
                    <strong className="text-slate-900">Supplier:</strong> {selectedDoc.vendor_name}
                  </p>
                )}
                {selectedDoc.batch_number && (
                  <p>
                    <strong className="text-slate-900">Batch Number:</strong> {selectedDoc.batch_number}
                  </p>
                )}
                <p>
                  <strong className="text-slate-900">Status:</strong> {selectedDoc.extraction_status || 'UPLOADED'}
                </p>
              </div>

              <div>
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                  OCR / Parser Extracted Fields
                </h4>
                {selectedDoc.extracted_data && Object.keys(selectedDoc.extracted_data).length > 0 ? (
                  <pre className="p-3 rounded-lg bg-slate-900 text-emerald-400 text-xs font-mono overflow-x-auto max-h-60">
                    {JSON.stringify(selectedDoc.extracted_data, null, 2)}
                  </pre>
                ) : (
                  <p className="text-xs text-slate-500 italic p-3 bg-slate-50 rounded border border-slate-200">
                    No structured metadata extracted yet. The document is queued or text parsing did not locate key assay fields.
                  </p>
                )}
              </div>

              <div className="flex justify-between items-center pt-2">
                <a
                  href={documentApi.downloadUrl(selectedDoc.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary text-xs flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Raw PDF</span>
                </a>
                <button
                  type="button"
                  onClick={() => setSelectedDoc(null)}
                  className="btn-primary text-xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">Upload Compliance Document</h3>
              <button onClick={() => setIsUploadModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleUploadSubmit} className="p-6 space-y-4">
              <div>
                <label className="form-label">Document File (PDF / DOCX) *</label>
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.xlsx,.png,.jpg"
                  onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                  className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>

              <div>
                <label className="form-label">Document Type *</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="form-select text-xs"
                >
                  <option value="COA">Certificate of Analysis (COA)</option>
                  <option value="SDS">Safety Data Sheet (SDS)</option>
                  <option value="GMP">GMP Certificate</option>
                  <option value="SPECIFICATION">Material Specification Monograph</option>
                  <option value="OTHER">Other Compliance Document</option>
                </select>
              </div>

              <div>
                <label className="form-label">Attach to Batch (Recommended)</label>
                <select
                  value={selectedBatchId}
                  onChange={(e) => handleBatchChange(e.target.value)}
                  className="form-select text-xs"
                >
                  <option value="">No Specific Batch (General Compliance Document)</option>
                  {batchList.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.batch_number} — {b.vendor?.name || (b.vendor as any)?.vendor_name || 'Assigned Vendor'}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="form-label">Assign to Supplier / Vendor</label>
                <select
                  value={selectedVendorId}
                  onChange={(e) => setSelectedVendorId(e.target.value)}
                  className="form-select text-xs"
                >
                  <option value="">Auto-detected or No Vendor</option>
                  {vendorList.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name || (v as any).vendor_name} ({v.contact_email || (v as any).email || 'No email'})
                    </option>
                  ))}
                </select>
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
                  disabled={uploadMutation.isPending || !uploadFile}
                  className="btn-primary"
                >
                  {uploadMutation.isPending ? 'Extracting...' : 'Upload & Extract'}
                </button>
              </div>
              {uploadMutation.isError && (
                <p role="alert" className="text-xs text-rose-700">
                  {(uploadMutation.error as any)?.response?.data?.detail ||
                    (uploadMutation.error as Error)?.message ||
                    'Document upload failed.'}
                </p>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
