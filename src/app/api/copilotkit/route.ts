import { NextResponse } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Point this to your Python agent base URL
const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:9000";
export async function POST(req: Request) {
  try {
    const url = new URL(req.url);
    // Build target: /<path>?<other query params>
    const path = url.searchParams.get("path") || "/";
    const qp = new URLSearchParams(url.searchParams);
    qp.delete("path"); // leave only extra params such as meeting_id
    const target = `${AGENT_URL}${path}${qp.toString() ? `?${qp}` : ""}`;
    const contentType = req.headers.get("content-type") || "";
  // debug
  console.debug("[copilotkit] proxy target ->", target, "content-type:", contentType);
    let upstreamRes: Response;
    if (contentType.includes("multipart/form-data")) {
      const form = await req.formData(); // rebuild so fetch sets boundary
      upstreamRes = await fetch(target, {
        method: "POST",
        body: form,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
    } else {
      const body = await req.text(); // works for JSON or empty
      upstreamRes = await fetch(target, {
        method: "POST",
        headers: { "Content-Type": contentType || "application/json" },
        body: body || undefined,
      });
    }
    const text = await upstreamRes.text();
  // log upstream status for diagnostics
  console.debug("[copilotkit] upstream status", upstreamRes.status, "ok", upstreamRes.ok);

    if (!upstreamRes.ok) {
      // try parse json for structured error
      try {
        const parsed = JSON.parse(text);
        return NextResponse.json({ ok: false, status: upstreamRes.status, body: parsed }, { status: upstreamRes.status });
      } catch {
        return NextResponse.json({ ok: false, status: upstreamRes.status, body: text }, { status: upstreamRes.status });
      }
    }

    try {
      return NextResponse.json(JSON.parse(text), { status: upstreamRes.status });
    } catch {
      return new NextResponse(text, {
        status: upstreamRes.status,
        headers: {
          "content-type": upstreamRes.headers.get("content-type") || "text/plain",
        },
      });
    }
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message ?? "proxy error" }, { status: 500 });
  }
}
