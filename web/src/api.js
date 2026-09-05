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
    body: JSON.stringify({ title: "New sales page" }),
  });
}

export function getConversation(id) {
  return request(`/api/conversations/${id}`);
}

export function sendMessage(id, content) {
  return request(`/api/conversations/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}
