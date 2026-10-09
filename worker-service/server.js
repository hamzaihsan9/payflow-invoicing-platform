/**
 * PayFlow Pro - Node.js Microservice Worker
 * Handles asynchronous background event processing, webhook routing, and audit logs.
 * Written with native Node.js HTTP capabilities for zero-dependency execution.
 */

const http = require('http');
const PORT = process.env.PORT || 5001;

const eventStore = [];

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // Health Check
  if (url.pathname === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'healthy', worker: 'Node.js Event Engine', uptime: process.uptime() }));
    return;
  }

  // Get Recorded Events
  if (url.pathname === '/api/events' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ count: eventStore.length, events: eventStore.slice(-20) }));
    return;
  }

  // Receive Webhook Events from Python FastAPI
  if (url.pathname === '/api/events' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = JSON.parse(body);
        const record = {
          id: `EVT-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
          received_at: new Date().toISOString(),
          ...payload
        };
        eventStore.push(record);
        console.log(`[Node Worker] Processed Event: ${record.event} for Invoice: ${record.data?.invoice_number || 'N/A'}`);

        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ message: 'Event ingested successfully', event_id: record.id }));
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Malformed JSON payload' }));
      }
    });
    return;
  }

  // 404 Fallback
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Route not found' }));
});

server.listen(PORT, () => {
  console.log(`⚡ PayFlow Node.js Worker Service listening on port ${PORT}`);
});
