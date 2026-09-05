import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { createConversation, getConversation, listConversations, sendMessage } from "./api.js";

const HEBREW_RE = /[\u0590-\u05FF]/;

function isHebrew(text) {
  return ((text || "").match(HEBREW_RE) || []).length >= 3;
}

function pagePills(conversation, generating) {
  if (generating) {
    return [{ key: "generating", label: "Generating" }];
  }
  const pills = [];
  if (conversation?.status === "error") {
    pills.push({ key: "error", label: "Error" });
  } else if (conversation?.preview_url) {
    pills.push({ key: "live", label: "Live" });
  } else {
    pills.push({ key: "draft", label: "Draft" });
  }
  if (conversation?.preview_url && conversation?.images_pending) {
    pills.push({ key: "pending", label: "Images pending" });
  }
  return pills;
}

function StatusPills({ pills }) {
  return (
    <span className="pills">
      {pills.map((pill) => (
        <span key={pill.key} className={`pill ${pill.key}`}>
          {pill.label}
        </span>
      ))}
    </span>
  );
}

function MessageBody({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a({ href, children, ...props }) {
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
              {children}
            </a>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export function App() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [previewNonce, setPreviewNonce] = useState(0);
  const [previewWidth, setPreviewWidth] = useState("desktop");
  const [copyNote, setCopyNote] = useState("");
  const threadRef = useRef(null);
  const composerRef = useRef(null);

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

  useEffect(() => {
    if (active && (active.messages || []).length === 0 && !busy) {
      composerRef.current?.focus();
    }
  }, [activeId, active?.messages?.length, busy]);

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
    setProgress({
      label: "Working…",
      detail: "Starting the page pipeline",
      short: "Working",
      steps: [],
    });
    setActive((current) =>
      current
        ? { ...current, messages: [...(current.messages || []), optimistic] }
        : current,
    );
    try {
      await sendMessage(activeId, text, (event) => {
        setProgress((current) => {
          const step = {
            stage: event.stage,
            label: event.label,
            detail: event.detail,
            current: true,
          };
          const prior = (current?.steps || []).map((item) => ({ ...item, current: false }));
          const without = prior.filter((item) => item.stage !== event.stage);
          return {
            ...event,
            steps: [...without, step],
          };
        });
      });
      setPreviewNonce((value) => value + 1);
      await refreshList(activeId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  async function onCopyLink() {
    if (!active?.preview_url) {
      return;
    }
    try {
      await navigator.clipboard.writeText(active.preview_url);
      setCopyNote("Copied");
    } catch {
      setCopyNote("Copy failed");
    }
    window.setTimeout(() => setCopyNote(""), 1600);
  }

  const previewUrl = active?.preview_url || "";
  const iframeSrc = previewUrl ? `${previewUrl}${previewUrl.includes("?") ? "&" : "?"}v=${previewNonce}` : "";
  const messages = active?.messages || [];
  const activePills = useMemo(() => pagePills(active, Boolean(busy && active)), [active, busy]);

  return (
    <div className="app">
      <header className="app-bar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div className="brand-text">
            <strong>Homerun</strong>
            <span>Sales Page Builder</span>
          </div>
        </div>
        <div className="app-bar-meta">
          {active ? <StatusPills pills={activePills} /> : null}
          {previewUrl ? (
            <a className="toolbar-link" href={previewUrl} target="_blank" rel="noopener noreferrer">
              Open
            </a>
          ) : null}
        </div>
      </header>
      <section className="pane" aria-label="Conversations">
        <div className="pane-head">
          <h1>Pages</h1>
          <button className="icon-btn" type="button" onClick={onNew}>
            New page
          </button>
        </div>
        <div className="list">
          {conversations.length === 0 ? (
            <p className="empty">Create a page to start. Each conversation is one sales page.</p>
          ) : (
            conversations.map((item) => (
              <button
                key={item.id}
                className={`list-item${item.id === activeId ? " active" : ""}`}
                type="button"
                onClick={() => onSelect(item.id)}
              >
                <span
                  className="list-title"
                  dir={isHebrew(item.title) ? "rtl" : "ltr"}
                  lang={isHebrew(item.title) ? "he" : undefined}
                >
                  {item.title}
                </span>
                <StatusPills pills={pagePills(item, busy && item.id === activeId)} />
              </button>
            ))
          )}
        </div>
      </section>

      <section className="pane" aria-label="Conversation thread">
        <div className="pane-head">
          <h2>{active?.title || "Thread"}</h2>
          {active ? <StatusPills pills={activePills} /> : <span className="list-meta">No conversation</span>}
        </div>
        <div className="thread" ref={threadRef}>
          {active && messages.length === 0 && !busy ? (
            <div className="thread-starter">
              <p>Tell Homerun the brief:</p>
              <ul>
                <li>
                  <strong>Offer</strong> — what you sell
                </li>
                <li>
                  <strong>Audience</strong> — who it is for
                </li>
                <li>
                  <strong>CTA</strong> — the one action
                </li>
              </ul>
            </div>
          ) : null}
          {messages.map((message) => (
            <div
              key={message.id}
              className={`bubble ${message.role}`}
              dir={isHebrew(message.content) ? "rtl" : "ltr"}
              lang={isHebrew(message.content) ? "he" : undefined}
            >
              <MessageBody content={message.content} />
            </div>
          ))}
          {busy ? (
            <div className="bubble pending" aria-live="polite">
              {progress?.steps?.length ? (
                <ol className="progress-steps">
                  {progress.steps.map((step) => (
                    <li key={step.stage} className={step.current ? "current" : "done"}>
                      <span>{step.label}</span>
                      {step.current && step.detail ? (
                        <span className="progress-detail">{step.detail}</span>
                      ) : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <>
                  <div>{progress?.label || "Working…"}</div>
                  {progress?.detail ? <div className="progress-detail">{progress.detail}</div> : null}
                </>
              )}
            </div>
          ) : null}
          {error ? <div className="bubble">{error}</div> : null}
        </div>
        <form className="composer" onSubmit={onSend}>
          <textarea
            ref={composerRef}
            value={draft}
            dir={isHebrew(draft) ? "rtl" : "ltr"}
            lang={isHebrew(draft) ? "he" : undefined}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Offer, audience, and CTA — or an edit to this page"
            disabled={!activeId}
          />
          <button className="primary-btn" type="submit" disabled={!activeId || busy}>
            {busy ? progress?.short || "Working" : "Send"}
          </button>
        </form>
      </section>

      <section className="pane" aria-label="Live preview">
        <div className="pane-head preview-head">
          <h2>Preview</h2>
          <div className="preview-toolbar">
            <button
              className="icon-btn"
              type="button"
              disabled={!previewUrl}
              onClick={() => setPreviewNonce((value) => value + 1)}
            >
              Reload
            </button>
            <button className="icon-btn" type="button" disabled={!previewUrl} onClick={onCopyLink}>
              {copyNote || "Copy link"}
            </button>
            {previewUrl ? (
              <a className="toolbar-link" href={previewUrl} target="_blank" rel="noopener noreferrer">
                Open
              </a>
            ) : (
              <button className="icon-btn" type="button" disabled>
                Open
              </button>
            )}
            <button
              className={`icon-btn${previewWidth === "desktop" ? " pressed" : ""}`}
              type="button"
              aria-pressed={previewWidth === "desktop"}
              onClick={() => setPreviewWidth("desktop")}
            >
              Desktop
            </button>
            <button
              className={`icon-btn${previewWidth === "mobile" ? " pressed" : ""}`}
              type="button"
              aria-pressed={previewWidth === "mobile"}
              onClick={() => setPreviewWidth("mobile")}
            >
              Mobile
            </button>
          </div>
        </div>
        {previewUrl ? (
          <div className={`preview-wrap ${previewWidth}`}>
            <iframe className="preview-frame" title="Sales page preview" src={iframeSrc} />
          </div>
        ) : (
          <p className="preview-empty">Publish a page to see it here.</p>
        )}
      </section>
    </div>
  );
}
