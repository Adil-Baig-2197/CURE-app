export const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function errorMessage(response: Response, fallback: string): Promise<string> {
  const body: unknown = await response.json().catch(() => ({}));
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => {
        if (typeof item === "string") return item;
        if (typeof item === "object" && item !== null && "msg" in item && typeof item.msg === "string") {
          const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.join(" → ") : "";
          return loc ? `${loc}: ${item.msg}` : item.msg;
        }
        return "Invalid request";
      }).join("; ");
    }
  }
  return fallback;
}

export async function request<T = unknown>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: { ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (!response.ok) throw new Error(await errorMessage(response, "Request failed"));
  return response.json() as Promise<T>;
}

export async function requestBlob(path: string, token: string): Promise<Blob> {
  const response = await fetch(`${baseUrl}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(await errorMessage(response, "Download failed"));
  return response.blob();
}
