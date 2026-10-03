import axios, { AxiosError } from 'axios';
import {
  User,
  Vendor,
  RawMaterial,
  Batch,
  BatchDetail,
  DocumentRecord,
  MLPrediction,
  RiskLevel,
  KimiIntelligence,
  DecisionRecord,
  DashboardAnalytics,
  AlertItem,
} from '../types';

const rawBaseUrl =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000';

const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

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
  throw new TypeError('The API returned an unexpected list response.');
};

const riskLevelFromScore = (score?: number): RiskLevel => {
  if (score === undefined || score === null) return 'UNKNOWN';
  if (score < 25) return 'LOW';
  if (score < 50) return 'MEDIUM';
  if (score < 75) return 'HIGH';
  return 'CRITICAL';
};

const normalizeVendor = (source: any): Vendor => {
  const score = source.risk_score ?? source.overall_risk_score;
  const approvalRate = source.approval_rate;
  const deliveryRate = source.delivery_reliability ?? source.on_time_delivery_rate;
  return {
    ...source,
    name: source.name || source.vendor_name || '',
    vendor_code: source.vendor_code || source.code || source.company_registration_id || '',
    contact_email: source.contact_email || source.email || '',
    risk_level: source.risk_level || riskLevelFromScore(score),
    approval_rate: approvalRate == null ? undefined : approvalRate <= 1 ? approvalRate * 100 : approvalRate,
    delivery_score: deliveryRate == null ? undefined : deliveryRate <= 1 ? deliveryRate * 100 : deliveryRate,
    quality_score: source.quality_score ?? source.quality_consistency,
    total_batches: source.total_batches ?? source.health?.total_batches ?? 0,
    approved_batches: source.approved_batches ?? source.health?.approved_batches ?? 0,
    rejected_batches: source.rejected_batches ?? source.health?.rejected_batches ?? 0,
    kimi_assessment: source.kimi_assessment
      ? {
          ...source.kimi_assessment,
          recommendations:
            source.kimi_assessment.recommendations ||
            source.kimi_assessment.recommended_actions ||
            [],
        }
      : undefined,
  } as Vendor;
};

const normalizeMaterial = (source: any): RawMaterial => ({
  ...source,
  material_code: source.material_code || source.code || '',
  required_purity: source.required_purity ?? source.purity_min,
  specifications: source.specifications || source.specification || {},
});

const normalizeDocument = (source: any): DocumentRecord => ({
  ...source,
  filename: source.filename || source.file_name || '',
  original_filename: source.original_filename || source.file_name || source.filename || '',
  extraction_status: source.extraction_status || source.processing_status || source.status,
  created_at: source.created_at || source.uploaded_at || source.upload_date || '',
});

const normalizeBatch = (source: any): Batch => {
  const decision = source.decision || source.final_decision?.decision;
  const score = source.risk_score ?? source.risk_prediction?.risk_score;
  return {
    ...source,
    price_per_unit: source.price_per_unit ?? source.price,
    decision,
    decision_status: decision,
    risk_score: score,
    risk_probability: source.risk_probability ?? source.risk_prediction?.risk_probability,
    risk_level: source.risk_level || source.risk_prediction?.risk_level || riskLevelFromScore(score),
    processed: source.processed ?? Boolean(source.risk_prediction || source.quality_checks?.all_checks?.length),
    vendor:
      source.vendor ||
      (source.vendor_name
        ? {
            id: source.vendor_id,
            name: source.vendor_name,
            vendor_code: source.vendor_code,
            contact_email: source.vendor_email,
          }
        : undefined),
    raw_material:
      source.raw_material ||
      (source.raw_material_name
        ? {
            id: source.raw_material_id,
            name: source.raw_material_name,
            required_purity:
              source.material_required_purity ??
              source.quality_checks?.specification?.purity_min,
          }
        : undefined),
  } as Batch;
};

