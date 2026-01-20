import React, { useState, useEffect, useRef } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState("page"); // page | workspace
  const chatEndRef = useRef(null);

  const API_BASE = "http://localhost:8000";

  useEffect(() => {
    fetchContext();
    const interval = setInterval(fetchContext, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchContext = async () => {
    try {
      const res = await fetch(`${API_BASE}/context`);
      if (res.ok) {
        const data = await res.json();
        setContext(data);
      }
    } catch (e) {
      console.error("Context fetch failed", e);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userText = input;
    setInput("");
    setMessages(prev => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/run-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: userText,
          context: scope === "page" ? context : null,
          scope: scope
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          role: 'assistant',
          text: data.result?.explanation || data.result?.message || JSON.stringify(data.result, null, 2),
          status: data.status
        }]);
      } else {
        const errorData = await res.json().catch(() => ({ detail: "Unknown Error" }));
        throw new Error(errorData.detail || "API Error");
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', text: `Error: ${e.message}`, status: 'error' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-panel flex flex-col text-slate-200">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <span className="text-indigo-400">🤖</span> AI Agent
        </h1>
        <div className="flex bg-slate-800 rounded-lg p-0.5 text-xs">
          <button
            onClick={() => setScope("page")}
            className={`px-3 py-1 rounded-md transition ${scope === "page" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            Page
          </button>
          <button
            onClick={() => setScope("workspace")}
            className={`px-3 py-1 rounded-md transition ${scope === "workspace" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            Workspace
          </button>
        </div>
      </div>

      {/* Context Bar */}
      {context && context.status === "success" && (
        <div className="px-4 py-2 bg-indigo-500/10 border-b border-indigo-500/20 text-[10px] flex items-center gap-2">
          <span className="text-indigo-400 font-bold uppercase tracking-wider">Active:</span>
          <span className="truncate text-slate-300">{context.page_name}</span>
          {context.page_type && (
            <span className="bg-indigo-500/20 px-1.5 py-0.5 rounded text-indigo-300">{context.page_type}</span>
          )}
        </div>
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="mt-10 text-center space-y-2">
            <p className="text-slate-400">Ask anything in the context of this page.</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {["Help me set up a DB", "Summarize this page", "Add 5 records"].map(hint => (
                <button
                  key={hint}
                  onClick={() => setInput(hint)}
                  className="text-[10px] px-2 py-1 bg-slate-800 border border-white/5 rounded hover:border-indigo-500/50 transition"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-3 rounded-xl text-sm ${m.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-none'
                : 'bg-white/5 border border-white/10 text-slate-200 rounded-bl-none'
              }`}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 border border-white/10 p-3 rounded-xl rounded-bl-none animate-pulse">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></div>
                <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0.4s]"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/10 bg-slate-900/50">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Cmd + J to toggle AI..."
            rows={2}
            className="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500/50 resize-none transition"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="absolute right-3 bottom-3 p-1.5 bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition"
          >
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>
        </div>
        <p className="text-[9px] text-slate-500 mt-2 text-center">
          Press Enter to send. Shift + Enter for new line.
        </p>
      </div>
    </div>
  );
}

export default App;
