import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Bot, User, RefreshCw } from "lucide-react";
import { chatApi } from "../services/chatApi";
import type { ChatMessage } from "../types";
import { SourceReference } from "../components/ai/SourceReference";


const DEFAULT_SUGGESTED_PROMPTS = [
  "How much time was spent in VS Code?",
  "Was there any suspicious activity?",
  "Generate an activity report",
  "What did the engineer work on?",
  "Are there any security alerts?",
  "Show enterprise productivity breakdown",
];

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "init_1",
      role: "assistant",
      content:
        "Hello Administrator. I am **WorkGuard Multi-Agent Copilot**, backed by the **Supervisor Agent** orchestrating Session Analysis, Security Intelligence, and Executive Reporting.\n\nYou can ask about employee activity, security anomalies, IDE metrics, or generate full forensic reports.",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>(DEFAULT_SUGGESTED_PROMPTS);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    chatApi.getSuggestions()
      .then((data) => {
        if (data?.suggestions && data.suggestions.length > 0) {
          setSuggestedPrompts(data.suggestions);
        }
      })
      .catch(() => { });
  }, []);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    };

    const updatedHistory = [...messages, userMsg];
    setMessages(updatedHistory);
    setInput("");
    setLoading(true);

    try {
      const historyPayload = updatedHistory.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await chatApi.sendMessage(query, historyPayload);
      const assistantMsg: ChatMessage = {
        id: `ast_${Date.now()}`,
        role: "assistant",
        content: res.answer,
        timestamp: new Date().toISOString(),
        sources: res.sources,
        routed_agent: res.routed_agent,
        suggested_followups: res.suggested_followups,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `⚠️ **Error communicating with WorkGuard AI Engine:** ${err.message || "Failed to reach AI service."}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 64px)",
        padding: "24px 28px",
        gap: "16px",
      }}
    >
      {/* Header Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              backgroundColor: "var(--apple-blue-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--apple-blue)",
            }}
          >
            <Sparkles size={18} />
          </div>
          <div>
            <h2 style={{ fontSize: "1rem", fontWeight: 700 }}>WorkGuard AI Copilot</h2>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              RAG telemetry synthesis over decrypted employee sessions & vector stores
            </p>
          </div>
        </div>

        <button
          onClick={() =>
            setMessages([
              {
                id: "init_1",
                role: "assistant",
                content: "Chat session cleared. How can I assist you with WorkGuard telemetry?",
                timestamp: new Date().toISOString(),
              },
            ])
          }
          className="apple-btn apple-btn-secondary"
          style={{ fontSize: "0.75rem", padding: "5px 10px" }}
        >
          <RefreshCw size={12} />
          <span>Clear Chat</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div
        className="glass-panel"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "18px",
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: "flex",
              gap: "12px",
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: msg.role === "user" ? "75%" : "85%",
            }}
          >
            {msg.role === "assistant" && (
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  backgroundColor: "var(--apple-blue)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#FFF",
                  flexShrink: 0,
                }}
              >
                <Bot size={16} />
              </div>
            )}

            <div
              style={{
                padding: "14px 18px",
                borderRadius: "var(--radius-lg)",
                backgroundColor:
                  msg.role === "user" ? "var(--apple-blue)" : "var(--system-grouped-bg)",
                color: msg.role === "user" ? "#FFFFFF" : "var(--text-primary)",
                border: msg.role === "assistant" ? "1px solid var(--border-subtle)" : "none",
                fontSize: "0.85rem",
                lineHeight: 1.5,
              }}
            >
              {msg.role === "assistant" && msg.routed_agent && (
                <div style={{ marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span
                    style={{
                      fontSize: "0.68rem",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      padding: "2px 8px",
                      borderRadius: "12px",
                      backgroundColor:
                        msg.routed_agent === "security"
                          ? "rgba(239, 68, 68, 0.15)"
                          : msg.routed_agent === "reporting"
                            ? "rgba(168, 85, 247, 0.15)"
                            : "rgba(59, 130, 246, 0.15)",
                      color:
                        msg.routed_agent === "security"
                          ? "#ef4444"
                          : msg.routed_agent === "reporting"
                            ? "#a855f7"
                            : "#3b82f6",
                      border: "1px solid currentColor",
                    }}
                  >
                    {msg.routed_agent === "security"
                      ? "🛡️ Security Intelligence Agent"
                      : msg.routed_agent === "reporting"
                        ? "📊 Executive Reporting Agent"
                        : msg.routed_agent === "knowledge"
                          ? "📖 Knowledge & Policy Agent"
                          : "🔍 Session Analysis Agent"}
                  </span>
                </div>
              )}

              <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>

              {/* Follow-up suggestions */}
              {msg.suggested_followups && msg.suggested_followups.length > 0 && (
                <div style={{ marginTop: "12px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", fontWeight: 700, marginBottom: "6px" }}>
                    Suggested Follow-ups:
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {msg.suggested_followups.map((fu, fIdx) => (
                      <button
                        key={fIdx}
                        onClick={() => handleSend(fu)}
                        disabled={loading}
                        style={{
                          background: "var(--system-surface-solid)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "12px",
                          padding: "3px 8px",
                          fontSize: "0.72rem",
                          color: "var(--apple-blue)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        ↳ {fu}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* RAG Transparency: Clickable Source Citations (Section 13 & 14) */}
              {msg.sources && msg.sources.length > 0 && (
                <div
                  style={{
                    marginTop: "12px",
                    paddingTop: "10px",
                    borderTop: "1px solid var(--border-subtle)",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", fontWeight: 700, textTransform: "uppercase" }}>
                    Sources / Evidence:
                  </span>
                  {msg.sources.map((s) => (
                    <SourceReference key={s} sessionId={s} />
                  ))}
                </div>
              )}
            </div>

            {msg.role === "user" && (
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  backgroundColor: "var(--system-grouped-bg)",
                  border: "1px solid var(--border-subtle)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-secondary)",
                  flexShrink: 0,
                }}
              >
                <User size={16} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", gap: "12px", alignSelf: "flex-start" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                backgroundColor: "var(--apple-blue)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#FFF",
              }}
            >
              <Bot size={16} />
            </div>
            <div
              style={{
                padding: "12px 18px",
                borderRadius: "var(--radius-lg)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
                fontSize: "0.82rem",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <div className="pulse-indicator" style={{ width: "8px", height: "8px" }} />
              <span>Analyzing telemetry with LangGraph & Ollama...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts Pills */}
      <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "2px", flexShrink: 0 }}>
        {suggestedPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(prompt)}
            className="badge badge-gray"
            style={{
              cursor: "pointer",
              whiteSpace: "nowrap",
              fontSize: "0.75rem",
              padding: "6px 12px",
              border: "1px solid var(--border-subtle)",
              transition: "all var(--transition-fast)",
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        style={{
          display: "flex",
          gap: "10px",
          flexShrink: 0,
        }}
      >
        <input
          type="text"
          placeholder="Ask WorkGuard Copilot about employee activity or security telemetry..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          style={{
            flex: 1,
            padding: "12px 18px",
            borderRadius: "var(--radius-pill)",
            border: "1px solid var(--border-subtle)",
            backgroundColor: "var(--system-surface-solid)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
            outline: "none",
            boxShadow: "var(--shadow-subtle)",
          }}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="apple-btn apple-btn-primary"
          style={{
            borderRadius: "var(--radius-pill)",
            padding: "0 22px",
            opacity: !input.trim() || loading ? 0.6 : 1,
          }}
        >
          <Send size={15} />
          <span>Ask</span>
        </button>
      </form>
    </div>
  );
};