const normalizeBatchDetail = (source: any): BatchDetail => {
  const batch = normalizeBatch(source);
  const checks = source.quality_checks?.all_checks || [];
  const kimi = source.kimi_analysis;
  const emailEvent = source.email_event;
  const finalDecision = source.final_decision;
  const riskPrediction = source.risk_prediction;
  const decisionAudit = (source.audit_timeline || []).find(
    (event: any) => event.event_type === 'Decision Made'
  );
  const historical = source.historical_comparison || {};
  return {
    ...batch,
    documents: (source.documents || []).map(normalizeDocument),
    validation_results: {
      is_valid: checks.length > 0 && checks.every((check: any) => check.status === 'PASS'),
      checks: checks.map((check: any) => ({
        name: check.name || 'Validation check',
        category: (check.name || 'validation').split('_')[0],
        required: check.expected ?? 'Configured requirement',
        actual: check.actual ?? 'Not provided',
        status:
          check.status === 'PASS'
            ? 'PASSED'
            : check.status === 'FAIL'
              ? 'FAILED'
              : check.status === 'NEEDS_REVIEW' || check.status === 'MISSING'
                ? 'WARNING'
                : 'PENDING',
        notes: check.reason,
      })),
    },
    prediction: riskPrediction
      ? {
          ...riskPrediction,
          batch_id: String(source.id),
        }
      : undefined,
    historical_comparison: {
      previous_batches_count: historical.previous_batches,
      approved_count: historical.approved_count,
      rejected_count: historical.rejected_count,
      vendor_average_purity: historical.average_purity,
      on_time_rate:
        historical.delivery_reliability == null
          ? undefined
          : historical.delivery_reliability <= 1
            ? historical.delivery_reliability * 100
            : historical.delivery_reliability,
      variance:
        historical.purity_variance == null
          ? undefined
          : `${historical.purity_variance > 0 ? '+' : ''}${historical.purity_variance}%`,
    },
    kimi_intelligence: kimi
      ? {
          ...kimi,
          business_impact: Array.isArray(kimi.business_impact)
            ? kimi.business_impact.join(' ')
            : kimi.business_impact,
        }
      : undefined,
    decision_record: finalDecision
      ? {
          ...finalDecision,
          batch_id: String(source.id),
          decision_status: finalDecision.decision,
          reasons: finalDecision.reason ? [finalDecision.reason] : [],
          manual_override: Boolean(decisionAudit?.details?.manual_override),
          override_notes: decisionAudit?.details?.override_notes,
          email_status: emailEvent?.status || source.email_status || 'NOT_APPLICABLE',
          email_sent_at: emailEvent?.sent_at,
          email_recipient: emailEvent?.recipient_email,
          email_subject: emailEvent?.subject,
          retry_count: 0,
          last_error: emailEvent?.error_message,
        }
      : undefined,
    email_event: emailEvent,
    email_status: emailEvent?.status || source.email_status || 'NOT_APPLICABLE',
    timeline: (source.audit_timeline || []).map((event: any, index: number) => ({
      id: event.id || `${event.event_type}-${index}`,
      step: event.event_type,
      label: event.event_type,
      status: 'COMPLETED',
      timestamp: event.timestamp,
      details: event.details,
    })),
  } as BatchDetail;
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
    const payload = response.data?.user || response.data;
    return {
      ...payload,
      company_id: payload.company_id || response.data?.company?.id,
      company_name: payload.company_name || response.data?.company?.name,
    };
  },
};

// ==================== VENDOR APIS ====================
export const vendorApi = {
  getAll: async (params?: { search?: string; risk_level?: string; status?: string }): Promise<Vendor[]> => {
    const response = await apiClient.get('/api/vendors', { params });
    return unwrapList<any>(response.data).map(normalizeVendor);
  },

  getById: async (id: string): Promise<Vendor> => {
    const response = await apiClient.get(`/api/vendors/${id}`);
    return normalizeVendor(response.data);
  },

  create: async (vendorData: Partial<Vendor>): Promise<Vendor> => {
    const response = await apiClient.post('/api/vendors', {
      vendor_name: vendorData.name || (vendorData as any).vendor_name,
      company_registration_id:
        vendorData.vendor_code || (vendorData as any).company_registration_id,
      contact_name: vendorData.contact_name,
      email: vendorData.contact_email || (vendorData as any).email,
      phone: vendorData.phone,
      address: vendorData.address,
      industry: (vendorData as any).industry,
      status: vendorData.status,
    });
    return normalizeVendor(response.data);
  },

  update: async (id: string, vendorData: Partial<Vendor>): Promise<Vendor> => {
    const response = await apiClient.put(`/api/vendors/${id}`, {
      vendor_name: vendorData.name,
      company_registration_id: vendorData.vendor_code,
      contact_name: vendorData.contact_name,
      email: vendorData.contact_email,
      phone: vendorData.phone,
      address: vendorData.address,
      status: vendorData.status,
    });
    return normalizeVendor(response.data);
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
    return unwrapList<any>(response.data).map(normalizeMaterial);
  },

  create: async (materialData: Partial<RawMaterial>): Promise<RawMaterial> => {
    const response = await apiClient.post('/api/raw-materials', {
      ...materialData,
      code: materialData.material_code || (materialData as any).code,
      purity_min: materialData.required_purity ?? (materialData as any).purity_min,
    });
    return normalizeMaterial(response.data);
  },
};

