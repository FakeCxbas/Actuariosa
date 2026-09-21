import { NextRequest, NextResponse } from "next/server";
import { getLatestRelease, publishNewRelease, getGlobalStore } from "@/lib/data-store";

export const dynamic = "force-dynamic";

function compareSemver(v1: string, v2: string): number {
  const p1 = (v1 || "").replace(/[^0-9.]/g, "").split(".").map(Number);
  const p2 = (v2 || "").replace(/[^0-9.]/g, "").split(".").map(Number);
  for (let i = 0; i < Math.max(p1.length, p2.length); i++) {
    const num1 = p1[i] || 0;
    const num2 = p2[i] || 0;
    if (num1 > num2) return 1;
    if (num1 < num2) return -1;
  }
  return 0;
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const clientVersion = searchParams.get("client_version") || searchParams.get("current_version") || "2.0.0";
    const release = getLatestRelease();
    const isOutdated = compareSemver(release.version, clientVersion) > 0;
    const store = getGlobalStore();

    return NextResponse.json({
      ok: true,
      client_version: clientVersion,
      latest_version: release.version,
      outdated: isOutdated,
      mandatory: release.mandatory,
      release,
      historial: store.historial_versiones || [release],
      timestamp: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    if (!body || !body.version) {
      return NextResponse.json(
        { ok: false, error: "El campo 'version' es obligatorio (ej: 2.1.0)." },
        { status: 400 }
      );
    }

    const changelogArray = Array.isArray(body.changelog)
      ? body.changelog
      : typeof body.changelog === "string"
      ? body.changelog.split("\n").map((s: string) => s.trim()).filter(Boolean)
      : ["Actualización general de estabilidad y nuevas funciones."];

    const release = publishNewRelease({
      version: body.version.trim(),
      title: body.title || `Actualización v${body.version.trim()}`,
      release_date: body.release_date || new Date().toISOString().slice(0, 10),
      mandatory: Boolean(body.mandatory),
      min_version: body.min_version || "2.0.0",
      changelog: changelogArray,
      download_url: body.download_url || `https://actuariosa.com/updates/mxcorreo-${body.version.trim()}.tar.gz`,
      package_size: body.package_size || "4.2 MB",
    });

    return NextResponse.json({
      ok: true,
      mensaje: `¡Versión v${release.version} lanzada exitosamente a todos los clientes!`,
      release,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}
