async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || payload.error || detail;
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export function listConversations() {
  return request("/api/conversations");
}

export function createConversation() {
  return request("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title: "Untitled page" }),
  });
}

export function getConversation(id) {
  return request(`/api/conversations/${id}`);
}

function parseSseBlock(block) {
  let event = "message";
  const dataLines = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  const raw = dataLines.join("\n");
  return { event, data: raw ? JSON.parse(raw) : null };
}

export async function sendMessage(id, content, onProgress) {
  const response = await fetch(`/api/conversations/${id}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || payload.error || detail;
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("text/event-stream")) {
    return response.json();
  }
  if (!response.body) {
    throw new Error("No progress stream from studio");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let donePayload = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      if (!part.trim()) {
        continue;
      }
      const parsed = parseSseBlock(part);
      if (parsed.event === "progress" && parsed.data && onProgress) {
        onProgress(parsed.data);
      } else if (parsed.event === "done") {
        donePayload = parsed.data;
      } else if (parsed.event === "error") {
        throw new Error(parsed.data?.detail || "Generation failed");
      }
    }
  }
  if (buffer.trim()) {
    const parsed = parseSseBlock(buffer);
    if (parsed.event === "done") {
      donePayload = parsed.data;
    } else if (parsed.event === "error") {
      throw new Error(parsed.data?.detail || "Generation failed");
    }
  }
  if (!donePayload) {
    throw new Error("Generation finished without a reply");
  }
  return donePayload;
}
