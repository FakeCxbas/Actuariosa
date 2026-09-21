import { NextRequest, NextResponse } from "next/server";
import { getGlobalStore, addLeadToStore, updateLeadStatus } from "@/lib/data-store";

export const dynamic = "force-dynamic";

export async function GET() {
  const store = getGlobalStore();
  return NextResponse.json({
    ok: true,
    leads: store.leads_respuestas,
    total: store.leads_respuestas.length,
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    if (!body.empresa || !body.correo) {
      return NextResponse.json(
        { ok: false, error: "Empresa y correo son obligatorios." },
        { status: 400 }
      );
    }

    const created = addLeadToStore({
      empresa: body.empresa,
      correo: body.correo,
      ruc: body.ruc || "",
      provincia: body.provincia || "GUAYAS",
      fecha_contacto: body.fecha_contacto || new Date().toISOString().slice(0, 10),
      estado: body.estado || "Positivo / Interesado",
      servicio_interes: body.servicio_interes || "Jubilación Patronal / NIC 19",
      notas: body.notas || "",
    });

    return NextResponse.json({
      ok: true,
      mensaje: "Respuesta de empresa registrada exitosamente.",
      lead: created,
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { ok: false, error: `Error registrando lead: ${errorMsg}` },
      { status: 500 }
    );
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json();
    if (!body.id || !body.estado) {
      return NextResponse.json(
        { ok: false, error: "ID de lead y nuevo estado son obligatorios." },
        { status: 400 }
      );
    }

    const ok = updateLeadStatus(body.id, body.estado, body.notas);
    if (!ok) {
      return NextResponse.json(
        { ok: false, error: "Lead no encontrado." },
        { status: 404 }
      );
    }

    return NextResponse.json({
      ok: true,
      mensaje: "Estado del lead actualizado correctamente.",
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { ok: false, error: `Error actualizando lead: ${errorMsg}` },
      { status: 500 }
    );
  }
}
