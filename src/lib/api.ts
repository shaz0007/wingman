const configuredApiBaseUrl = (
  import.meta.env.vite_api_base_url || import.meta.env.VITE_API_BASE_URL
)?.trim();

if (import.meta.env.PROD && !configuredApiBaseUrl) {
  throw new Error(
    "vite_api_base_url is missing. Set it in the Vercel project environment variables and redeploy.",
  );
}

// Local development remains zero-configuration; production must use the deployed API URL.
const apiBaseUrl = (configuredApiBaseUrl || "http://localhost:8000").replace(/\/+$/, "");

export function apiUrl(path: string): string {
  return `${apiBaseUrl}/${path.replace(/^\/+/, "")}`;
}
