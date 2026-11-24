export function obterUrlApi() {
  return (import.meta.env.VITE_RADARLEAD_API_URL?.trim() || 'http://127.0.0.1:8000').replace(/\/+$/, '')
}
