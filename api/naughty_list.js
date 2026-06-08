// api/naughty-list.js — Vercel serverless endpoint
// Serves the public EVEZ NPC naughty list from GitHub raw + Ably history
// Deploy: vercel --prod from evez-agentnet root

const https = require('https');

const GITHUB_RAW = 'https://raw.githubusercontent.com/EvezArt/evez-agentnet/main/honeypot/output/naughty_list.json';
const ABLY_KEY   = process.env.ABLY_API_KEY || '';

function fetchUrl(url, headers = {}) {
  return new Promise((resolve, reject) => {
    const opts = { headers: { 'User-Agent': 'evez-os/2.0', ...headers } };
    https.get(url, opts, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { resolve(null); }
      });
    }).on('error', reject);
  });
}

function fetchAblyHistory(channel) {
  if (!ABLY_KEY) return Promise.resolve([]);
  const [keyId, keySecret] = ABLY_KEY.split(':');
  const token = Buffer.from(`${keyId}:${keySecret}`).toString('base64');
  const url = `https://rest.ably.io/channels/${encodeURIComponent(channel)}/messages?limit=50&direction=backwards`;
  return fetchUrl(url, { Authorization: `Basic ${token}` })
    .then(data => Array.isArray(data) ? data.map(m => {
      try { return typeof m.data === 'string' ? JSON.parse(m.data) : m.data; }
      catch { return null; }
    }).filter(Boolean) : [])
    .catch(() => []);
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Type', 'application/json');

  try {
    // fetch from GitHub raw (committed by watcher) + Ably history in parallel
    const [ghList, ablyList] = await Promise.all([
      fetchUrl(GITHUB_RAW).catch(() => []),
      fetchAblyHistory('evez-vcl-npc').catch(() => [])
    ]);

    const base    = Array.isArray(ghList)   ? ghList   : [];
    const overlay = Array.isArray(ablyList) ? ablyList : [];

    // merge — deduplicate by fingerprint
    const seen = new Set();
    const merged = [...overlay, ...base].filter(r => {
      if (!r || !r.npc_class) return false;
      const key = r.fingerprint || JSON.stringify(r);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // summary stats
    const stats = {};
    merged.forEach(r => { stats[r.npc_class] = (stats[r.npc_class] || 0) + 1; });
    const hostile = merged.filter(r => ['hostile', 'confirmed'].includes(r.tier)).length;

    res.status(200).json({
      generated_at:   new Date().toISOString(),
      total:          merged.length,
      hostile_actors: hostile,
      stats,
      records:        merged.slice(0, 200)
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};
