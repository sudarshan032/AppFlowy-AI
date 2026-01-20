import React, { useState, useEffect, useRef } from 'react';

function App() {
  const [prompt, setPrompt] = useState("");
  const [logs, setLogs] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [messages, setMessages] = useState([]);
  const logsEndRef = useRef(null);

  const API_BASE = "http://localhost:8000";

  useEffect(() => {
    fetchDatabases();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const fetchDatabases = async () => {
    try {
      const res = await fetch(`${API_BASE}/databases`);
      if (res.ok) {
        const data = await res.json();
        setDatabases(data.databases || []);
      }
    } catch (e) {
      console.error("Failed to fetch DBs", e);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/logs`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (e) {
      // silent
    }
  };

  const sendPrompt = async () => {
    if (!prompt.trim()) return;

    const userMsg = { role: "user", text: prompt };
    setMessages(prev => [...prev, userMsg]);
    setPrompt("");

    try {
      const res = await fetch(`${API_BASE}/run-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: userMsg.text })
      });

      const data = await res.json();
      const agentMsg = {
        role: "agent",
        text: JSON.stringify(data, null, 2),
        status: data.status
      };
      setMessages(prev => [...prev, agentMsg]);
      fetchDatabases(); // Refresh DB list
    } catch (e) {
      setMessages(prev => [...prev, { role: "agent", text: `Error: ${e.message}`, status: "error" }]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex font-sans">
      {/* Sidebar - Databases */}
      <div className="w-64 bg-slate-800 p-4 border-r border-slate-700 flex flex-col">
        <h2 className="text-xl font-bold mb-4 text-emerald-400">Databases</h2>
        <div className="flex-1 overflow-y-auto space-y-2">
          {databases.length === 0 && <p className="text-slate-500 italic">No databases yet.</p>}
          {databases.map((db, i) => (
            <div key={i} className="p-2 bg-slate-700 rounded hover:bg-slate-600 transition cursor-pointer">
              <div className="font-medium">{db.name}</div>
              <div className="text-xs text-slate-400">{db.description || "No description"}</div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-slate-700">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">Templates</h3>
          <div className="flex flex-wrap gap-2">
            {["CRM", "Tracker", "Notes"].map(t => (
              <button
                key={t}
                onClick={() => setPrompt(`Create a ${t}`)}
                className="px-2 py-1 text-xs bg-indigo-600 rounded hover:bg-indigo-500"
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center px-6">
          <h1 className="font-bold text-lg">Agent Operator</h1>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-sm text-emerald-500">Online</span>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-900">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 mt-20">
              <p className="text-lg">Ready for commands.</p>
              <p className="text-sm">Try "Create a database called Clients"</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-2xl p-4 rounded-lg shadow-lg ${msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-none"
                  : "bg-slate-700 text-slate-200 rounded-bl-none border border-slate-600"
                }`}>
                {msg.role === "agent" ? (
                  <pre className="text-xs overflow-x-auto whitespace-pre-wrap font-mono">{msg.text}</pre>
                ) : (
                  <div>{msg.text}</div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 bg-slate-800 border-t border-slate-700">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              type="text"
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendPrompt()}
              placeholder="Ask the agent to do something..."
              className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500 transition"
            />
            <button
              onClick={sendPrompt}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition"
            >
              Send
            </button>
          </div>
        </div>

        {/* Logs Panel (Overlay or Bottom) */}
        <div className="h-48 bg-black/80 border-t border-slate-700 overflow-y-auto p-2 font-mono text-xs text-green-400">
          <div className="sticky top-0 bg-black/80 px-2 py-1 border-b border-gray-800 font-bold text-gray-400 flex justify-between">
            <span>System Logs</span>
            <span className="text-gray-600">Auto-refreshing</span>
          </div>
          {logs.map((log, i) => (
            <div key={i} className="py-0.5 border-b border-gray-800/50">
              <span className="text-gray-500">[{log.time}]</span> {log.message}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}

export default App;
