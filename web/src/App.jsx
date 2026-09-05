import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ApiError,
  billingStatus,
  createConversation,
  getConversation,
  getMe,
  listConversations,
  logout,
  sendMessage,
  startCheckout,
} from "./api.js";

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
  const [user, setUser] = useState(undefined);
  const [billing, setBilling] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState("");
  const [jobs, setJobs] = useState({});
  const [jobErrors, setJobErrors] = useState({});
  const [error, setError] = useState("");
  const [previewNonce, setPreviewNonce] = useState(0);
  const [previewWidth, setPreviewWidth] = useState("desktop");
  const [copyNote, setCopyNote] = useState("");
  const threadRef = useRef(null);
  const composerRef = useRef(null);
  const activeIdRef = useRef(null);
  activeIdRef.current = activeId;

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
    getMe()
      .then((payload) => {
        setUser(payload.user || null);
        if (payload.user) {
          return Promise.all([refreshList(), billingStatus().then(setBilling)]);
        }
        return null;
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const node = threadRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [active?.messages, jobs]);

  useEffect(() => {
    if (active && (active.messages || []).length === 0 && !jobs[active.id]) {
      composerRef.current?.focus();
    }
  }, [activeId, active?.messages?.length, jobs]);

  async function onNew() {
    setError("");
    try {
      const created = await createConversation();
      const status = await billingStatus();
      setBilling(status);
      await refreshList(created.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setError(err.payload?.message || err.message || "A card is required to create another page.");
        const checkout = await startCheckout();
        if (checkout?.url) {
          window.location.assign(checkout.url);
          return;
        }
        if (checkout?.ready) {
          const created = await createConversation();
          setBilling(await billingStatus());
          await refreshList(created.id);
          return;
        }
        return;
      }
      setError(err.message);
    }
  }

  async function onSignOut() {
    await logout();
    setUser(null);
    setConversations([]);
    setActive(null);
    setActiveId(null);
    setBilling(null);
  }

  async function onSelect(id) {
    setError("");
    setActiveId(id);
    setActive(await getConversation(id));
  }

  async function onSend(event) {
    event.preventDefault();
    const sentId = activeId;
    if (!sentId || !draft.trim() || jobs[sentId]) {
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
    setJobErrors((current) => {
      const next = { ...current };
      delete next[sentId];
      return next;
    });
    setJobs((current) => ({
      ...current,
      [sentId]: {
        progress: {
          label: "Working…",
          detail: "Starting the page pipeline",
          short: "Working",
          steps: [],
        },
      },
    }));
    setActive((current) =>
      current?.id === sentId
        ? { ...current, messages: [...(current.messages || []), optimistic] }
        : current,
    );
    try {
      await sendMessage(sentId, text, (event) => {
        setJobs((current) => {
          const job = current[sentId];
          if (!job) {
            return current;
          }
          const step = {
            stage: event.stage,
            label: event.label,
            detail: event.detail,
            current: true,
          };
          const prior = (job.progress?.steps || []).map((item) => ({ ...item, current: false }));
          const without = prior.filter((item) => item.stage !== event.stage);
          return {
            ...current,
            [sentId]: {
              progress: {
                ...event,
                steps: [...without, step],
              },
            },
          };
        });
      });
      const rows = await listConversations();
      setConversations(rows);
      const latest = await getConversation(sentId);
      if (activeIdRef.current === sentId) {
        setActive(latest);
        setPreviewNonce((value) => value + 1);
      }
    } catch (err) {
      setJobErrors((current) => ({ ...current, [sentId]: err.message }));
    } finally {
      setJobs((current) => {
        const next = { ...current };
        delete next[sentId];
        return next;
      });
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
  const activeJob = activeId ? jobs[activeId] : null;
  const activeGenerating = Boolean(activeJob);
  const progress = activeJob?.progress || null;
  const threadError = (activeId && jobErrors[activeId]) || error;
  const activePills = useMemo(
    () => pagePills(active, activeGenerating),
    [active, activeGenerating],
  );

  if (user === undefined) {
    return (
      <div className="signin">
        <p>Loading…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="signin">
        <div className="signin-card">
          <strong>Homerun</strong>
          <p>Sign in with Google to create and manage your sales pages.</p>
          <a className="primary-btn" href="/auth/google">
            Sign in with Google
          </a>
        </div>
      </div>
    );
  }

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
        <div className="list-billing">
          <span>
            {billing
              ? `${billing.free_used} / ${billing.free_limit} free pages`
              : user.email}
          </span>
          <button className="icon-btn" type="button" onClick={onSignOut}>
            Sign out
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
                <StatusPills pills={pagePills(item, Boolean(jobs[item.id]))} />
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
          {active && messages.length === 0 && !activeGenerating ? (
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
          {activeGenerating ? (
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
          {threadError ? <div className="bubble">{threadError}</div> : null}
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
          <button className="primary-btn" type="submit" disabled={!activeId || activeGenerating}>
            {activeGenerating ? progress?.short || "Working" : "Send"}
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
