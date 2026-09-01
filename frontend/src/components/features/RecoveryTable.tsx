import React from 'react';
import { RecoveryRecord } from '../../types';
import { RecoveryTableRow } from './RecoveryTableRow';
import { Search } from 'lucide-react';

interface RecoveryTableProps {
  data: RecoveryRecord[];
}

export const RecoveryTable: React.FC<RecoveryTableProps> = ({ data }) => {
  return (
    <section className="bg-white border border-line rounded-lg overflow-hidden">
      <div className="flex justify-between items-center p-3 border-b">
        <div className="flex gap-2">
          <button className="border rounded-full px-3 py-1 text-xs hover:bg-slate-50">
            Root Cause: All⌄
          </button>
          <button className="border rounded-full px-3 py-1 text-xs hover:bg-slate-50">
            Channel: All⌄
          </button>
          <button className="border rounded-full px-3 py-1 text-xs hover:bg-slate-50">
            Duration: 24/08/2026 - 31/08/2026⌄
          </button>
          <button className="text-slate-500 px-1 hover:text-black">×</button>
        </div>
        <div className="border rounded px-3 py-2 w-72 text-slate-400 text-xs flex gap-2 items-center bg-white">
          <Search size={14} />
          <span>Search by Customer ID or Record ID</span>
        </div>
      </div>
      <div className="scroll overflow-auto">
        <table className="w-full text-[13px] table-fixed">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-3 w-36">Record ID</th>
              <th className="p-3 w-24">Customer</th>
              <th className="p-3 w-24 text-right">Amount</th>
              <th className="p-3 w-32">Root Cause</th>
              <th className="p-3 w-28">Channel</th>
              <th className="p-3 w-16">Retries</th>
              <th className="p-3 w-64">Message/Call Sent</th>
              <th className="p-3 w-24">Status</th>
              <th className="p-3">Promise Captured</th>
            </tr>
          </thead>
          <tbody>
            {data.map((record) => (
              <RecoveryTableRow key={record.id} record={record} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-center text-muted text-xs py-4">
        Showing 1–{data.length}
      </div>
    </section>
  );
};
