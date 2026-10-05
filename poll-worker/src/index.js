// St. Nicholas newsletter — lightweight event polls (e.g. Parish Social Night
// activity vote). One KV namespace, keys scoped per poll:
//   count:<poll>:<option>   -> integer vote count
//   voted:<poll>:<ip-hash>  -> "1" (TTL'd) -- best-effort same-network dedupe,
//                              not a security control; the real guard is the
//                              client's localStorage flag set after voting.
//
// POLLS below is the single source of truth for which poll/option
// combinations are accepted -- add a new entry here for each future event
// poll rather than accepting arbitrary option strings from the client.

const POLLS = {
  'parish-social-2026-10-17': [
    'movie-night',
    'bingo-night',
    'game-night',
    'fellowship-social',
  ],
};

const ALLOWED_ORIGINS = new Set([
  'https://stnicholasphilly.org',
  'https://www.stnicholasphilly.org',
  'https://photoromano.github.io',
]);

const VOTE_DEDUPE_TTL_SECONDS = 60 * 60 * 24 * 14; // 14 days

function corsHeaders(origin) {
  const headers = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    Vary: 'Origin',
  };
  if (ALLOWED_ORIGINS.has(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
  }
  return headers;
}

function json(data, status, headers) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...headers, 'Content-Type': 'application/json' },
  });
}

async function hashIp(ip) {
  const data = new TextEncoder().encode(ip);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function getCounts(env, poll) {
  const options = POLLS[poll];
  const counts = {};
  await Promise.all(
    options.map(async (option) => {
      const raw = await env.VOTES.get(`count:${poll}:${option}`);
      counts[option] = raw ? parseInt(raw, 10) : 0;
    }),
  );
  return counts;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const headers = corsHeaders(origin);
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers });
    }

    if (!ALLOWED_ORIGINS.has(origin)) {
      return json({ ok: false, error: 'Origin not allowed' }, 403, headers);
    }

    if (request.method === 'GET' && url.pathname === '/results') {
      const poll = url.searchParams.get('poll') || '';
      if (!POLLS[poll]) {
        return json({ ok: false, error: 'Unknown poll' }, 404, headers);
      }
      const counts = await getCounts(env, poll);
      return json({ ok: true, poll, counts }, 200, headers);
    }

    if (request.method === 'POST' && url.pathname === '/vote') {
      let body;
      try {
        body = await request.json();
      } catch (e) {
        return json({ ok: false, error: 'Invalid JSON' }, 400, headers);
      }

      const poll = (body.poll || '').trim();
      const option = (body.option || '').trim();

      if (!POLLS[poll] || !POLLS[poll].includes(option)) {
        return json({ ok: false, error: 'Unknown poll or option' }, 400, headers);
      }

      const ip = request.headers.get('CF-Connecting-IP') || '';
      if (ip) {
        const ipHash = await hashIp(ip);
        const dedupeKey = `voted:${poll}:${ipHash}`;
        const already = await env.VOTES.get(dedupeKey);
        if (already) {
          // Same network already voted in this poll -- still return current
          // counts so the UI can show a graceful "already counted" state
          // instead of erroring.
          const counts = await getCounts(env, poll);
          return json({ ok: true, poll, counts, duplicate: true }, 200, headers);
        }
        await env.VOTES.put(dedupeKey, '1', { expirationTtl: VOTE_DEDUPE_TTL_SECONDS });
      }

      const countKey = `count:${poll}:${option}`;
      const current = await env.VOTES.get(countKey);
      const next = (current ? parseInt(current, 10) : 0) + 1;
      await env.VOTES.put(countKey, String(next));

      const counts = await getCounts(env, poll);
      return json({ ok: true, poll, counts }, 200, headers);
    }

    return json({ ok: false, error: 'Not found' }, 404, headers);
  },
};
