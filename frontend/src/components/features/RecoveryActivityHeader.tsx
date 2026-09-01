import React from 'react';

interface RecoveryActivityHeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const RecoveryActivityHeader: React.FC<RecoveryActivityHeaderProps> = ({
  activeTab,
  setActiveTab,
}) => {
  const tabs = ['All', 'Retried', 'WhatsApp Sent', 'Voice Escalated', 'Recovered', 'Unresolved'];

  return (
    <div className="flex justify-between items-end mb-2">
      <div>
        <h1 className="text-lg font-bold">
          Vasooli — Recovery Activity
        </h1>
        <div className="flex gap-6 mt-3">
          {tabs.map((tab) => (
            <span
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`tab cursor-pointer pb-2 transition-all duration-150 ${
                activeTab === tab
                  ? 'text-blue font-semibold border-b-2 border-blue'
                  : 'text-slate-600 hover:text-blue'
              }`}
            >
              {tab}
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-5 text-blue text-[13px]">
        <a href="#" className="hover:underline">Audit Log</a>
        <a href="#" className="hover:underline">Config Rules</a>
        <a href="#" className="hover:underline">Documentation ↗</a>
        <button className="bg-blue hover:bg-blue-900 text-white rounded px-4 py-2 font-semibold transition-colors">
          + Configure Rules
        </button>
      </div>
    </div>
  );
};
