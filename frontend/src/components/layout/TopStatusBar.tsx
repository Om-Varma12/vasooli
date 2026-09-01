import React from 'react';
import { KeyRound, Expand, List } from 'lucide-react';
import { Toggle } from '../ui';

interface TopStatusBarProps {
  testMode: boolean;
  setTestMode: (val: boolean) => void;
}

export const TopStatusBar: React.FC<TopStatusBarProps> = ({ testMode, setTestMode }) => {
  return (
    <div className="fixed top-14 right-0 h-10 bg-bg z-20 flex items-center gap-5 px-8">
      <Toggle on={testMode} onChange={setTestMode} />
      <span className="tracking-[4px] text-xs text-slate-500">TEST</span>
      <KeyRound size={16} className="text-slate-600 cursor-pointer hover:text-blue" />
      <Expand size={16} className="text-slate-600 cursor-pointer hover:text-blue" />
      <List size={16} className="text-slate-600 cursor-pointer hover:text-blue" />
    </div>
  );
};
