import React from 'react';
import { Badge } from '../ui';
import type { RecoveryRecord } from '../../types/recovery';

interface RecoveryTableRowProps {
  record: RecoveryRecord;
}

export const RecoveryTableRow: React.FC<RecoveryTableRowProps> = ({ record }) => {
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
    </tr>
  );
};
