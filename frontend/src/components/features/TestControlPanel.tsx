import React, { useState } from 'react';
import { Play, Terminal, CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface TestScript {
  key: string;
  label: string;
  description: string;
}

const AVAILABLE_SCRIPTS: TestScript[] = [
  { key: 'gen_tests', label: 'Generate Tests', description: 'Generates test cases for pipeline validation' },
  { key: 'generate_data', label: 'Generate Synthetic Data', description: 'Populates database with synthetic recovery records' },
  { key: 'run_demo', label: 'Run Demo Pipeline', description: 'Executes the demo recovery pipeline on batch data' },
  { key: 'test_voice', label: 'Test Voice Send', description: 'Tests the voice escalation delivery channel' },
  { key: 'test_whatsapp', label: 'Test WhatsApp Send', description: 'Tests the WhatsApp messaging delivery channel' },
  { key: 'trigger_bouncer', label: 'Trigger Chronic Bouncer', description: 'Simulates a chronic bouncer scenario for testing' },
];

interface TestControlPanelProps {
  apiUrl: string;
}

export const TestControlPanel: React.FC<TestControlPanelProps> = ({ apiUrl }) => {
  const [runningScript, setRunningScript] = useState<string | null>(null);
  const [output, setOutput] = useState<{ stdout: string; stderr: string; status: string } | null>(null);

  const runScript = async (key: string) => {
    setRunningScript(key);
    setOutput(null);
    try {
      const res = await fetch(`${apiUrl}/system/run-test/${key}`, {
        method: 'POST',
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Script execution failed');
      }

      setOutput({
        stdout: data.stdout,
        stderr: data.stderr,
        status: data.status,
      });
    } catch (e: any) {
      setOutput({
        stdout: '',
        stderr: e.message,
        status: 'failed',
      });
    } finally {
      setRunningScript(null);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1 space-y-4">
        <div className="bg-white border border-[#e5e7eb] rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-bold mb-4 flex items-center gap-2">
            <Play size={16} className="text-blue" />
            Test Suite
          </h3>
          <div className="space-y-2">
            {AVAILABLE_SCRIPTS.map((script) => (
              <button
                key={script.key}
                onClick={() => runScript(script.key)}
                disabled={runningScript !== null}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  runningScript === script.key
                    ? 'bg-blue-50 border-blue text-blue ring-1 ring-blue'
                    : 'bg-white border-[#dfe3e8] hover:border-blue hover:bg-slate-50'
                } ${runningScript !== null && runningScript !== script.key ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold">{script.label}</span>
                  {runningScript === script.key && <Loader2 size={12} className="animate-spin" />}
                </div>
                <div className="text-[11px] text-[#6b7280] mt-1">{script.description}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="lg:col-span-2">
        <div className="bg-[#0f172a] rounded-xl overflow-hidden shadow-lg border border-slate-800 h-full min-h-[400px] flex flex-col">
          <div className="bg-slate-800 px-4 py-2 flex justify-between items-center border-b border-slate-700">
            <div className="flex items-center gap-2 text-slate-300">
              <Terminal size={14} />
              <span className="text-xs font-mono">vasooli-test-console</span>
            </div>
            {output && (
              <div className="flex items-center gap-2">
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                  output.status === 'success' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                }`}>
                  {output.status.toUpperCase()}
                </span>
              </div>
            )}
          </div>
          <div className="p-4 font-mono text-xs overflow-auto flex-1">
            {!output && !runningScript && (
              <div className="text-slate-500 italic">
                Select a script to execute. Output will appear here...
              </div>
            )}
            {runningScript && (
              <div className="text-blue-400 flex items-center gap-2">
                <Loader2 size={12} className="animate-spin" />
                Executing {AVAILABLE_SCRIPTS.find(s => s.key === runningScript)?.label}...
              </div>
            )}
            {output && (
              <div className="space-y-4">
                {output.stdout && (
                  <div className="space-y-1">
                    <div className="text-slate-500 font-bold flex items-center gap-2">
                      <CheckCircle size={12} className="text-green-500" /> STDOUT
                    </div>
                    <pre className="text-slate-300 whitespace-pre-wrap leading-relaxed">
                      {output.stdout}
                    </pre>
                  </div>
                )}
                {output.stderr && (
                  <div className="space-y-1">
                    <div className="text-slate-500 font-bold flex items-center gap-2">
                      <XCircle size={12} className="text-red-500" /> STDERR
                    </div>
                    <pre className="text-red-400 whitespace-pre-wrap leading-relaxed">
                      {output.stderr}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
