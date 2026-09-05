import React, { useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { TopStatusBar } from './components/layout/TopStatusBar';
import { Banner } from './components/ui';
import { GetStarted } from './components/features/GetStarted';
import { RecoveryActivityHeader } from './components/features/RecoveryActivityHeader';
import { RecoveryTable } from './components/features/RecoveryTable';
import { TestControlPanel } from './components/features/TestControlPanel';
import { AuditPanel } from './components/features/AuditPanel';
import type { RecoveryRecord } from './types/recovery';

const API_BASE_URL = "http://127.0.0.1:8001";

function App() {
  const [activeTab, setActiveTab] = useState('payments');
  const [testMode, setTestMode] = useState(true);
  const [showGetStarted, setShowGetStarted] = useState(true);
  const [recoveryData, setRecoveryData] = useState<RecoveryRecord[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [isAuditLoading, setIsAuditLoading] = useState(false);

  const [banners, setBanners] = useState([
    { id: 'a', title: 'Bounded, Auditable Recovery', content: 'Every retry, message, and call this system takes is logged and explainable.', linkText: 'View Audit Trail', variant: 'default' as const },
    { id: 'b', title: 'Vasooli Guardrails', content: 'NPCI caps automated retries at 3 attempts — this system enforces that limit in code, not just policy.', linkText: 'Learn more', variant: 'info' as const },
  ]);

  const fetchData = async () => {
    try {
      const [eventsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/recovery-events`),
        fetch(`${API_BASE_URL}/recovery-events/stats`)
      ]);

      const eventsJson = await eventsRes.json();
      const statsJson = await statsRes.json();

      setRecoveryData(eventsJson.data || []);
      setStats(statsJson);
    } catch (e) {
      console.error("Failed to fetch recovery data:", e);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchAuditLogs = async (id: string) => {
    setIsAuditLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/recovery-events/${id}/audit`);
      const data = await res.json();
      setAuditLogs(data);
    } catch (e) {
      console.error("Failed to fetch audit logs:", e);
    } finally {
      setIsAuditLoading(false);
    }
  };

  const handleSelectRecord = (id: string) => {
    setSelectedRecordId(id);
    fetchAuditLogs(id);
  };

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

            {stats && (
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-white border border-[#e5e7eb] p-4 rounded-xl shadow-sm">
                  <p className="text-[11px] text-[#6b7280] uppercase font-medium">Total At Risk</p>
                  <p className="text-xl font-bold text-ink">₹{stats.total_amount_at_risk.toLocaleString()}</p>
                </div>
                <div className="bg-white border border-[#e5e7eb] p-4 rounded-xl shadow-sm">
                  <p className="text-[11px] text-[#6b7280] uppercase font-medium">Recovered</p>
                  <p className="text-xl font-bold text-green-600">₹{stats.total_recovered.toLocaleString()}</p>
                </div>
                <div className="bg-white border border-[#e5e7eb] p-4 rounded-xl shadow-sm">
                  <p className="text-[11px] text-[#6b7280] uppercase font-medium">Recovery Rate</p>
                  <p className="text-xl font-bold text-ink">{stats.recovery_rate.toFixed(1)}%</p>
                </div>
                <div className="bg-white border border-[#e5e7eb] p-4 rounded-xl shadow-sm">
                  <p className="text-[11px] text-[#6b7280] uppercase font-medium">Active Retries</p>
                  <p className="text-xl font-bold text-blue-600">{stats.state_distribution['RETRYING'] || 0}</p>
                </div>
              </div>
            )}

            <RecoveryTable data={recoveryData} onRunTest={handleRunTest} onSelectRecord={handleSelectRecord} />
          </>
        )}
      </main>

      <AuditPanel
        recordId={selectedRecordId}
        logs={auditLogs}
        isLoading={isAuditLoading}
        onClose={() => setSelectedRecordId(null)}
      />

      <button className="fixed bottom-5 right-7 z-40 bg-ink hover:bg-slate-950 text-white rounded-full px-5 py-3 text-xs font-semibold transition-colors">
        ♧ &nbsp;Help &amp; Support
      </button>
    </div>
  );
}

export default App;
