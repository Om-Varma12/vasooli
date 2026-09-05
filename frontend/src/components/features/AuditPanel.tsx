import React from 'react';
import { X, CheckCircle2, Activity, ShieldAlert, Zap } from 'lucide-react';
import type { RecoveryRecord } from '../../types/recovery';

interface AuditLogEntry {
  step: string;
  detail: string;
  created_at: string;
}

interface AuditPanelProps {
  recordId: string | null;
  record?: RecoveryRecord;
  promise?: any;
  onClose: () => void;
  isLoading?: boolean;
  logs: AuditLogEntry[];
}

const STEP_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  classify: {
    color: 'bg-slate-100 text-slate-600 border-slate-200',
    icon: <Activity size={12} />,
    label: 'Diagnosis',
  },
  policy: {
    color: 'bg-indigo-50 text-indigo-600 border-indigo-100',
    icon: <ShieldAlert size={12} />,
    label: 'Policy Decision',
  },
  outcome: {
    color: 'bg-green-50 text-green-600 border-green-100',
    icon: <CheckCircle2 size={12} />,
    label: 'Outcome',
  },
  default: {
    color: 'bg-orange-50 text-orange-600 border-orange-100',
    icon: <Zap size={12} />,
    label: 'Execution',
  },
};

export const AuditPanel: React.FC<AuditPanelProps> = ({ recordId, record, promise, onClose, isLoading, logs }) => {
  if (!recordId) return null;

  const formatAuditDetail = (detail: string) => {
    if (!detail) return "No details available";

    if (detail.includes("succeeded=")) {
      const isSuccess = detail.includes("succeeded=True");
      const amountMatch = detail.match(/amount_recovered_inr=([\d.]+)/);
      const amount = amountMatch ? amountMatch[1] : "0";

      return isSuccess
        ? `Payment successfully recovered. Total amount collected: ₹${parseFloat(amount).toLocaleString()}`
        : `Recovery attempt failed. No payment was collected during this step.`;
    }

    if (detail.startsWith("[")) {
      const bracketEnd = detail.indexOf("]");
      if (bracketEnd !== -1) {
        const content = detail.substring(bracketEnd + 1).trim();
        return content || detail;
      }
    }

    return detail;
  };

  const getPersonalizedReasoning = (log: AuditLogEntry) => {
    if (!record) return null;

    const amount = record.amount.replace('₹', '');
    const rootCause = record.rootCause;
    const channel = record.channel;

    if (log.step === 'policy') {
      if (channel === 'voice') {
        return `The system escalated to Voice because the customer is in a high-priority tier with a recovery amount of ₹${amount}, and the cause '${rootCause}' is most effectively resolved through direct human intervention.`;
      } else if (channel === 'whatsapp') {
        return `A WhatsApp nudge was selected as a low-friction first touch for this ${rootCause} event, adhering to the compliance-first approach for the current risk tier.`;
      } else if (channel === 'none' || record.status === 'stopped') {
        return `No further automated contact is permitted for this record due to the retry ceiling being reached or a critical risk block for the amount of ₹${amount}.`;
      }
      return `Based on the current recovery state and root cause '${rootCause}', the system applied the optimal retry interval to maximize recovery probability.`;
    }
    return null;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-6 transition-all">
      <div className="w-full max-w-4xl max-h-[90vh] bg-white shadow-2xl rounded-3xl border border-[#e5e7eb] flex flex-col animate-in zoom-in-95 duration-200 overflow-hidden">
        <div className="flex justify-between items-center p-6 border-b border-[#e5e7eb] bg-white">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-600 rounded-xl shadow-sm">
              <Activity size={24} className="text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-ink leading-tight">Recovery Audit Trail</h3>
              <p className="text-xs text-[#6b7280] font-mono mt-1 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                System Trace for Record: <span className="font-bold text-ink">{recordId}</span>
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors group">
            <X size={22} className="text-[#9ca3af] group-hover:text-ink" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-8 bg-[#fafafa]">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-96 text-sm text-[#6b7280] gap-3">
              <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="font-medium">Analyzing recovery pipeline logs...</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="flex items-center justify-center h-96 text-sm text-[#6b7280]">
              No audit logs found for this record.
            </div>
          ) : (
            <div className="relative max-w-3xl mx-auto">
              <div className="absolute left-[15px] top-2 bottom-2 w-0.5 bg-slate-200" />

              <div className="space-y-8">
                {logs.map((log, index) => {
                  const config = STEP_CONFIG[log.step] || STEP_CONFIG.default;
                  const isOutcome = log.step === 'outcome';
                  const isFailure = isOutcome && log.detail.includes('succeeded=False');

                  const finalColor = isFailure
                    ? 'bg-red-50 text-red-600 border-red-100'
                    : config.color;

                  return (
                    <div key={index} className="relative pl-10 group">
                      <div className="absolute left-0 top-1 z-10">
                        <div className={`w-8 h-8 rounded-full border-2 bg-white flex items-center justify-center transition-transform group-hover:scale-110 ${finalColor.split(' ')[1].replace('text-', 'border-')}`}>
                          {React.cloneElement(config.icon as React.ReactElement, { className: finalColor.split(' ')[1].replace('text-', 'text-') })}
                        </div>
                      </div>

                      <div className="bg-white border border-[#e5e7eb] p-5 rounded-2xl shadow-sm transition-all group-hover:border-blue-300 group-hover:shadow-md">
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex items-center gap-2">
                            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${finalColor}`}>
                              {config.label}
                            </span>
                            {log.step === 'policy' && (
                              <span className="text-[10px] text-indigo-400 font-semibold uppercase tracking-tighter">
                                Compliance Guarded
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-[#9ca3af] font-medium">
                            {new Date(log.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                          </span>
                        </div>
                        <div className="pl-1">
                          <p className="text-sm text-[#374151] leading-relaxed font-medium">
                            {formatAuditDetail(log.detail)}
                          </p>
                          {log.step === 'policy' && getPersonalizedReasoning(log) && (
                            <div className="mt-3 p-3 bg-indigo-50/50 border-l-2 border-indigo-200 rounded-r-lg">
                              <p className="text-[11px] text-indigo-700 leading-normal">
                                <span className="font-bold uppercase text-[10px] block mb-1">User-Specific Reasoning:</span>
                                {getPersonalizedReasoning(log)}
                              </p>
                            </div>
                          )}
                          {(promise && log.step.startsWith('execute:')) && (
                            <div className="mt-3 p-3 bg-green-50/50 border-l-2 border-green-200 rounded-r-lg">
                              <p className="text-[11px] text-green-700 leading-normal">
                                <span className="font-bold uppercase text-[10px] block mb-1">Payment Promise:</span>
                                Customer has promised to pay by {new Date(promise.promised_date).toLocaleDateString([], { dateStyle: 'long' })}.
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
