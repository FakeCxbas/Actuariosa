import { createClient, SupabaseClient } from "@supabase/supabase-js";

let cachedClient: SupabaseClient | null = null;

/**
 * Retorna un cliente de Supabase configurado para operaciones de backend.
 * Utiliza SUPABASE_SERVICE_ROLE_KEY preferentemente para bypass de RLS en serverless,
 * o NEXT_PUBLIC_SUPABASE_ANON_KEY como respaldo.
 * Si las credenciales no están presentes, retorna null para permitir fallback en memoria.
 */
export function getSupabaseServerClient(): SupabaseClient | null {
  if (cachedClient) return cachedClient;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key || url.includes("tu-proyecto.supabase.co")) {
    return null;
  }

  try {
    cachedClient = createClient(url, key, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    });
    return cachedClient;
  } catch (err) {
    console.error("[Supabase] Error al inicializar cliente:", err);
    return null;
  }
}
