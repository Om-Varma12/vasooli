import React, { useState } from 'react';
import { Badge } from '../ui';
import { Play } from 'lucide-react';
import type { RecoveryRecord } from '../../types/recovery';

interface RecoveryTableRowProps {
  record: RecoveryRecord;
  onRunTest: (id: string) => Promise<void>;
}

export const RecoveryTableRow: React.FC<RecoveryTableRowProps> = ({ record, onRunTest }) => {
  const [isRunning, setIsRunning] = useState(false);

  const handleRunTest = async () => {
    setIsRunning(true);
    try {
      await onRunTest(record.id);
    } finally {
      setIsRunning(false);
    }
  };

  const statusVariant = {
    Recovered: 'recovered' as const,
    Pending: 'pending' as const,
    Unresolved: 'unresolved' as const,
    Stopped: 'stopped' as const,
  };

  return (
    <tr className="group transition-colors duration-150 bg-white hover:bg-[#f8fafc] border-b border-[#f1f3f5]">
      <td className="p-3 whitespace-nowrap">
        <span className="text-[#2563eb] font-medium cursor-pointer hover:text-blue-700 transition-colors">
          {record.id}
        </span>
      </td>
      <td className="p-3 whitespace-nowrap text-[#374151]">
        {record.customer}
      </td>
      <td className="p-3 whitespace-nowrap text-right text-[#374151] font-medium">
        {record.amount}
      </td>
      <td className="p-3 whitespace-nowrap text-[#374151]">
        {record.rootCause}
      </td>
      <td className="p-3 whitespace-nowrap text-[#374151]">
        {record.channel}
      </td>
      <td className="p-3 whitespace-nowrap text-[#374151] text-center">
        {record.retries}
      </td>
      <td className="p-3 whitespace-nowrap text-[#374151] truncate max-w-xs" title={record.message}>
        {record.message}
      </td>
      <td className="p-3 whitespace-nowrap">
        <Badge variant={statusVariant[record.status]}>
          {record.status}
        </Badge>
      </td>
      <td className="p-3 whitespace-nowrap text-center">
        {record.promiseCaptured === '✓' ? (
          <span className="text-[#16a34a] font-medium">✓</span>
        ) : (
          <span className="text-[#9ca3af]">—</span>
        )}
      </td>
      <td className="p-3 whitespace-nowrap text-center">
        <button
          onClick={handleRunTest}
          disabled={isRunning}
          className={`p-1.5 rounded-md transition-colors ${
            isRunning
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
          }`}
          title="Run pipeline test"
        >
          <Play size={14} fill="currentColor" />
        </button>
      </td>
    </tr>
  );
};
