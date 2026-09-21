import { NextRequest, NextResponse } from "next/server";
import { getGlobalStore, updateGlobalStore } from "@/lib/data-store";

export const dynamic = "force-dynamic";

export async function GET() {
  const data = getGlobalStore();
  return NextResponse.json({
    ok: true,
    data,
    timestamp: new Date().toISOString(),
  });
}

export async function POST(req: NextRequest) {
  try {
    const authHeader = req.headers.get("authorization");
    // Token opcional configurable en variables de entorno o clave por defecto
    const expectedToken = process.env.SYNC_API_KEY || "actuariosa-telemetry-key-2026";
    if (authHeader && !authHeader.includes(expectedToken) && process.env.NODE_ENV === "production" && process.env.ENFORCE_SYNC_AUTH === "true") {
      return NextResponse.json(
        { ok: false, error: "No autorizado. Token de telemetría inválido." },
        { status: 401 }
      );
    }

    const body = await req.json();
    if (!body || typeof body !== "object") {
      return NextResponse.json(
        { ok: false, error: "Cuerpo de solicitud inválido." },
        { status: 400 }
      );
    }

    const updated = updateGlobalStore({
      fuente: body.fuente || "Sincronización Externa",
      resumen_general: body.resumen_general,
      distribucion_provincias: body.distribucion_provincias,
      top_dominios: body.top_dominios,
      campanas: body.campanas,
    });

    return NextResponse.json({
      ok: true,
      mensaje: "Telemetría sincronizada exitosamente con el Panel de Actuariosa.",
      resumen: updated.resumen_general,
      ultima_actualizacion: updated.ultima_actualizacion,
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { ok: false, error: `Error procesando sincronización: ${errorMsg}` },
      { status: 500 }
    );
  }
}
