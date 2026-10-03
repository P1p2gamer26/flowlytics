// Django autentica por sesión: las peticiones van con cookie y, si escriben,
// con el token CSRF que Django dejó en esa misma cookie.
function csrf(): string {
  const par = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="));
  return par ? par.slice("csrftoken=".length) : "";
}

async function pedir<T>(ruta: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(ruta, {
    credentials: "same-origin",
    ...init,
    headers: { "X-CSRFToken": csrf(), ...(init.headers ?? {}) },
  });
  if (!r.ok) {
    const datos = await r.json().catch(() => ({}));
    throw new Error(datos.error ?? `La petición a ${ruta} falló (${r.status}).`);
  }
  return r.status === 204 ? (undefined as T) : ((await r.json()) as T);
}

export const get = <T,>(ruta: string) => pedir<T>(ruta);

export const borrar = (ruta: string) => pedir<void>(ruta, { method: "DELETE" });

export const post = <T,>(ruta: string, cuerpo?: unknown) =>
  pedir<T>(ruta, {
    method: "POST",
    // FormData pone su propio Content-Type con el boundary: no tocarlo.
    body: cuerpo instanceof FormData ? cuerpo : JSON.stringify(cuerpo ?? {}),
    headers: cuerpo instanceof FormData ? {} : { "Content-Type": "application/json" },
  });

export const pedirPut = <T,>(ruta: string, cuerpo: unknown) =>
  pedir<T>(ruta, { method: "PUT", body: JSON.stringify(cuerpo),
                   headers: { "Content-Type": "application/json" } });

