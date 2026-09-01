import React from 'react';
import { Badge } from '../ui';
import { RecoveryRecord } from '../../types/index';

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
    <tr className="table-row border-t text-left">
      <td className="p-3 text-blue font-medium">{record.id}</td>
      <td className="p-3">{record.customer}</td>
      <td className="p-3 text-right">{record.amount}</td>
      <td className="p-3">{record.rootCause}</td>
      <td className="p-3">{record.channel}</td>
      <td className="p-3">{record.retries}</td>
      <td className="p-3 truncate max-w-xs" title={record.message}>
        {record.message}
      </td>
      <td className="p-3">
        <Badge variant={statusVariant[record.status]}>
          {record.status}
        </Badge>
      </td>
      <td className={`p-3 ${record.promiseCaptured === '✓' ? 'text-emerald-600' : ''}`}>
        {record.promiseCaptured}
      </td>
    </tr>
  );
};
