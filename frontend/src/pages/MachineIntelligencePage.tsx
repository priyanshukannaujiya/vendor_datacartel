import React from 'react';
import { Link } from 'react-router-dom';
import {
  Cpu,
  Activity,
  AlertCircle,
  Clock,
  Sparkles,
  Zap,
  Radio,
  Sliders,
  BellRing,
  Gauge,
  Layers,
  ArrowRight,
} from 'lucide-react';

export const MachineIntelligencePage: React.FC = () => {
  const modules = [
    {
      title: 'Predictive Maintenance',
      description:
        'Continuous vibration, temperature, and rotational acoustic modeling to schedule maintenance before bearing breakdown.',
      icon: Gauge,
      metrics: ['Component Remaining Useful Life (RUL)', 'Vibration FFT Peak Analysis', 'Thermal Degradation Curve'],
      status: 'COMING SOON',
    },
    {
      title: 'Machine Health Scoring',
      description:
        'Real-time holistic vitality telemetry across bioreactors, granulators, tablet presses, and HPLC chromatography units.',
      icon: Activity,
      metrics: ['Aggregate Equipment Effectiveness (OEE)', 'Operational Health Index (0-100)', 'Duty Cycle Stress Factors'],
      status: 'COMING SOON',
    },
    {
      title: 'Anomaly Detection',
      description:
        'Unsupervised autoencoder neural networks monitoring sub-second telemetry for multivariate deviations and pressure spikes.',
      icon: Radio,
      metrics: ['Sensor Drift Residuals', 'Pressure Envelope Deviations', 'Power Transient Outliers'],
      status: 'COMING SOON',
    },
    {
      title: 'Failure Prediction Engine',
      description:
        'Early warning system estimating catastrophic shutdown probabilities and auto-generating emergency work tickets.',
      icon: Zap,
      metrics: ['Mean Time Between Failures (MTBF)', 'Failure Probability within 48h', 'Root Cause Probability Vectors'],
      status: 'COMING SOON',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="v-card p-8 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/20 border border-blue-400/30 text-blue-300 text-xs font-semibold uppercase tracking-wider mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Next-Gen Module</span>
          </div>

          <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2">
            Machine Failure Intelligence
          </h1>
          <p className="text-slate-300 text-base leading-relaxed">
            "Predict machine failures before they impact production."
          </p>

          <p className="text-xs text-slate-400 mt-4 leading-relaxed">
            Integrating IoT streaming telemetry from pharmaceutical production lines, tableting machines, and analytical laboratory instrumentation into the VendorIQ unified intelligence fabric.
          </p>
        </div>

        {/* Decorative Grid Lines */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none"></div>
      </div>

      {/* 4 Feature Modules */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {modules.map((mod, idx) => {
          const Icon = mod.icon;
          return (
            <div key={idx} className="v-card p-6 flex flex-col justify-between hover:border-slate-300 transition-all">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="badge font-bold text-xs uppercase px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200">
                    {mod.status}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900">{mod.title}</h3>
                <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">{mod.description}</p>

                <div className="mt-4 pt-4 border-t border-slate-100">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                    Target Telemetry & Indicators
                  </span>
                  <ul className="space-y-1.5">
                    {mod.metrics.map((m, i) => (
                      <li key={i} className="text-xs text-slate-700 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                        <span>{m}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] font-medium text-slate-500">
                  Machine telemetry is not available in this release.
                </span>
                <Link to="/predictions" className="btn-secondary text-xs">
                  <span>View Supplier Risk Scores</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
