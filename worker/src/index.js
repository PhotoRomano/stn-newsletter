const ALLOWED_ORIGINS = new Set([
  'https://stnicholasphilly.org',
  'https://www.stnicholasphilly.org',
  'https://photoromano.github.io',
]);

const PUBLICATION_ID = 'pub_3d3143a5-5814-440b-97d6-3445e4e2ef7c';

function corsHeaders(origin) {
  const headers = {
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Vary': 'Origin',
  };
  if (ALLOWED_ORIGINS.has(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
  }
  return headers;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const headers = corsHeaders(origin);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ ok: false, error: 'Method not allowed' }), {
        status: 405,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    if (!ALLOWED_ORIGINS.has(origin)) {
      return new Response(JSON.stringify({ ok: false, error: 'Origin not allowed' }), {
        status: 403,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return new Response(JSON.stringify({ ok: false, error: 'Invalid JSON' }), {
        status: 400,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    const email = (body.email || '').trim();
    const firstName = (body.first_name || '').trim();
    const lastName = (body.last_name || '').trim();

    if (!email || !email.includes('@') || !firstName || !lastName) {
      return new Response(JSON.stringify({ ok: false, error: 'Missing required fields' }), {
        status: 400,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    const payload = {
      email,
      first_name: firstName,
      last_name: lastName,
      utm_source: body.utm_source || 'website',
      utm_medium: body.utm_medium || 'organic',
      send_welcome_email: body.send_welcome_email !== false,
    };
    if (Array.isArray(body.custom_fields) && body.custom_fields.length) {
      payload.custom_fields = body.custom_fields;
    }

    const beehiivRes = await fetch(
      `https://api.beehiiv.com/v2/publications/${PUBLICATION_ID}/subscriptions`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${env.BEEHIIV_API_KEY}`,
        },
        body: JSON.stringify(payload),
      }
    );

    if (beehiivRes.ok) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    const errText = await beehiivRes.text();
    return new Response(JSON.stringify({ ok: false, error: 'Beehiiv rejected the request', detail: errText }), {
      status: 502,
      headers: { ...headers, 'Content-Type': 'application/json' },
    });
  },
};
