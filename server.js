require('dotenv').config();

const express = require('express');
const session = require('express-session');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 34343;
const DATA_FILE = path.join(__dirname, 'data', 'content.json');

app.use(express.json());
app.use(express.static(__dirname, { index: 'index.html' }));
app.use(session({
  secret: process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex'),
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 24 * 60 * 60 * 1000 } // 24 hours
}));

function readContent() {
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function writeContent(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

function generateId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

const requireAuth = (req, res, next) => {
  if (req.session.authenticated) return next();
  res.status(401).json({ error: 'Unauthorized' });
};

// --- Auth routes ---

app.post('/api/auth/login', (req, res) => {
  const { password } = req.body;
  const adminPassword = process.env.ADMIN_PASSWORD;

  if (!adminPassword) {
    return res.status(500).json({ error: 'Admin password not configured. Set ADMIN_PASSWORD in your .env file.' });
  }

  const inputBuf = Buffer.from(password || '');
  const storedBuf = Buffer.from(adminPassword);

  // Constant-time comparison to avoid timing attacks
  if (inputBuf.length === storedBuf.length && crypto.timingSafeEqual(inputBuf, storedBuf)) {
    req.session.authenticated = true;
    res.json({ success: true });
  } else {
    res.status(401).json({ error: 'Invalid password' });
  }
});

app.post('/api/auth/logout', (req, res) => {
  req.session.destroy();
  res.json({ success: true });
});

app.get('/api/auth/check', (req, res) => {
  res.json({ authenticated: !!req.session.authenticated });
});

// --- Content routes ---

app.get('/api/content', (req, res) => {
  res.json(readContent());
});

// Add a card to a section
app.post('/api/content/:section', requireAuth, (req, res) => {
  const { section } = req.params;
  const content = readContent();

  if (!content[section]) {
    return res.status(400).json({ error: `Unknown section: ${section}` });
  }

  const prefixes = { projects: 'proj', articles: 'art', presentations: 'pres', videos: 'vid', shop: 'shop' };
  const card = { id: generateId(prefixes[section] || section), ...req.body };
  content[section].push(card);
  writeContent(content);
  res.json({ success: true, card });
});

// Update a card
app.put('/api/content/:section/:id', requireAuth, (req, res) => {
  const { section, id } = req.params;
  const content = readContent();

  if (!content[section]) {
    return res.status(400).json({ error: `Unknown section: ${section}` });
  }

  const idx = content[section].findIndex(c => c.id === id);
  if (idx === -1) return res.status(404).json({ error: 'Card not found' });

  content[section][idx] = { ...content[section][idx], ...req.body, id };
  writeContent(content);
  res.json({ success: true, card: content[section][idx] });
});

// Delete a card
app.delete('/api/content/:section/:id', requireAuth, (req, res) => {
  const { section, id } = req.params;
  const content = readContent();

  if (!content[section]) {
    return res.status(400).json({ error: `Unknown section: ${section}` });
  }

  const idx = content[section].findIndex(c => c.id === id);
  if (idx === -1) return res.status(404).json({ error: 'Card not found' });

  content[section].splice(idx, 1);
  writeContent(content);
  res.json({ success: true });
});

// Reorder cards in a section
app.put('/api/content/:section', requireAuth, (req, res) => {
  const { section } = req.params;
  const content = readContent();

  if (!content[section]) {
    return res.status(400).json({ error: `Unknown section: ${section}` });
  }

  if (!Array.isArray(req.body)) {
    return res.status(400).json({ error: 'Expected an array' });
  }

  content[section] = req.body;
  writeContent(content);
  res.json({ success: true });
});

// Serve admin panel
app.get('/admin', (req, res) => {
  res.sendFile(path.join(__dirname, 'admin.html'));
});

app.listen(PORT, () => {
  console.log(`BardSec server running at http://localhost:${PORT}`);
  console.log(`Admin panel at http://localhost:${PORT}/admin`);
});
