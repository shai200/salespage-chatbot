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

test('GET /health returns the expected status payload', async () => {
  const { server, baseUrl } = await startServer();

  try {
    const response = await fetch(`${baseUrl}/health`);
    const data = await response.json();

    assert.equal(response.status, 200);
    assert.deepEqual(data, { status: 'ok' });
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

test('POST /api/chat rejects blank messages', async () => {
  const { server, baseUrl } = await startServer();

  try {
    const response = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '   ' }),
    });
    const data = await response.json();

    assert.equal(response.status, 400);
    assert.equal(data.error, 'The "message" field is required.');
  } finally {
    await stopServer(server);
  }
});

test('POST /api/chat rejects non-string messages', async () => {
  const { server, baseUrl } = await startServer();

  try {
    const response = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 123 }),
    });
    const data = await response.json();

    assert.equal(response.status, 400);
    assert.equal(data.error, 'The "message" field is required.');
  } finally {
    await stopServer(server);
  }
});

test('POST /api/chat rejects oversized request bodies', async () => {
  const { server, baseUrl } = await startServer();

  try {
    const oversizedResponse = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'x'.repeat(20000) }),
    });
    const oversizedData = await oversizedResponse.json();

    assert.equal(oversizedResponse.status, 413);
    assert.equal(oversizedData.error, 'Request body too large');

    const normalResponse = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'pricing details' }),
    });
    const normalData = await normalResponse.json();

    assert.equal(normalResponse.status, 200);
    assert.match(normalData.reply, /\$49\/month/);
  } finally {
    await stopServer(server);
  }
});
