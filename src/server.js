const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { generateReply } = require('./chatbot');

const publicDir = path.join(__dirname, '..', 'public');

const contentTypes = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
};

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(payload));
}

function serveStatic(response, fileName) {
  const filePath = path.join(publicDir, fileName);
  const extension = path.extname(filePath);

  fs.readFile(filePath, (error, content) => {
    if (error) {
      response.writeHead(404);
      response.end('Not found');
      return;
    }

    response.writeHead(200, { 'Content-Type': contentTypes[extension] || 'text/plain; charset=utf-8' });
    response.end(content);
  });
}

function createServer() {
  return http.createServer((request, response) => {
    if (request.method === 'GET' && request.url === '/health') {
      sendJson(response, 200, { status: 'ok' });
      return;
    }

    if (request.method === 'POST' && request.url === '/api/chat') {
      let body = '';
      request.on('data', (chunk) => {
        body += chunk;
      });
      request.on('end', () => {
        try {
          const parsed = JSON.parse(body || '{}');
          if (typeof parsed.message !== 'string') {
            sendJson(response, 400, { error: 'The "message" field is required.' });
            return;
          }
          sendJson(response, 200, { reply: generateReply(parsed.message) });
        } catch {
          sendJson(response, 400, { error: 'Invalid JSON payload' });
        }
      });
      return;
    }

    if (request.method === 'GET' && (request.url === '/' || request.url === '/index.html')) {
      serveStatic(response, 'index.html');
      return;
    }

    if (request.method === 'GET' && request.url === '/styles.css') {
      serveStatic(response, 'styles.css');
      return;
    }

    if (request.method === 'GET' && request.url === '/client.js') {
      serveStatic(response, 'client.js');
      return;
    }

    response.writeHead(404);
    response.end('Not found');
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT || 3000);
  createServer().listen(port, () => {
    process.stdout.write(`Server running on http://localhost:${port}\n`);
  });
}

module.exports = { createServer };
