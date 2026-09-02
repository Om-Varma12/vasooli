import React, { useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { TopStatusBar } from './components/layout/TopStatusBar';
import { Banner } from './components/ui';
import { GetStarted } from './components/features/GetStarted';
import { RecoveryActivityHeader } from './components/features/RecoveryActivityHeader';
import { RecoveryTable } from './components/features/RecoveryTable';
import { TestControlPanel } from './components/features/TestControlPanel';
import type { RecoveryRecord } from './types/recovery';



const API_BASE_URL = "http://localhost:8000";

function App() {
  const [activeTab, setActiveTab] = useState('payments');
  const [testMode, setTestMode] = useState(true);
  const [showGetStarted, setShowGetStarted] = useState(true);
  const [recoveryData, setRecoveryData] = useState<RecoveryRecord[]>([]);
  const [banners, setBanners] = useState([
    { id: 'a', title: 'Bounded, Auditable Recovery', content: 'Every retry, message, and call this system takes is logged and explainable.', linkText: 'View Audit Trail', variant: 'default' as const },
    { id: 'b', title: 'Vasooli Guardrails', content: 'NPCI caps automated retries at 3 attempts — this system enforces that limit in code, not just policy.', linkText: 'Learn more', variant: 'info' as const },
  ]);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/recovery-events`);
      const json = await res.json();
      // Assuming the API returns { data: RecoveryRecord[], next_cursor: string }
      setRecoveryData(json.data || []);
    } catch (e) {
      console.error("Failed to fetch recovery events:", e);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunTest = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/recovery-events/${id}/run`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || "Pipeline execution failed");
      }
      alert("Pipeline triggered successfully!");
      await fetchData();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    }
  };

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

        {activeTab === 'TEST mode' ? (
          <TestControlPanel apiUrl={API_BASE_URL} />
        ) : (
          <>
            <div className="bg-orange-50 rounded px-4 py-2 text-[13px] mb-3">
              You are in <b>Test Mode</b>, so only test data is shown.
              <a href="#" className="text-blue ml-1 hover:underline">Activate your account →</a>
            </div>

            <RecoveryTable data={recoveryData} onRunTest={handleRunTest} />
          </>
        )}
      </main>

      <button className="fixed bottom-5 right-7 z-40 bg-ink hover:bg-slate-950 text-white rounded-full px-5 py-3 text-xs font-semibold transition-colors">
        ♧ &nbsp;Help &amp; Support
      </button>
    </div>
  );
}

export default App;
