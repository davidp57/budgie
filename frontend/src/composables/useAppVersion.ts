/**
 * Singleton composable that fetches the backend version once and exposes it
 * as a shared reactive ref. Multiple callers share the same ref and the HTTP
 * request is made only once.
 */
import { ref } from 'vue'
import client from '@/api/client'

const appVersion = ref('')
let fetched = false

export function useAppVersion(): typeof appVersion {
  if (!fetched) {
    fetched = true
    client
      .get<{ version: string }>('/api/health')
      .then(({ data }) => {
        appVersion.value = data.version
      })
      .catch(() => {
        // health endpoint not available — silently ignore
      })
  }
  return appVersion
}
