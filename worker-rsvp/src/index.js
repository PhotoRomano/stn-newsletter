// Parish Social Night RSVP: collects name, party size and which of the day's
// events a household plans to attend, for headcount estimates.
const EVENTS = {
  'parish-social-2026-10-17': ['movie', 'games', 'kids-karaoke', 'young-adults-karaoke'],
};
const ALLOWED_ORIGINS = new Set([
  'https://stnicholasphilly.org',
  'https://www.stnicholasphilly.org',
  'https://photoromano.github.io',
]);
const MAX_PARTY = 30;

function cors(origin) {
  const h = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    Vary: 'Origin',
  };
  if (ALLOWED_ORIGINS.has(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}
const json = (d, s, h) => new Response(JSON.stringify(d), { status: s, headers: { ...h, 'Content-Type': 'application/json' } });
const isAdmin = (req, env) => Boolean(env.ADMIN_TOKEN) && (req.headers.get('Authorization') || '') === `Bearer ${env.ADMIN_TOKEN}`;

async function loadAll(env, event) {
  const list = await env.RSVPS.list({ prefix: `rsvp:${event}:` });
  const raw = await Promise.all(list.keys.map((k) => env.RSVPS.get(k.name)));
  const rows = raw.filter(Boolean).map((r) => JSON.parse(r));
  return rows.sort((a, b) => a.ts.localeCompare(b.ts));
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const headers = cors(origin);
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers });

    // Admin: totals + list. Bearer token, no Origin requirement (curl-friendly).
    if (request.method === 'GET' && url.pathname === '/results') {
      if (!isAdmin(request, env)) return json({ ok: false, error: 'Unauthorized' }, 401, headers);
      const event = url.searchParams.get('event') || '';
      if (!EVENTS[event]) return json({ ok: false, error: 'Unknown event' }, 404, headers);
      const rows = await loadAll(env, event);
      const headcount = Object.fromEntries(EVENTS[event].map((e) => [e, 0]));
      let households = rows.length;
      for (const r of rows) for (const e of r.activities) headcount[e] += r.party_size;
      return json({ ok: true, event, households, headcount, rsvps: rows }, 200, headers);
    }

    if (request.method === 'POST' && url.pathname === '/rsvp') {
      if (!ALLOWED_ORIGINS.has(origin)) return json({ ok: false, error: 'Origin not allowed' }, 403, headers);
      let b;
      try { b = await request.json(); } catch { return json({ ok: false, error: 'Invalid JSON' }, 400, headers); }
      const event = String(b.event || '').trim();
      if (!EVENTS[event]) return json({ ok: false, error: 'Unknown event' }, 400, headers);
      const name = String(b.name || '').trim().slice(0, 100);
      const partySize = parseInt(b.party_size, 10);
      const activities = Array.isArray(b.activities) ? [...new Set(b.activities.map(String))] : [];
      if (!name) return json({ ok: false, error: 'Name required' }, 400, headers);
      if (!Number.isInteger(partySize) || partySize < 1 || partySize > MAX_PARTY) return json({ ok: false, error: 'Party size 1-30 required' }, 400, headers);
      if (!activities.length || !activities.every((a) => EVENTS[event].includes(a))) return json({ ok: false, error: 'Pick at least one activity' }, 400, headers);
      const row = { name, party_size: partySize, activities, ts: new Date().toISOString() };
      // Same name re-submitting replaces their earlier RSVP (lets people fix a mistake).
      const key = `rsvp:${event}:${name.toLowerCase().replace(/\s+/g, ' ')}`;
      await env.RSVPS.put(key, JSON.stringify(row));
      return json({ ok: true }, 200, headers);
    }
    return json({ ok: false, error: 'Not found' }, 404, headers);
  },
};