// ==================== BATCH APIS ====================
export const batchApi = {
  getAll: async (params?: { vendor_id?: string; status?: string; search?: string }): Promise<Batch[]> => {
    const response = await apiClient.get('/api/batches', { params });
    return unwrapList<any>(response.data).map(normalizeBatch);
  },

  getById: async (id: string): Promise<BatchDetail> => {
    const response = await apiClient.get(`/api/batches/${id}`);
    return normalizeBatchDetail(response.data);
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
    const response = await apiClient.post('/api/batches', {
      ...batchData,
      price: batchData.price_per_unit,
    });
    return normalizeBatch(response.data);
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
  makeDecision: async (
    id: string,
    options?: {
      manual_override?: boolean;
      decision?: string;
      notes?: string;
      company_thresholds?: Record<string, unknown>;
    }
  ): Promise<DecisionRecord> => {
    const response = await apiClient.post(`/api/batches/${id}/decision`, options || {});
    return response.data;
  },

  // Document upload directly attached to batch
  uploadDocument: async (batchId: string, file: File, documentType: string): Promise<DocumentRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(
      `/api/batches/${batchId}/upload-document`,
      formData,
      {
        params: { document_type: documentType },
      }
    );
    return normalizeDocument(response.data);
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
    return unwrapList<any>(response.data).map(normalizeDocument);
  },

  upload: async (file: File, meta: { document_type: string; batch_id?: string; vendor_id?: string }): Promise<DocumentRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/api/documents', formData, {
      params: {
        document_type: meta.document_type,
        batch_id: meta.batch_id,
        vendor_id: meta.vendor_id,
      },
    });
    return normalizeDocument(response.data);
  },

  getById: async (id: string): Promise<DocumentRecord> => {
    const response = await apiClient.get(`/api/documents/${id}`);
    return normalizeDocument(response.data);
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/documents/${id}`);
  },
};

// ==================== PREDICTION APIS ====================
export const predictionApi = {
  getAll: async (): Promise<MLPrediction[]> => {
    const response = await apiClient.get('/api/predictions');
    return unwrapList<any>(response.data).map((item) => ({
      ...item,
      batch_id: item.batch_id,
      batch_status: item.batch_status || 'UNKNOWN',
      risk_factors: item.risk_factors || [],
      top_risk_factors: item.risk_factors || [],
    }));
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
    const data = response.data;

    const kpis = data.kpis || {};
    const charts = data.charts || {};
    const tables = data.tables || {};

    const vendor_risk_distribution =
      charts.vendor_risk_distribution || data.vendor_risk_distribution || [];

    const rawRiskTrend = charts.risk_trend || data.risk_trend || [];
    const risk_trend = rawRiskTrend.map((item: any) => ({
      date: item.date || item.period || '',
      avg_risk: item.avg_risk ?? item.average_risk ?? null,
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
      average_purity: item.average_purity ?? item.avg_purity ?? null,
      compliance_rate: item.compliance_rate ?? null,
    }));

    const high_risk_vendors_list = (tables.high_risk_vendors || data.high_risk_vendors_list || []).map(normalizeVendor);

    const recent_batches_list = (tables.recent_batch_assessments || data.recent_batches_list || []).map(normalizeBatch);

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

  retryEmail: async (eventId: string): Promise<{ id: string; status: string; error_message?: string }> => {
    const response = await apiClient.post(`/api/email-events/${eventId}/retry`);
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
