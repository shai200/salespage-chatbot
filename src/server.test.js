const test = require('node:test');
const assert = require('node:assert/strict');
const { createServer } = require('./server');

function startServer() {
  return new Promise((resolve) => {
    const server = createServer();
    server.listen(0, () => {
      const { port } = server.address();
      resolve({
        server,
        baseUrl: `http://127.0.0.1:${port}`,
      });
    });
  });
}

function stopServer(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

test('POST /api/chat returns a chatbot reply', async () => {
  const { server, baseUrl } = await startServer();

  try {
    const response = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'Can I book a demo?' }),
    });
    const data = await response.json();

    assert.equal(response.status, 200);
    assert.match(data.reply, /personalized demo/i);
  } finally {
    await stopServer(server);
  }
});

test('POST /api/chat rejects malformed JSON', async () => {
  const { server, baseUrl } = await startServer();

  try {
    const response = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{',
    });
    const data = await response.json();

    assert.equal(response.status, 400);
    assert.equal(data.error, 'Invalid JSON payload');
  } finally {
    await stopServer(server);
  }
});

test('POST /api/chat requires a message field', async () => {
  const { server, baseUrl } = await startServer();

  try {
    const response = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await response.json();

    assert.equal(response.status, 400);
    assert.equal(data.error, 'The "message" field is required.');
  } finally {
    await stopServer(server);
  }
});
