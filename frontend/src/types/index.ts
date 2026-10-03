export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
export type BatchStatus = 'PENDING' | 'DOCUMENTS_RECEIVED' | 'VALIDATING' | 'ANALYZING' | 'EVALUATED' | 'APPROVED' | 'REJECTED' | 'NEEDS_REVIEW';
export type DecisionStatus = 'APPROVED' | 'REJECTED' | 'NEEDS_REVIEW' | 'PENDING';
export type EmailStatus = 'PENDING' | 'SENT' | 'FAILED' | 'RETRYING' | 'NOT_APPLICABLE';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  company_id?: string;
  is_active: boolean;
  created_at?: string;
}

export interface Vendor {
  id: string;
  name: string;
  vendor_code: string;
  contact_name?: string;
  contact_email?: string;
  phone?: string;
  address?: string;
  status: string;
  risk_score: number;
  risk_level: RiskLevel;
  approval_rate: number;
  quality_score: number;
  delivery_score: number;
  documentation_score: number;
  certifications?: string[];
  compliance_status?: string;
  total_batches: number;
  approved_batches: number;
  rejected_batches: number;
  avg_purity?: number;
  on_time_delivery_rate?: number;
  documentation_completeness_rate?: number;
  overall_risk_score?: number;
  kimi_assessment?: {
    summary?: string;
    risk_level?: string;
    recommendations?: string[];
    strengths?: string[];
    weaknesses?: string[];
  };
  created_at: string;
  updated_at?: string;
}

export interface RawMaterial {
  id: string;
  name: string;
  material_code: string;
  category?: string;
  description?: string;
  required_purity?: number;
  specifications?: Record<string, any>;
  created_at: string;
}

export interface DocumentRecord {
  id: string;
  batch_id?: string;
  vendor_id?: string;
  document_type: string;
  filename: string;
  original_filename?: string;
  file_size?: number;
  extraction_status?: string;
  validation_status?: string;
  extracted_data?: Record<string, any>;
  is_valid?: boolean;
  created_at: string;
}

export interface MLPrediction {
  batch_id?: string;
  risk_score: number;
  risk_level: RiskLevel;
  risk_probability: number;
  confidence?: number;
  top_risk_factors?: string[];
  feature_importance?: Record<string, number>;
  features_used?: Record<string, any>;
  model_version?: string;
  created_at?: string;
}

export interface KimiIntelligence {
  summary: string;
  key_findings: string[];
  risk_factors: string[];
  business_impact: string;
  recommended_actions: string[];
  raw_response?: string;
  confidence_score?: number;
}

export interface DecisionRecord {
  id: string;
  batch_id: string;
  decision: DecisionStatus;
  decision_status?: DecisionStatus;
  reasons: string[];
  conditions?: string[];
  manual_override: boolean;
  overridden_by?: string;
  override_notes?: string;
  email_status: EmailStatus;
  email_sent_at?: string;
  email_recipient?: string;
  email_subject?: string;
  retry_count: number;
  last_error?: string;
  created_at: string;
}

export interface QualityCheckItem {
  name: string;
  category: string;
  required: string | number;
  actual: string | number;
  status: 'PASSED' | 'FAILED' | 'WARNING' | 'PENDING';
  notes?: string;
}

export interface AuditTimelineEvent {
  id: string;
  step: string;
  label: string;
  status: 'COMPLETED' | 'IN_PROGRESS' | 'FAILED' | 'PENDING';
  timestamp?: string;
  description?: string;
  details?: Record<string, any>;
}

export interface Batch {
  id: string;
  batch_number: string;
  vendor_id: string;
  raw_material_id: string;
  quantity: number;
  unit: string;
  price_per_unit?: number;
  manufacturing_date?: string;
  expiry_date?: string;
  status: BatchStatus;
  validation_status?: string;
  risk_score?: number;
  risk_level?: RiskLevel;
  risk_probability?: number;
  decision?: DecisionStatus;
  decision_status?: DecisionStatus;
  processed: boolean;
  email_status: EmailStatus;
  vendor?: {
    id: string;
    name: string;
    vendor_code?: string;
    contact_email?: string;
    total_batches?: number;
    approved_batches?: number;
    rejected_batches?: number;
    approval_rate?: number;
    avg_purity?: number;
    on_time_delivery_rate?: number;
    risk_score?: number;
    risk_level?: RiskLevel;
  };
  raw_material?: {
    id: string;
    name: string;
    material_code?: string;
    required_purity?: number;
  };
  created_at: string;
  updated_at?: string;
}

export interface BatchDetail extends Batch {
  documents: DocumentRecord[];
  validation_results?: {
    is_valid: boolean;
    missing_documents?: string[];
    purity_check?: {
      required: number;
      actual: number;
      passed: boolean;
    };
    expiry_check?: {
      expiry_date: string;
      passed: boolean;
    };
    coa_verified?: boolean;
    sds_verified?: boolean;
    gmp_verified?: boolean;
    contaminants_check?: {
      detected: boolean;
      passed: boolean;
    };
    checks?: QualityCheckItem[];
  };
  historical_comparison?: {
    vendor_average_purity: number;
    batch_purity: number;
    previous_batches_count: number;
    approved_count: number;
    rejected_count: number;
    on_time_rate: number;
    variance: string;
  };
  prediction?: MLPrediction;
  kimi_intelligence?: KimiIntelligence;
  decision_record?: DecisionRecord;
  timeline?: AuditTimelineEvent[];
}

export interface DashboardAnalytics {
  total_vendors: number;
  batches_processed: number;
  approved_batches: number;
  rejected_batches: number;
  high_risk_vendors: number;
  pending_reviews: number;
  vendor_risk_distribution: {
    name: string;
    value: number;
    color: string;
  }[];
  risk_trend: {
    date: string;
    avg_risk: number;
    low: number;
    medium: number;
    high: number;
  }[];
  batch_approval_trend: {
    date: string;
    approved: number;
    rejected: number;
    review: number;
  }[];
  quality_trend: {
    month: string;
    average_purity: number;
    compliance_rate: number;
  }[];
  high_risk_vendors_list: Vendor[];
  recent_batches_list: Batch[];
}

export interface AlertItem {
  id: string;
  title: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  batch_id?: string;
  vendor_id?: string;
  created_at: string;
  read: boolean;
}
