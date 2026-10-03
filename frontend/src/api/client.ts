import axios, { AxiosError } from 'axios';
import {
  User,
  Vendor,
  RawMaterial,
  Batch,
  BatchDetail,
  DocumentRecord,
  MLPrediction,
  KimiIntelligence,
  DecisionRecord,
  DashboardAnalytics,
  AlertItem,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('vendoriq_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle unauthenticated 401 responses
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Don't auto-redirect if checking auth or on login page
      const url = error.config?.url || '';
      if (!url.includes('/api/auth/login') && !url.includes('/api/auth/me')) {
        localStorage.removeItem('vendoriq_token');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// Helper to safely unwrap list responses whether backend returns array or { items: [...], total: ... }
const unwrapList = <T>(data: any): T[] => {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  return [];
};

// ==================== AUTH APIS ====================
export const authApi = {
  login: async (credentials: { email: string; password: string }): Promise<{ access_token: string; token_type: string }> => {
    // Backend expects JSON LoginRequest with email + password
    const response = await apiClient.post('/api/auth/login', credentials);
    return response.data;
  },

  register: async (userData: { email: string; password: string; full_name?: string; company_name?: string }): Promise<User> => {
    const response = await apiClient.post('/api/auth/register', userData);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  },
};

// ==================== VENDOR APIS ====================
export const vendorApi = {
  getAll: async (params?: { search?: string; risk_level?: string; status?: string }): Promise<Vendor[]> => {
    const response = await apiClient.get('/api/vendors', { params });
    return unwrapList<Vendor>(response.data);
  },

  getById: async (id: string): Promise<Vendor> => {
    const response = await apiClient.get(`/api/vendors/${id}`);
    return response.data;
  },

  create: async (vendorData: Partial<Vendor>): Promise<Vendor> => {
    const response = await apiClient.post('/api/vendors', vendorData);
    return response.data;
  },

  update: async (id: string, vendorData: Partial<Vendor>): Promise<Vendor> => {
    const response = await apiClient.put(`/api/vendors/${id}`, vendorData);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/vendors/${id}`);
  },

  getHistory: async (id: string): Promise<any> => {
    const response = await apiClient.get(`/api/vendors/${id}/history`);
    return response.data;
  },

  getKimiAssessment: async (id: string): Promise<any> => {
    const response = await apiClient.get(`/api/vendors/${id}/kimi-assessment`);
    return response.data;
  },

  getEmailDirectory: async (): Promise<any[]> => {
    const response = await apiClient.get('/api/vendors/email-directory');
    return unwrapList<any>(response.data);
  },
};

// ==================== RAW MATERIAL APIS ====================
export const rawMaterialApi = {
  getAll: async (): Promise<RawMaterial[]> => {
    const response = await apiClient.get('/api/raw-materials');
    return unwrapList<RawMaterial>(response.data);
  },

  create: async (materialData: Partial<RawMaterial>): Promise<RawMaterial> => {
    const response = await apiClient.post('/api/raw-materials', materialData);
    return response.data;
  },
};

// ==================== BATCH APIS ====================
export const batchApi = {
  getAll: async (params?: { vendor_id?: string; status?: string; search?: string }): Promise<Batch[]> => {
    const response = await apiClient.get('/api/batches', { params });
    return unwrapList<Batch>(response.data);
  },

  getById: async (id: string): Promise<BatchDetail> => {
    const response = await apiClient.get(`/api/batches/${id}`);
    return response.data;
  },

  create: async (batchData: {
    batch_number: string;
    vendor_id: string;
    raw_material_id: string;
    quantity: number;
    unit?: string;
    price_per_unit?: number;
    manufacturing_date?: string;
    expiry_date?: string;
  }): Promise<Batch> => {
    const response = await apiClient.post('/api/batches', batchData);
    return response.data;
  },

  // Developer 2 workflow: Process documents & run validation
  processBatch: async (id: string): Promise<{ success: boolean; message: string; results?: any }> => {
    const response = await apiClient.post(`/api/batches/${id}/process`);
    return response.data;
  },

  // Developer 2 workflow: ML Risk Prediction
  predictRisk: async (id: string): Promise<MLPrediction> => {
    const response = await apiClient.post(`/api/batches/${id}/predict-risk`);
    return response.data;
  },

  // Developer 3 workflow: Decision Engine & SMTP Email
  makeDecision: async (id: string, options?: { manual_override?: boolean; decision?: string; notes?: string }): Promise<DecisionRecord> => {
    const response = await apiClient.post(`/api/batches/${id}/decision`, options || {});
    return response.data;
  },

  // Document upload directly attached to batch
  uploadDocument: async (batchId: string, file: File, documentType: string): Promise<DocumentRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    const response = await apiClient.post(`/api/batches/${batchId}/upload-document`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Request batch PDF documents (COA/SDS/GMP) from vendor via Google SMTP
  requestDocuments: async (batchId: string, customEmail?: string): Promise<{ success: boolean; message: string; recipient: string; email_status: string }> => {
    const response = await apiClient.post(`/api/batches/${batchId}/request-documents`, {
      custom_email: customEmail || undefined,
    });
    return response.data;
  },
};

// ==================== DOCUMENT APIS ====================
export const documentApi = {
  getAll: async (params?: { batch_id?: string; vendor_id?: string }): Promise<DocumentRecord[]> => {
    const response = await apiClient.get('/api/documents', { params });
    return unwrapList<DocumentRecord>(response.data);
  },

  upload: async (file: File, meta: { document_type: string; batch_id?: string; vendor_id?: string }): Promise<DocumentRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', meta.document_type);
    if (meta.batch_id) formData.append('batch_id', meta.batch_id);
    if (meta.vendor_id) formData.append('vendor_id', meta.vendor_id);
    const response = await apiClient.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getById: async (id: string): Promise<DocumentRecord> => {
    const response = await apiClient.get(`/api/documents/${id}`);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/documents/${id}`);
  },
};

// ==================== PREDICTION APIS ====================
export const predictionApi = {
  getAll: async (): Promise<MLPrediction[]> => {
    const response = await apiClient.get('/api/predictions');
    return unwrapList<MLPrediction>(response.data);
  },

  predictBatch: async (batchId: string): Promise<MLPrediction> => {
    const response = await apiClient.post(`/api/predictions/${batchId}`);
    return response.data;
  },
};

// ==================== ANALYTICS APIS ====================
export const analyticsApi = {
  getDashboardAnalytics: async (): Promise<DashboardAnalytics> => {
    const response = await apiClient.get('/api/analytics');
    const data = response.data || {};

    const kpis = data.kpis || {};
    const charts = data.charts || {};
    const tables = data.tables || {};

    const vendor_risk_distribution = charts.vendor_risk_distribution || data.vendor_risk_distribution || [
      { name: 'Low Risk (<25)', value: 1, color: '#10b981' },
      { name: 'Medium Risk (25-50)', value: 0, color: '#3b82f6' },
      { name: 'High Risk (50-75)', value: 0, color: '#f59e0b' },
      { name: 'Critical Risk (>75)', value: 0, color: '#ef4444' },
    ];

    const rawRiskTrend = charts.risk_trend || data.risk_trend || [];
    const risk_trend = rawRiskTrend.map((item: any) => ({
      date: item.date || item.period || '',
      avg_risk: item.avg_risk ?? item.average_risk ?? 0,
      low: item.low ?? 0,
      medium: item.medium ?? 0,
      high: item.high ?? item.high_risk_count ?? 0,
    }));

    const rawApprovalTrend = charts.batch_approval_trend || data.batch_approval_trend || [];
    const batch_approval_trend = rawApprovalTrend.map((item: any) => ({
      date: item.date || item.period || '',
      approved: item.approved ?? 0,
      rejected: item.rejected ?? 0,
      review: item.review ?? item.needs_review ?? 0,
    }));

    const rawQualityTrend = charts.quality_trend || data.quality_trend || [];
    const quality_trend = rawQualityTrend.map((item: any) => ({
      month: item.month || item.period || '',
      average_purity: item.average_purity ?? item.avg_purity ?? 99.0,
      compliance_rate: item.compliance_rate ?? 98.0,
    }));

    const high_risk_vendors_list = (tables.high_risk_vendors || data.high_risk_vendors_list || []).map((v: any) => ({
      ...v,
      name: v.name || v.vendor_name || 'Vendor',
      vendor_code: v.vendor_code || v.code || 'VND-001',
    }));

    const recent_batches_list = (tables.recent_batch_assessments || data.recent_batches_list || []).map((b: any) => ({
      ...b,
      vendor: b.vendor || { name: b.vendor_name || 'Vendor' },
    }));

    return {
      total_vendors: kpis.total_vendors ?? data.total_vendors ?? 0,
      batches_processed: kpis.batches_processed ?? data.batches_processed ?? 0,
      approved_batches: kpis.approved_batches ?? data.approved_batches ?? 0,
      rejected_batches: kpis.rejected_batches ?? data.rejected_batches ?? 0,
      high_risk_vendors: kpis.high_risk_vendors ?? data.high_risk_vendors ?? 0,
      pending_reviews: kpis.pending_reviews ?? data.pending_reviews ?? 0,
      vendor_risk_distribution,
      risk_trend,
      batch_approval_trend,
      quality_trend,
      high_risk_vendors_list,
      recent_batches_list,
    };
  },
};

// ==================== ALERTS APIS ====================
export const alertsApi = {
  getAll: async (): Promise<AlertItem[]> => {
    const response = await apiClient.get('/api/alerts');
    return unwrapList<AlertItem>(response.data);
  },

  markAsRead: async (id: string): Promise<void> => {
    await apiClient.post(`/api/alerts/${id}/read`);
  },
};

// ==================== EMAIL EVENT APIS ====================
export const emailApi = {
  getEvents: async (params?: { batch_id?: string }): Promise<any[]> => {
    const response = await apiClient.get('/api/email-events', { params });
    return unwrapList<any>(response.data);
  },

  retryEmail: async (batchId: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post(`/api/email-events/retry/${batchId}`);
    return response.data;
  },
};

// ==================== SETTINGS APIS ====================
export const settingsApi = {
  getSmtpStatus: async (): Promise<{
    is_configured: boolean;
    host: string;
    port: string;
    username_preview?: string;
    from_address?: string;
    from_name?: string;
    mode: string;
  }> => {
    const response = await apiClient.get('/api/settings/smtp');
    return response.data;
  },

  saveSmtpConfig: async (config: {
    smtp_host?: string;
    smtp_port?: number;
    smtp_username: string;
    smtp_password: string;
    smtp_from: string;
    smtp_from_name?: string;
  }): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post('/api/settings/smtp', config);
    return response.data;
  },

  testSmtp: async (data: { recipient_email: string; message?: string }): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post('/api/settings/smtp/test', data);
    return response.data;
  },
};

