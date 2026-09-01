import React from 'react';
import type { RecoveryRecord } from '../../types/recovery';
import { RecoveryTableRow } from './RecoveryTableRow';
import { Search } from 'lucide-react';

interface RecoveryTableProps {
  data: RecoveryRecord[];
}

export const RecoveryTable: React.FC<RecoveryTableProps> = ({ data }) => {
  return (
    <section className="bg-white border border-[#e5e7eb] rounded-xl overflow-hidden shadow-sm">
      <div className="flex justify-between items-center p-4 h-[60px] border-b border-[#e5e7eb] bg-white">
        <div className="flex gap-2">
          {['Root Cause: All', 'Channel: All', 'Duration: 24/08 - 31/08'].map((filter) => (
            <button
              key={filter}
              className="px-3 py-1.5 bg-white border border-[#dfe3e8] rounded-md text-[12px] text-[#374151] hover:bg-[#f8fafc] transition-colors"
            >
              {filter}⌄
            </button>
          ))}
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9ca3af]" />
          <input
            type="text"
            placeholder="Search by Customer ID or Record ID"
            className="pl-9 pr-3 py-2 w-[280px] h-10 border border-[#dfe3e8] rounded-lg text-[13px] placeholder:text-[#9ca3af] focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
          />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px] table-fixed border-collapse">
          <thead className="bg-[#f8fafc] text-left">
            <tr className="h-[44px]">
              <th className="p-3 w-[150px] text-[#6b7280] font-medium border-b border-[#e5e7eb]">Record ID</th>
              <th className="p-3 w-[110px] text-[#6b7280] font-medium border-b border-[#e5e7eb]">Customer</th>
              <th className="p-3 w-[90px] text-right text-[#6b7280] font-medium border-b border-[#e5e7eb]">Amount</th>
              <th className="p-3 w-[130px] text-[#6b7280] font-medium border-b border-[#e5e7eb]">Root Cause</th>
              <th className="p-3 w-[100px] text-[#6b7280] font-medium border-b border-[#e5e7eb]">Channel</th>
              <th className="p-3 w-[70px] text-center text-[#6b7280] font-medium border-b border-[#e5e7eb]">Retries</th>
              <th className="p-3 w-[250px] text-[#6b7280] font-medium border-b border-[#e5e7eb]">Message/Call Sent</th>
              <th className="p-3 w-[110px] text-[#6b7280] font-medium border-b border-[#e5e7eb]">Status</th>
              <th className="p-3 w-[120px] text-center text-[#6b7280] font-medium border-b border-[#e5e7eb]">Promise Captured</th>
            </tr>
          </thead>
          <tbody>
            {data.map((record) => (
              <RecoveryTableRow key={record.id} record={record} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-center text-[#6b7280] text-[12px] py-4 bg-white">
        Showing 1–{data.length}
      </div>
    </section>
  );
};
