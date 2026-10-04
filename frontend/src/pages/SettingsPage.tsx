import React, { useState, useEffect } from 'react';
import {
  Settings,
  Server,
  Database,
  Sparkles,
  Mail,
  Shield,
  CheckCircle2,
  Key,
  Globe,
  RefreshCw,
  Building,
  Send,
  Lock,
  AlertCircle,
  HelpCircle,
  User as UserIcon,
  Save,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { settingsApi, authApi } from '../api/client';

export const SettingsPage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState<'smtp' | 'profile' | 'organization' | 'integrations'>('smtp');

  // SMTP Configuration State
  const [smtpForm, setSmtpForm] = useState({
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    smtp_from: '',
    smtp_from_name: 'VendorIQ Quality Operations',
  });

  const [smtpStatus, setSmtpStatus] = useState<any>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Test Email State
  const [testRecipient, setTestRecipient] = useState('');
  const [isTesting, setIsTesting] = useState(false);
  const [testSuccessMessage, setTestSuccessMessage] = useState<string | null>(null);
  const [testErrorMessage, setTestErrorMessage] = useState<string | null>(null);

  // User Profile State
  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Organization State
  const [companyForm, setCompanyForm] = useState({
    name: user?.company_name || '',
    industry: 'Cosmeceuticals & Skincare Manufacturing',
  });
  const [companySaving, setCompanySaving] = useState(false);
  const [companySuccess, setCompanySuccess] = useState<string | null>(null);
  const [companyError, setCompanyError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setProfileForm((prev) => ({
        ...prev,
        full_name: user.full_name || '',
        email: user.email || '',
      }));
      setCompanyForm((prev) => ({
        ...prev,
        name: user.company_name || prev.name,
      }));
    }
  }, [user]);

  const loadSmtpStatus = async () => {
    try {
      setIsLoadingStatus(true);
      const res = await settingsApi.getSmtpStatus();
      setSmtpStatus(res);
      if (res.from_address) {
        setSmtpForm((prev) => ({
          ...prev,
          smtp_from: res.from_address || '',
          smtp_from_name: res.from_name || 'VendorIQ Quality Operations',
          smtp_host: res.host || 'smtp.gmail.com',
          smtp_port: parseInt(res.port, 10) || 587,
        }));
      }
    } catch (err) {
      console.warn('Could not load SMTP status:', err);
    } finally {
      setIsLoadingStatus(false);
    }
  };

  useEffect(() => {
    loadSmtpStatus();
  }, []);

  const handleSaveSmtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccessMessage(null);
    setSaveErrorMessage(null);
    setIsSaving(true);
    try {
      const res = await settingsApi.saveSmtpConfig(smtpForm);
      setSaveSuccessMessage(res.message || 'Google SMTP credentials successfully saved & activated!');
      await loadSmtpStatus();
      setTimeout(() => setSaveSuccessMessage(null), 6000);
    } catch (err: any) {
      setSaveErrorMessage(err.response?.data?.detail || err.message || 'Failed to save SMTP configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSendTestEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testRecipient) return;
    setTestSuccessMessage(null);
    setTestErrorMessage(null);
    setIsTesting(true);
    try {
      const res = await settingsApi.testSmtp({
        recipient_email: testRecipient,
        message: 'This confirms your Google SMTP connection is operational for VendorIQ document requests.',
      });
      setTestSuccessMessage(res.message || `Test email dispatched to ${testRecipient}!`);
      setTimeout(() => setTestSuccessMessage(null), 6000);
    } catch (err: any) {
      setTestErrorMessage(
        err.response?.data?.detail || err.message || 'Failed to send test email. Please check your credentials.'
      );
    } finally {
      setIsTesting(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileSuccess(null);
    setProfileError(null);

    if (profileForm.new_password) {
      if (!profileForm.current_password) {
        setProfileError('Current password is required to set a new password.');
        return;
      }
      if (profileForm.new_password.length < 8) {
        setProfileError('New password must be at least 8 characters long.');
        return;
      }
      if (profileForm.new_password !== profileForm.confirm_password) {
        setProfileError('New passwords do not match.');
        return;
      }
    }

    setProfileSaving(true);
    try {
      const payload: any = {
        full_name: profileForm.full_name,
        email: profileForm.email,
      };
      if (profileForm.new_password) {
        payload.current_password = profileForm.current_password;
        payload.new_password = profileForm.new_password;
      }

      const res = await authApi.updateProfile(payload);
      setProfileSuccess('Profile credentials successfully updated!');
      await refreshUser();
      setProfileForm((prev) => ({
        ...prev,
        current_password: '',
        new_password: '',
        confirm_password: '',
      }));
      setTimeout(() => setProfileSuccess(null), 5000);
    } catch (err: any) {
      setProfileError(err.response?.data?.detail || err.message || 'Failed to update profile.');
    } finally {
      setProfileSaving(false);
    }
  };

  const handleUpdateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setCompanySuccess(null);
    setCompanyError(null);
    setCompanySaving(true);
    try {
      const res = await authApi.updateCompany({
        name: companyForm.name,
        industry: companyForm.industry,
      });
      setCompanySuccess(res.message || 'Organization settings successfully saved!');
      await refreshUser();
      setTimeout(() => setCompanySuccess(null), 5000);
    } catch (err: any) {
      setCompanyError(err.response?.data?.detail || err.message || 'Failed to update organization.');
    } finally {
      setCompanySaving(false);
    }
  };

  const integrations = [
    {
      name: 'Unified FastAPI Backend',
      provider: 'Render Web Service',
      status: 'CONNECTED',
      desc: 'Single unified backend instance running uvicorn app.main:app',
      icon: Server,
    },
    {
      name: 'PostgreSQL Relational DB',
      provider: 'Neon Serverless',
      status: 'ACTIVE',
      desc: 'Production ACID database with Alembic migration integrity',
      icon: Database,
    },
    {
      name: 'Kimi K3 AI Model',
      provider: 'Moonshot AI API',
      status: 'CONFIGURED',
      desc: 'Contextual scientific synthesis & risk justification reasoning',
      icon: Sparkles,
    },
    {
      name: 'Notification Delivery',
      provider: 'Google SMTP (Gmail)',
      status: smtpStatus?.is_configured ? 'VERIFIED' : 'PENDING CONFIG',
      desc: 'Automated STARTTLS lot qualification & document request delivery',
      icon: Mail,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">System & Account Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage Google SMTP email delivery, your user account credentials, organization profile, and integrations.
        </p>
      </div>

      {/* Settings Tab Navigation */}
      <div className="flex border-b border-slate-200 gap-2">
        <button
          onClick={() => setActiveTab('smtp')}
          className={`py-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'smtp'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Mail className="w-4 h-4" />
          <span>Google SMTP & Email Intake</span>
        </button>
        <button
          onClick={() => setActiveTab('profile')}
          className={`py-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'profile'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <UserIcon className="w-4 h-4" />
          <span>User Profile & Security</span>
        </button>
        <button
          onClick={() => setActiveTab('organization')}
          className={`py-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'organization'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Building className="w-4 h-4" />
          <span>Company & Organization</span>
        </button>
        <button
          onClick={() => setActiveTab('integrations')}
          className={`py-3 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'integrations'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Globe className="w-4 h-4" />
          <span>Platform Infrastructure</span>
        </button>
      </div>

      {/* TAB 1: Google SMTP Credentials Card */}
      {activeTab === 'smtp' && (
        <div className="v-card p-6 border-blue-200/90 bg-gradient-to-br from-white via-white to-blue-50/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
                <Mail className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Google SMTP (Gmail) Configuration</h3>
                <p className="text-xs text-slate-500">
                  Send real document requests and batch qualification results directly to vendor emails.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {smtpStatus?.is_configured ? (
                <span className="badge badge-approved text-xs font-bold py-1 px-3">
                  <CheckCircle2 className="w-3.5 h-3.5" /> SMTP ACTIVE
                </span>
              ) : (
                <span className="badge badge-needs-review text-xs font-bold py-1 px-3">
                  AWAITING CREDENTIALS
                </span>
              )}
            </div>
          </div>

          {saveSuccessMessage && (
            <div className="mb-4 p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{saveSuccessMessage}</span>
            </div>
          )}

          {saveErrorMessage && (
            <div className="mb-4 p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{saveErrorMessage}</span>
            </div>
          )}

          {/* Configuration Form */}
          <form onSubmit={handleSaveSmtp} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="form-label">Gmail / Google Workspace Address *</label>
                <input
                  type="email"
                  required
                  value={smtpForm.smtp_username}
                  onChange={(e) => {
                    setSmtpForm({
                      ...smtpForm,
                      smtp_username: e.target.value,
                      smtp_from: smtpForm.smtp_from || e.target.value,
                    });
                  }}
                  placeholder="your.company.quality@gmail.com"
                  className="form-input"
                />
                <span className="text-[11px] text-slate-600 mt-1 block">
                  {smtpStatus?.username_preview
                    ? `Active account: ${smtpStatus.username_preview}`
                    : 'Your Google email account used for dispatching.'}
                </span>
              </div>

              <div>
                <label className="form-label">Google 16-Character App Password *</label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="password"
                    required
                    value={smtpForm.smtp_password}
                    onChange={(e) => setSmtpForm({ ...smtpForm, smtp_password: e.target.value })}
                    placeholder="xxxx xxxx xxxx xxxx"
                    className="form-input pl-10 font-mono tracking-wider"
                  />
                </div>
                <span className="text-[11px] text-slate-600 mt-1 block">
                  Must be an App Password generated under your Google Account security settings.
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="form-label">From Address (Reply-To) *</label>
                <input
                  type="email"
                  required
                  value={smtpForm.smtp_from}
                  onChange={(e) => setSmtpForm({ ...smtpForm, smtp_from: e.target.value })}
                  placeholder="quality@vendoriq.com"
                  className="form-input"
                />
              </div>

              <div>
                <label className="form-label">From Sender Name</label>
                <input
                  type="text"
                  value={smtpForm.smtp_from_name}
                  onChange={(e) => setSmtpForm({ ...smtpForm, smtp_from_name: e.target.value })}
                  placeholder="VendorIQ Quality Assurance"
                  className="form-input"
                />
              </div>

              <div>
                <label className="form-label">Host & Port (STARTTLS)</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={smtpForm.smtp_host}
                    onChange={(e) => setSmtpForm({ ...smtpForm, smtp_host: e.target.value })}
                    className="form-input font-mono text-xs"
                  />
                  <input
                    type="number"
                    value={smtpForm.smtp_port}
                    onChange={(e) => setSmtpForm({ ...smtpForm, smtp_port: parseInt(e.target.value, 10) || 587 })}
                    className="form-input font-mono text-xs"
                  />
                </div>
              </div>
            </div>

            {/* Quick Helper Box */}
            <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200/80 text-xs text-blue-900 flex items-start gap-2.5">
              <HelpCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold">How to create a Google App Password:</strong>
                <p className="mt-0.5 text-blue-800">
                  1. Go to <a href="https://myaccount.google.com/security" target="_blank" rel="noreferrer" className="underline font-semibold">myaccount.google.com/security</a>.<br />
                  2. Under <em>2-Step Verification</em>, scroll down to <strong>App Passwords</strong>.<br />
                  3. Name it "VendorIQ" and click <strong>Create</strong>.<br />
                  4. Paste the 16-character code into the field above and click <strong>Save SMTP Credentials</strong>.
                </p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="submit"
                disabled={isSaving || !smtpForm.smtp_username || !smtpForm.smtp_password}
                className="btn-primary"
              >
                {isSaving ? 'Authenticating & Saving...' : 'Save Google SMTP Credentials'}
              </button>
            </div>
          </form>

          {/* Live Test Section */}
          <div className="mt-6 pt-6 border-t border-slate-100">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-3 flex items-center gap-1.5">
              <Send className="w-3.5 h-3.5 text-blue-600" />
              Send Live Verification Test Email
            </h4>

            {testSuccessMessage && (
              <div className="mb-3 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{testSuccessMessage}</span>
              </div>
            )}

            {testErrorMessage && (
              <div className="mb-3 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{testErrorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSendTestEmail} className="flex flex-col sm:flex-row items-center gap-3">
              <input
                type="email"
                required
                placeholder="Enter your personal or vendor email to test..."
                value={testRecipient}
                onChange={(e) => setTestRecipient(e.target.value)}
                className="form-input flex-1"
              />
              <button
                type="submit"
                disabled={isTesting || !testRecipient}
                className="btn-secondary whitespace-nowrap w-full sm:w-auto text-xs"
              >
                <Send className="w-3.5 h-3.5 mr-1" />
                {isTesting ? 'Dispatching...' : 'Send Test Email'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: User Account & Security */}
      {activeTab === 'profile' && (
        <div className="v-card p-6 space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <UserIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">User Account & Security</h3>
              <p className="text-xs text-slate-500">Update your name, email address, or update your password.</p>
            </div>
          </div>

          {profileSuccess && (
            <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{profileSuccess}</span>
            </div>
          )}

          {profileError && (
            <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{profileError}</span>
            </div>
          )}

          <form onSubmit={handleUpdateProfile} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="form-label">Full Name *</label>
                <input
                  type="text"
                  required
                  value={profileForm.full_name}
                  onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                  className="form-input"
                />
              </div>

              <div>
                <label className="form-label">Email Address *</label>
                <input
                  type="email"
                  required
                  value={profileForm.email}
                  onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                  className="form-input"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-3 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-indigo-600" />
                Change Password (Leave blank to keep current password)
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="form-label">Current Password</label>
                  <input
                    type="password"
                    value={profileForm.current_password}
                    onChange={(e) => setProfileForm({ ...profileForm, current_password: e.target.value })}
                    placeholder="••••••••"
                    className="form-input"
                  />
                </div>

                <div>
                  <label className="form-label">New Password</label>
                  <input
                    type="password"
                    value={profileForm.new_password}
                    onChange={(e) => setProfileForm({ ...profileForm, new_password: e.target.value })}
                    placeholder="Min. 8 characters"
                    className="form-input"
                  />
                </div>

                <div>
                  <label className="form-label">Confirm New Password</label>
                  <input
                    type="password"
                    value={profileForm.confirm_password}
                    onChange={(e) => setProfileForm({ ...profileForm, confirm_password: e.target.value })}
                    placeholder="••••••••"
                    className="form-input"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end pt-2">
              <button
                type="submit"
                disabled={profileSaving}
                className="btn-primary flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                <span>{profileSaving ? 'Saving Changes...' : 'Save Profile Changes'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 3: Company & Organization */}
      {activeTab === 'organization' && (
        <div className="v-card p-6 space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Organization & Tenant Profile</h3>
              <p className="text-xs text-slate-500">Configure your company identity and industry vertical.</p>
            </div>
          </div>

          {companySuccess && (
            <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{companySuccess}</span>
            </div>
          )}

          {companyError && (
            <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{companyError}</span>
            </div>
          )}

          <form onSubmit={handleUpdateCompany} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="form-label">Company / Organization Name *</label>
                <input
                  type="text"
                  required
                  value={companyForm.name}
                  onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                  placeholder="e.g. Lumina Derma Labs"
                  className="form-input"
                />
              </div>

              <div>
                <label className="form-label">Primary Industry Vertical *</label>
                <input
                  type="text"
                  required
                  value={companyForm.industry}
                  onChange={(e) => setCompanyForm({ ...companyForm, industry: e.target.value })}
                  placeholder="e.g. Cosmeceuticals & Skincare Manufacturing"
                  className="form-input"
                />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
              <strong>Multi-Tenant Data Isolation:</strong> All vendor intelligence, document records, and raw material qualification pipelines are strictly isolated to your company ID.
            </div>

            <div className="flex items-center justify-end pt-2">
              <button
                type="submit"
                disabled={companySaving}
                className="btn-primary flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                <span>{companySaving ? 'Updating...' : 'Save Organization Settings'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 4: Production Infrastructure Integrations */}
      {activeTab === 'integrations' && (
        <div className="v-card p-6">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Globe className="w-4 h-4 text-blue-600" />
            Infrastructure Integrations
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {integrations.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div key={idx} className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-100/70 text-blue-700 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900">{item.name}</span>
                      <span className="badge badge-approved text-[10px] font-bold">
                        <CheckCircle2 className="w-3 h-3" /> {item.status}
                      </span>
                    </div>
                    <span className="text-[11px] font-semibold text-blue-600 block mt-0.5">
                      {item.provider}
                    </span>
                    <p className="text-[11px] text-slate-500 mt-1 leading-snug">{item.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
