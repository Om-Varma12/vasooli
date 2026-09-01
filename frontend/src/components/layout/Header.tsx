import React from 'react';
import { Search, Activity, Bell, LayoutGrid } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  const navLinks = [
    { id: 'home', label: '⌂ Razorpay Home' },
    { id: 'payments', label: '▣ Payments' },
    { id: 'company', label: '♧ Company Registration' },
    { id: 'banking', label: '⚒ Banking+' },
    { id: 'payroll', label: '▤ Payroll ↗' },
    { id: 'more', label: 'More⌄' },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 h-14 bg-navy text-white z-40 flex items-center px-7 gap-10">
      <div className="text-xl italic font-semibold w-56">
        <span className="text-sky-400">↗</span>Razorpay
      </div>
      <nav className="flex items-center gap-7 text-[13px] text-slate-300">
        {navLinks.map((link) => (
          <a
            key={link.id}
            href="#"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab(link.id);
            }}
            className={`transition-all duration-150 ${
              activeTab === link.id
                ? 'text-white font-semibold border-b-2 border-blue h-14 flex items-center'
                : 'hover:text-white'
            }`}
          >
            {link.label}
          </a>
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-2">
        <div className="w-88 h-10 rounded-lg border border-slate-700 bg-slate-800 flex items-center px-3 gap-2 text-slate-400 text-[13px]">
          <Search size={16} />
          <span>Search payment products, settings, and more</span>
        </div>
        <button aria-label="Activity" className="w-9 h-9 border border-slate-700 rounded-lg flex items-center justify-center">
          <Activity size={18} />
        </button>
        <button aria-label="Notifications" className="w-9 h-9 border border-slate-700 rounded-lg flex items-center justify-center">
          <Bell size={18} />
        </button>
        <button aria-label="Apps" className="w-9 h-9 border border-slate-700 rounded-lg flex items-center justify-center">
          <LayoutGrid size={18} />
        </button>
        <div className="w-9 h-9 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-semibold text-xs">
          OV
        </div>
      </div>
    </header>
  );
};
