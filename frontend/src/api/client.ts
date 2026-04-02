import axios, { AxiosError } from 'axios'

// We import auth store lazily to avoid circular deps
let getAccessToken: () => string | null = () => null
let getRefreshToken: () => string | null = () => null
let setTokens: (a: string, r: string) => void = () => {}
let clearAuth: () => void = () => {}

export function initApiClient(
  accessTokenFn: () => string | null,
  refreshTokenFn: () => string | null,
  setTokensFn: (a: string, r: string) => void,
  clearAuthFn: () => void
) {
  getAccessToken = accessTokenFn
  getRefreshToken = refreshTokenFn
  setTokens = setTokensFn
  clearAuth = clearAuthFn
}

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach Bearer token
client.interceptors.request.use(config => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Refresh on 401
let isRefreshing = false
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach(p => {
    if (error) p.reject(error)
    else p.resolve(token!)
  })
  failedQueue = []
}

client.interceptors.response.use(
  res => res,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean }

    if (error.response?.status === 401 && !original?._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          if (original) {
            original.headers!['Authorization'] = `Bearer ${token}`
          }
          return client(original!)
        })
      }

      original!._retry = true
      isRefreshing = true

      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        clearAuth()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        })
        setTokens(data.access_token, data.refresh_token)
        client.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
        processQueue(null, data.access_token)
        if (original) {
          original.headers!['Authorization'] = `Bearer ${data.access_token}`
          return client(original)
        }
      } catch (err) {
        processQueue(err, null)
        clearAuth()
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default client
