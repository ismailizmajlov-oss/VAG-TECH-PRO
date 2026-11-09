import * as wikipediaCandidates from "../../../lib/wikipedia-engine-candidates-db.cjs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const headers = {
  "Cache-Control": "private, no-store, max-age=0",
  "X-Content-Type-Options": "nosniff",
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  try {
    if (url.searchParams.get("summary") === "1") {
      return Response.json({ ok: true, summary: wikipediaCandidates.getSummary() }, { headers });
    }
    const query = url.searchParams.get("q") || "";
    const rawLimit = url.searchParams.get("limit") || "25";
    const limit = Number.parseInt(rawLimit, 10);
    if (!Number.isInteger(limit) || limit < 1 || limit > 50) {
      return Response.json({ error: "Лимит должен быть от 1 до 50." }, { status: 400, headers });
    }
    const rows = wikipediaCandidates.searchCandidates(query, limit);
    return Response.json({ ok: true, query: query.trim(), count: rows.length, rows }, { headers });
  } catch (error) {
    if (error instanceof TypeError) {
      return Response.json({ error: error.message }, { status: 400, headers });
    }
    return Response.json(
      { error: "Исследовательский набор кодов двигателей недоступен или не прошёл проверку целостности." },
      { status: 503, headers },
    );
  }
}
