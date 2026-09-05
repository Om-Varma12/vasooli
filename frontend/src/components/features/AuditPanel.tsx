import React from 'react';
import { X } from 'lucide-react';

interface AuditLogEntry {
  step: string;
  detail: string;
  created_at: string;
}

interface AuditPanelProps {
  recordId: string | null;
  onClose: () => void;
  isLoading?: boolean;
  logs: AuditLogEntry[];
}

export const AuditPanel: React.FC<AuditPanelProps> = ({ recordId, onClose, isLoading, logs }) => {
  if (!recordId) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm">
      <div className="w-full max-w-md h-full bg-white shadow-2xl border-l border-[#e5e7eb] flex flex-col animate-in slide-in-from-right duration-300">
        <div className="flex justify-between items-center p-4 border-b border-[#e5e7eb] bg-[#f8fafc]">
          <div>
            <h3 className="text-sm font-bold text-ink">Audit Trail</h3>
            <p className="text-[11px] text-[#6b7280]">Record: {recordId}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X size={18} className="text-[#6b7280]" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-sm text-[#6b7280]">
              Loading audit logs...
            </div>
          ) : logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-[#6b7280]">
              No audit logs found for this record.
            </div>
          ) : (
            <div className="relative">
              {/* Vertical Line */}
              <div className="absolute left-2 top-0 bottom-0 w-px bg-[#dfe3e8]" />

              <div className="space-y-8">
                {logs.map((log, index) => (
                  <div key={index} className="relative pl-8">
                    {/* Timeline Dot */}
                    <div className="absolute left-0 top-1.5 w-4 h-4 rounded-full bg-white border-2 border-blue-500 z-10" />

                    <div className="flex flex-col">
                      <div className="flex justify-between items-baseline mb-1">
                        <span className="text-[12px] font-bold text-ink uppercase tracking-wider">
                          {log.step}
                        </span>
                        <span className="text-[10px] text-[#9ca3af]">
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-[13px] text-[#374151] leading-relaxed">
                        {log.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
