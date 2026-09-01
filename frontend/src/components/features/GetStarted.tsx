import React from 'react';

interface GetStartedProps {
  onClose: () => void;
}

export const GetStarted: React.FC<GetStartedProps> = ({ onClose }) => {
  return (
    <section className="bg-white border border-line rounded-lg p-5 mb-6">
      <div className="flex justify-between font-semibold text-sm text-muted">
        <span>GET STARTED</span>
        <button
          onClick={onClose}
          className="border rounded px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
        >
          ♧ Got It
        </button>
      </div>
      <div className="flex items-center mt-7">
        <div className="w-40 text-5xl text-blue-300">◈</div>
        <div className="flex-1 flex items-start">
          <div className="flex-1 text-center">
            <div className="mx-auto w-4 h-4 rounded-full bg-blue ring-8 ring-blue-50"></div>
            <div className="mt-4 font-medium">
              1. Payment failure detected
            </div>
            <p className="text-xs text-muted">
              Transaction declined by bank
            </p>
          </div>
          <div className="h-px bg-slate-300 w-20 mt-2"></div>
          <div className="flex-1 text-center">
            <div className="mx-auto w-4 h-4 rounded-full bg-blue ring-8 ring-blue-50"></div>
            <div className="mt-4 font-medium">
              2. Recovery action taken
            </div>
            <p className="text-xs text-muted">
              Automated retry or escalation initiated
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
