import React, { useEffect, useMemo, useRef, useState } from "react";
import { createConversation, getConversation, listConversations, sendMessage } from "./api.js";

const URL_RE = /(https?:\/\/localhost:\d+\/?)/g;
const LOCAL_URL = /^https?:\/\/localhost:\d+\/?$/;

function MessageBody({ content }) {
  const parts = content.split(URL_RE);
  return parts.map((part, index) => {
    if (LOCAL_URL.test(part)) {
      return (
        <a key={`${part}-${index}`} href={part} target="_blank" rel="noopener noreferrer">
          {part}
        </a>
      );
    }
    return <React.Fragment key={`${index}`}>{part}</React.Fragment>;
  });
}

export function App() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const threadRef = useRef(null);

  async function refreshList(selectId) {
    const rows = await listConversations();
    setConversations(rows);
    const nextId = selectId || activeId || rows[0]?.id || null;
    setActiveId(nextId);
    if (nextId) {
      setActive(await getConversation(nextId));
    } else {
      setActive(null);
    }
  }

  useEffect(() => {
    refreshList().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const node = threadRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [active?.messages, busy]);

  async function onNew() {
    setError("");
    const created = await createConversation();
    await refreshList(created.id);
  }

  async function onSelect(id) {
    setError("");
    setActiveId(id);
    setActive(await getConversation(id));
  }

  async function onSend(event) {
    event.preventDefault();
    if (!activeId || !draft.trim() || busy) {
      return;
    }
    const text = draft.trim();
    const optimistic = {
      id: `local-${Date.now()}`,
      role: "user",
      content: text,
    };
    setDraft("");
    setError("");
    setBusy(true);
    setActive((current) =>
      current
        ? { ...current, messages: [...(current.messages || []), optimistic] }
        : current,
    );
    try {
      await sendMessage(activeId, text);
      await refreshList(activeId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const previewUrl = active?.preview_url || "";
  const messages = active?.messages || [];
  const status = useMemo(() => {
    if (!active) return "No conversation";
    return active.port ? `localhost:${active.port}` : active.status || "draft";
  }, [active]);

  return (
    <div className="app">
      <section className="pane" aria-label="Conversations">
        <div className="pane-head">
          <h1>Pages</h1>
          <button className="icon-btn" type="button" onClick={onNew}>
            New
          </button>
        </div>
        <div className="list">
          {conversations.length === 0 ? (
            <p className="empty">No conversations yet.</p>
          ) : (
            conversations.map((item) => (
              <button
                key={item.id}
                className={`list-item${item.id === activeId ? " active" : ""}`}
                type="button"
                onClick={() => onSelect(item.id)}
              >
                <span className="list-title">{item.title}</span>
                <span className="list-meta">{item.preview_url || item.status}</span>
              </button>
            ))
          )}
        </div>
      </section>

      <section className="pane" aria-label="Conversation thread">
        <div className="pane-head">
          <h2>{active?.title || "Thread"}</h2>
          <span className="list-meta">{status}</span>
        </div>
        <div className="thread" ref={threadRef}>
          {messages.map((message) => (
            <div key={message.id} className={`bubble ${message.role}`}>
              <MessageBody content={message.content} />
            </div>
          ))}
          {busy ? <div className="bubble pending">Working…</div> : null}
          {error ? <div className="bubble">{error}</div> : null}
        </div>
        <form className="composer" onSubmit={onSend}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Offer, audience, and CTA — or an edit to this page"
            disabled={!activeId}
          />
          <button className="primary-btn" type="submit" disabled={!activeId || busy}>
            {busy ? "Working" : "Send"}
          </button>
        </form>
      </section>

      <section className="pane" aria-label="Live preview">
        <div className="pane-head">
          <h2>Preview</h2>
          {previewUrl ? (
            <a href={previewUrl} target="_blank" rel="noopener noreferrer">
              {previewUrl}
            </a>
          ) : (
            <span className="list-meta">No page yet</span>
          )}
        </div>
        {previewUrl ? (
          <iframe className="preview-frame" title="Sales page preview" src={previewUrl} />
        ) : (
          <p className="preview-empty">Publish a page to see it here.</p>
        )}
      </section>
    </div>
  );
}
