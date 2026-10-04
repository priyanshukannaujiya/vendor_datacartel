import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Trash2,
  X,
} from 'lucide-react';
import { documentApi, batchApi } from '../api/client';
import { DocumentRecord, Batch } from '../types';

export const DocumentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentRecord | null>(null);

  // Upload Form
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [selectedBatchId, setSelectedBatchId] = useState('');
  const [docType, setDocType] = useState('COA');

  const { data: documents = [], isLoading, refetch } = useQuery<DocumentRecord[]>({
    queryKey: ['documents'],
    queryFn: () => documentApi.getAll(),
  });

  const { data: batches = [] } = useQuery<Batch[]>({
    queryKey: ['batches-list'],
    queryFn: () => batchApi.getAll(),
  });

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File; meta: { document_type: string; batch_id?: string } }) =>
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
      },
    });
  };

  const docList = Array.isArray(documents) ? documents : [];
  const batchList = Array.isArray(batches) ? batches : [];

  const filteredDocs = docList.filter((doc) => {
    const filename = doc.filename || '';
    const origFilename = doc.original_filename || '';
    const docType = doc.document_type || '';
    const matchesSearch =
      filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      origFilename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      docType.toLowerCase().includes(searchTerm.toLowerCase());
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
            Certificates of Analysis (COA), Safety Data Sheets (SDS), and GMP lot monographs.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => refetch()} className="btn-secondary">
            <RefreshCw className="w-4 h-4 mr-1.5" />
            <span>Sync</span>
          </button>
          <button onClick={() => setIsUploadModalOpen(true)} className="btn-primary">
            <UploadCloud className="w-4 h-4 mr-1.5" />
            <span>Upload Document</span>
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="v-card p-4 flex flex-col md:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by filename or document identifier..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10"
          />
        </div>

        <div className="w-full md:w-48">
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
                <th>File Size</th>
                <th>Extraction Status</th>
                <th>Validation</th>
                <th>Uploaded</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-10">
                    <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
                    <span className="text-xs text-slate-500">Scanning repository...</span>
                  </td>
                </tr>
              ) : filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-16 px-4">
                    <div className="max-w-md mx-auto text-center space-y-3">
                      <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto shadow-sm">
                        <FileText className="w-6 h-6" />
                      </div>
                      <h3 className="text-base font-bold text-slate-900">
                        {docList.length === 0 ? 'No compliance documents cataloged yet' : 'No matching documents found'}
                      </h3>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        {docList.length === 0
                          ? 'Documents appear here automatically when suppliers email their Certificates of Analysis (CoAs) and SDS attachments, or when you upload files manually.'
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
                          <div className="text-[10px] text-slate-600 font-mono">{doc.filename}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800">
                        {doc.document_type}
                      </span>
                    </td>
                    <td>
                      <span className="text-xs text-slate-600">
                        {doc.file_size != null ? `${(doc.file_size / 1024).toFixed(1)} KB` : '—'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge text-xs ${
                        ['PROCESSED', 'EXTRACTED', 'COMPLETED'].includes(doc.extraction_status?.toUpperCase() || '')
                          ? 'badge-approved'
                          : 'badge-pending'
                      }`}>
                        {doc.extraction_status || 'UPLOADED'}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-info text-xs">{doc.validation_status || 'Not validated'}</span>
                    </td>
                    <td>
                      <span className="text-xs text-slate-600">
                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => setSelectedDoc(doc)}
                        className="btn-ghost text-xs text-blue-600 font-semibold"
                      >
                        Inspect Data
                      </button>
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
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 text-xs space-y-1">
                <p>
                  <strong className="text-slate-900">Filename:</strong> {selectedDoc.original_filename || selectedDoc.filename}
                </p>
                <p>
                  <strong className="text-slate-900">Type:</strong> {selectedDoc.document_type}
                </p>
                <p>
                  <strong className="text-slate-900">Processing Status:</strong> {selectedDoc.extraction_status || 'Not processed'}
                </p>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                  Extracted Chemical & Lot Entities
                </h4>
                {selectedDoc.extracted_data ? (
                  <pre className="p-3 bg-slate-900 text-slate-200 rounded-lg text-xs font-mono overflow-x-auto">
                    {JSON.stringify(selectedDoc.extracted_data, null, 2)}
                  </pre>
                ) : (
                  <p className="text-xs text-slate-500">No extracted fields are stored for this document.</p>
                )}
              </div>
            </div>
            <div className="px-6 py-3 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button onClick={() => setSelectedDoc(null)} className="btn-secondary text-xs">
                Close
              </button>
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
                  accept=".pdf"
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
                </select>
              </div>

              <div>
                <label className="form-label">Attach to Batch (Optional)</label>
                <select
                  value={selectedBatchId}
                  onChange={(e) => setSelectedBatchId(e.target.value)}
                  className="form-select text-xs"
                >
                  <option value="">No Batch Association (General Document)</option>
                  {batchList.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.batch_number} ({b.vendor?.name || (b.vendor as any)?.vendor_name || 'Assigned Vendor'})
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
