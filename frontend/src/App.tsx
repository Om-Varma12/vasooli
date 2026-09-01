import React, { useState } from 'react';
import './styles/globals.css';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { TopStatusBar } from './components/layout/TopStatusBar';
import { Banner } from './components/ui/Banner';
import { GetStarted } from './components/features/GetStarted';
import { RecoveryActivityHeader } from './components/features/RecoveryActivityHeader';
import { RecoveryTable } from './components/features/RecoveryTable';
import { RecoveryRecord } from './types';

const MOCK_DATA: RecoveryRecord[] = [
  { id: "rec_A7K2M9L3X", customer: "cust_1847", amount: "₹5,400.00", rootCause: "Insufficient Funds", channel: "WhatsApp", retries: "2/3", message: "Hi, your payment failed. Please retry...", status: "Recovered", promiseCaptured: "✓" },
  { id: "rec_B4Q9P2W1Z", customer: "cust_5032", amount: "₹12,800.00", rootCause: "Mandate Expired", channel: "Voice Call", retries: "3/3", message: "We noticed your mandate has expired...", status: "Pending", promiseCaptured: "✓" },
  { id: "rec_C8N1R6T5V", customer: "cust_7210", amount: "₹2,250.00", rootCause: "Bank Downtime", channel: "Retry", retries: "1/3", message: "Your bank is temporarily unavailable...", status: "Recovered", promiseCaptured: "–" },
  { id: "rec_D2H7K4P9M", customer: "cust_2664", amount: "₹8,999.00", rootCause: "Risk Block", channel: "Human Handoff", retries: "3/3", message: "A specialist will help complete your payment...", status: "Unresolved", promiseCaptured: "–" },
  { id: "rec_E5L3S8W2Q", customer: "cust_9041", amount: "₹1,499.00", rootCause: "Cancellation Intent", channel: "Voice Call", retries: "2/3", message: "I understand you would like to cancel...", status: "Stopped", promiseCaptured: "–" },
  { id: "rec_F6J2V9A4K", customer: "cust_3378", amount: "₹6,750.00", rootCause: "Insufficient Funds", channel: "Retry", retries: "2/3", message: "A retry is scheduled for your account...", status: "Pending", promiseCaptured: "–" },
  { id: "rec_G1P8M5C3R", customer: "cust_6159", amount: "₹3,200.00", rootCause: "Bank Downtime", channel: "WhatsApp", retries: "1/3", message: "Payment systems are recovering. We will retry...", status: "Recovered", promiseCaptured: "✓" },
  { id: "rec_H9Q4B7N2D", customer: "cust_4586", amount: "₹18,400.00", rootCause: "Mandate Expired", channel: "Voice Call", retries: "3/3", message: "Please confirm a convenient payment date...", status: "Pending", promiseCaptured: "✓" },
  { id: "rec_J3K6T1X8L", customer: "cust_8023", amount: "₹950.00", rootCause: "Risk Block", channel: "Human Handoff", retries: "3/3", message: "Your case has been routed to our support team...", status: "Unresolved", promiseCaptured: "–" },
  { id: "rec_K7V2D5S9P", customer: "cust_1294", amount: "₹4,680.00", rootCause: "Cancellation Intent", channel: "WhatsApp", retries: "1/3", message: "We can pause reminders if you need assistance...", status: "Stopped", promiseCaptured: "–" },
];

function App() {
  const [activeTab, setActiveTab] = useState('payments');
  const [testMode, setTestMode] = useState(true);
  const [showGetStarted, setShowGetStarted] = useState(true);
  const [banners, setBanners] = useState([
    { id: 'a', title: 'Bounded, Auditable Recovery', content: 'Every retry, message, and call this system takes is logged and explainable.', linkText: 'View Audit Trail', variant: 'default' as const },
    { id: 'b', title: 'Vasooli Guardrails', content: 'NPCI caps automated retries at 3 attempts — this system enforces that limit in code, not just policy.', linkText: 'Learn more', variant: 'info' as const },
  ]);

  const removeBanner = (id: string) => {
    setBanners(prev => prev.filter(b => b.id !== id));
  };

  return (
    <div className="shell min-h-screen bg-bg">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />
      <Sidebar testMode={testMode} setTestMode={setTestMode} />
      <TopStatusBar testMode={testMode} setTestMode={setTestMode} />

      <main className="ml-[300px] pt-24 pl-1 pr-2 pb-16">
        {banners.map(banner => (
          <Banner
            key={banner.id}
            title={banner.title}
            content={banner.content}
            linkText={banner.linkText}
            variant={banner.variant}
            onClose={() => removeBanner(banner.id)}
          />
        ))}

        {showGetStarted && (
          <GetStarted onClose={() => setShowGetStarted(false)} />
        )}

        <RecoveryActivityHeader activeTab={activeTab} setActiveTab={setActiveTab} />

        <div className="bg-orange-50 rounded px-4 py-2 text-[13px] mb-3">
          You are in <b>Test Mode</b>, so only test data is shown.
          <a href="#" className="text-blue ml-1 hover:underline">Activate your account →</a>
        </div>

        <RecoveryTable data={MOCK_DATA} />
      </main>

      <button className="fixed bottom-5 right-7 z-40 bg-ink hover:bg-slate-950 text-white rounded-full px-5 py-3 text-xs font-semibold transition-colors">
        ♧ &nbsp;Help &amp; Support
      </button>
    </div>
  );
}

export default App;
