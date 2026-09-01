import React from 'react';
import {
  Home,
  ArrowLeftRight,
  CheckCheck,
  FileText,
  Link,
  Bot,
  PanelsTopLeft,
  AtSign,
  Files,
  CreditCard,
  Percent,
  QrCode,
  RefreshCw,
  Landmark,
  Banknote,
  Compass,
  Shield,
  GitBranch,
  Settings
} from 'lucide-react';
import { Badge, Toggle } from '../ui';

interface SidebarProps {
  testMode: boolean;
  setTestMode: (val: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ testMode, setTestMode }) => {
  const mainNav = [
    { icon: Home, label: 'Home', active: false },
    { icon: ArrowLeftRight, label: 'Transactions' },
    { icon: CheckCheck, label: 'Settlements' },
    { icon: FileText, label: 'Reports' },
  ];

  const paymentProducts = [
    { icon: Link, label: 'Payment Links', badge: { text: 'New Update', variant: 'update' as const } },
    { icon: Bot, label: 'Vasooli', badge: { text: 'AI', variant: 'ai' as const }, special: true },
    { icon: PanelsTopLeft, label: 'Payment Pages' },
    { icon: AtSign, label: 'Razorpay.me Link' },
    { icon: Files, label: 'Invoices' },
    { icon: CreditCard, label: 'Payment Button' },
    { icon: Percent, label: 'Affordability' },
    { icon: QrCode, label: 'QR Codes' },
    { icon: RefreshCw, label: 'Subscriptions' },
    { icon: Landmark, label: 'Smart Collect' },
    { icon: Banknote, label: 'Checkout Rewards' },
    { icon: Compass, label: 'Konnect' },
    { icon: Shield, label: 'Customer Trust' },
    { icon: GitBranch, label: 'Optimizer' },
  ];

  return (
    <aside className="fixed top-14 bottom-0 left-0 w-[290px] bg-white border-r border-line z-30 flex flex-col">
      <div className="p-2 pt-3">
        {mainNav.map((item) => (
          <div
            key={item.label}
            className={`side-row rounded-lg px-3 py-2.5 flex gap-3 items-center transition-all duration-150 cursor-pointer ${
              item.active ? 'bg-slate-100 text-blue font-semibold' : 'hover:bg-slate-100'
            }`}
          >
            <item.icon size={18} />
            {item.label}
          </div>
        ))}

        <div className="text-[11px] text-slate-400 mt-5 mb-1 px-3">
          PAYMENT PRODUCTS
        </div>

        {paymentProducts.map((item) => (
          <div
            key={item.label}
            className={`side-row px-3 py-2 flex gap-3 items-center transition-all duration-150 cursor-pointer ${
              item.special ? 'bg-slate-100 text-blue font-semibold' : 'hover:bg-slate-100'
            }`}
          >
            <item.icon size={18} />
            <span className="flex-1">{item.label}</span>
            {item.badge && <Badge variant={item.badge.variant}>{item.badge.text}</Badge>}
          </div>
        ))}

        <div className="px-3 py-2 text-xs text-muted cursor-pointer hover:text-blue">
          Show Less⌃
        </div>
      </div>

      <div className="mt-auto border-t border-line p-3">
        <div className="flex justify-between items-center py-2">
          <span className="text-sm">♙ &nbsp;Test Mode</span>
          <Toggle on={testMode} onChange={setTestMode} />
        </div>
        <div className="py-2 text-sm cursor-pointer hover:text-blue flex items-center gap-2">
          <Settings size={16} /> Account & Settings
        </div>
      </div>
    </aside>
  );
};
