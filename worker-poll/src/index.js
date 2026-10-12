// stnicholas-social-poll: Social Night activity poll (closed) + RSVP headcount view.
// The RSVP data is written by the stnicholas-social-rsvp worker into the shared RSVPS KV;
// it is surfaced here as a pseudo-poll so the existing /classifieds-admin "Poll Votes"
// panel (same admin token) shows it with no page change.
const POLLS = {
  "parish-social-2026-10-17": ["movie-night", "bingo-night", "game-night", "fellowship-social", "other"]
};
const RSVP_EVENT = "parish-social-2026-10-17";
const RSVP_POLL_ID = "Social Night RSVP headcount (people expected)";
const RSVP_ACTIVITIES = {
  "movie": "Movie (2-4 PM)",
  "games": "Informal games (4-5 PM)",
  "kids-karaoke": "Kids karaoke (5-7 PM)",
  "young-adults-karaoke": "Young adults karaoke (7-10 PM)"
};
const WRITEIN_MAX_LEN = 200;
const WRITEIN_MAX_STORED = 200;
const ALLOWED_ORIGINS = new Set([
  "https://stnicholasphilly.org",
  "https://www.stnicholasphilly.org",
  "https://photoromano.github.io"
]);
const VOTE_DEDUPE_TTL_SECONDS = 60 * 60 * 24 * 14;
function corsHeaders(origin) {
  const headers = {
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    Vary: "Origin"
  };
  if (ALLOWED_ORIGINS.has(origin)) headers["Access-Control-Allow-Origin"] = origin;
  return headers;
}
function isAdmin(request, env) {
  const auth = request.headers.get("Authorization") || "";
  return Boolean(env.ADMIN_TOKEN) && auth === `Bearer ${env.ADMIN_TOKEN}`;
}
function json(data, status, headers) {
  return new Response(JSON.stringify(data), { status, headers: { ...headers, "Content-Type": "application/json" } });
}
async function hashIp(ip) {
  const data = new TextEncoder().encode(ip);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
async function getCounts(env, poll) {
  const options = POLLS[poll];
  const counts = {};
  await Promise.all(options.map(async (option) => {
    const raw = await env.VOTES.get(`count:${poll}:${option}`);
    counts[option] = raw ? parseInt(raw, 10) : 0;
  }));
  return counts;
}
async function getRsvpView(env) {
  const list = await env.RSVPS.list({ prefix: `rsvp:${RSVP_EVENT}:` });
  const raw = await Promise.all(list.keys.map((k) => env.RSVPS.get(k.name)));
  const rows = raw.filter(Boolean).map((r) => JSON.parse(r)).sort((a, b) => a.ts.localeCompare(b.ts));
  const seg = (r) => ({ k: r.kids ?? 0, y: r.young_adults ?? 0, a: r.adults ?? r.party_size ?? 0 });
  const per = Object.fromEntries(Object.keys(RSVP_ACTIVITIES).map((a) => [a, { k: 0, y: 0, a: 0 }]));
  const tot = { k: 0, y: 0, a: 0 };
  for (const r of rows) {
    const g = seg(r);
    tot.k += g.k; tot.y += g.y; tot.a += g.a;
    for (const act of r.activities) if (per[act]) { per[act].k += g.k; per[act].y += g.y; per[act].a += g.a; }
  }
  const counts = {};
  for (const [act, label] of Object.entries(RSVP_ACTIVITIES)) counts[label] = per[act].k + per[act].y + per[act].a;
  counts["ALL RSVPs: kids"] = tot.k;
  counts["ALL RSVPs: young adults"] = tot.y;
  counts["ALL RSVPs: adults"] = tot.a;
  const fmt = (g) => `${g.k} kids, ${g.y} young adults, ${g.a} adults`;
  const lines = Object.entries(RSVP_ACTIVITIES).map(([act, label]) => `${label}: ${fmt(per[act])}`);
  const households = rows.map((r) => { const g = seg(r); return `${r.name} \u2014 ${fmt(g)} \u2014 ${r.activities.map((a) => RSVP_ACTIVITIES[a] || a).join(", ")}`; });
  return { counts, writeins: [...lines, "\u2014 Households \u2014", ...households] };
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const headers = corsHeaders(origin);
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (!ALLOWED_ORIGINS.has(origin)) return json({ ok: false, error: "Origin not allowed" }, 403, headers);
    if (request.method === "GET" && url.pathname === "/results") {
      if (!isAdmin(request, env)) return json({ ok: false, error: "Unauthorized" }, 401, headers);
      const poll = url.searchParams.get("poll") || "";
      if (poll === RSVP_POLL_ID) {
        const v = await getRsvpView(env);
        return json({ ok: true, poll, counts: v.counts, writeins: v.writeins }, 200, headers);
      }
      if (!POLLS[poll]) return json({ ok: false, error: "Unknown poll" }, 404, headers);
      const counts = await getCounts(env, poll);
      const writeinsRaw = await env.VOTES.get(`writeins:${poll}`);
      const writeins = writeinsRaw ? JSON.parse(writeinsRaw) : [];
      return json({ ok: true, poll, counts, writeins }, 200, headers);
    }
    if (request.method === "GET" && url.pathname === "/admin/polls") {
      if (!isAdmin(request, env)) return json({ ok: false, error: "Unauthorized" }, 401, headers);
      return json({ ok: true, polls: [RSVP_POLL_ID, ...Object.keys(POLLS)] }, 200, headers);
    }
    if (request.method === "POST" && url.pathname === "/vote") {
      let body;
      try { body = await request.json(); } catch (e) { return json({ ok: false, error: "Invalid JSON" }, 400, headers); }
      const poll = (body.poll || "").trim();
      const option = (body.option || "").trim();
      if (!POLLS[poll] || !POLLS[poll].includes(option)) return json({ ok: false, error: "Unknown poll or option" }, 400, headers);
      let writein = "";
      if (option === "other") {
        writein = (body.writein || "").trim().slice(0, WRITEIN_MAX_LEN);
        if (!writein) return json({ ok: false, error: "Write-in text required" }, 400, headers);
      }
      const ip = request.headers.get("CF-Connecting-IP") || "";
      if (ip) {
        const ipHash = await hashIp(ip);
        const dedupeKey = `voted:${poll}:${ipHash}`;
        const already = await env.VOTES.get(dedupeKey);
        if (already) {
          const counts2 = await getCounts(env, poll);
          return json({ ok: true, poll, counts: counts2, duplicate: true }, 200, headers);
        }
        await env.VOTES.put(dedupeKey, "1", { expirationTtl: VOTE_DEDUPE_TTL_SECONDS });
      }
      const countKey = `count:${poll}:${option}`;
      const current = await env.VOTES.get(countKey);
      const next = (current ? parseInt(current, 10) : 0) + 1;
      await env.VOTES.put(countKey, String(next));
      if (writein) {
        const writeinsKey = `writeins:${poll}`;
        const raw = await env.VOTES.get(writeinsKey);
        const list = raw ? JSON.parse(raw) : [];
        list.push(writein);
        while (list.length > WRITEIN_MAX_STORED) list.shift();
        await env.VOTES.put(writeinsKey, JSON.stringify(list));
      }
      const counts = await getCounts(env, poll);
      return json({ ok: true, poll, counts }, 200, headers);
    }
    return json({ ok: false, error: "Not found" }, 404, headers);
  }
};
