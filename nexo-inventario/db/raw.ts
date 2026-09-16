import { env } from 'cloudflare:workers';
export function database() {
  if (!env.DB) throw new Error('Base de datos no disponible');
  return env.DB as D1Database;
}
