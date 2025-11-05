/**
 * Authentication utilities with JWT token management and auto-refresh
 */

import { createAnonymousSession } from './api-client'

// Storage keys
const SESSION_TOKEN_KEY = 'session_token'
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_ID_KEY = 'user_id'
const CONSENT_GIVEN_KEY = 'consent_given'
const CONVERSATION_ID_KEY = 'conversation_id'

// Token constants
const ACCESS_TOKEN_EXPIRE_MINUTES = 15
const REFRESH_BEFORE_EXPIRE_MINUTES = 5 // Refresh 5 minutes before expiration

// Token refresh state
let refreshTimer: ReturnType<typeof setTimeout> | null = null
let isRefreshing = false
let refreshPromise: Promise<string> | null = null

/**
 * Get session token from storage or create new one
 */
export async function getSessionToken(): Promise<string> {
  if (typeof window === 'undefined') return ''

  let token = localStorage.getItem(SESSION_TOKEN_KEY)

  // If no token, create new anonymous session
  if (!token) {
    try {
      const session = await createAnonymousSession()
      token = session.session_token

      // Store token and user info
      localStorage.setItem(SESSION_TOKEN_KEY, token)
      if (session.user.id) {
        localStorage.setItem(USER_ID_KEY, session.user.id)
      }
    } catch (error) {
      console.error('Failed to create session:', error)
      // Fallback to local token
      token = `local_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`
      localStorage.setItem(SESSION_TOKEN_KEY, token)
    }
  }

  return token
}

/**
 * Clear session data
 */
export function clearSession(): void {
  if (typeof window === 'undefined') return

  localStorage.removeItem(SESSION_TOKEN_KEY)
  localStorage.removeItem(USER_ID_KEY)
  localStorage.removeItem(CONVERSATION_ID_KEY)
}

/**
 * Get user ID from storage
 */
export function getUserId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(USER_ID_KEY)
}

/**
 * Get consent status
 */
export function getConsentStatus(): boolean {
  if (typeof window === 'undefined') return false
  return localStorage.getItem(CONSENT_GIVEN_KEY) === 'true'
}

/**
 * Set consent status
 */
export function setConsentStatus(given: boolean): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(CONSENT_GIVEN_KEY, given.toString())
}

/**
 * Get conversation ID from storage
 */
export function getConversationId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(CONVERSATION_ID_KEY)
}

/**
 * Save conversation ID to storage
 */
export function saveConversationId(id: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(CONVERSATION_ID_KEY, id)
}

/**
 * Clear conversation (start new)
 */
export function clearConversation(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(CONVERSATION_ID_KEY)
}

/**
 * Check if user has valid session
 */
export function hasValidSession(): boolean {
  if (typeof window === 'undefined') return false
  return !!localStorage.getItem(SESSION_TOKEN_KEY)
}

// =============================================================================
// JWT Token Management
// =============================================================================

/**
 * Decode JWT token payload (client-side only, no verification)
 */
function decodeToken(token: string): any {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (error) {
    console.error('Failed to decode token:', error)
    return null
  }
}

/**
 * Check if token is expired or will expire soon
 */
function isTokenExpiringSoon(token: string, minutesBeforeExpiry: number = 5): boolean {
  const payload = decodeToken(token)
  if (!payload || !payload.exp) return true

  const expirationTime = payload.exp * 1000 // Convert to milliseconds
  const now = Date.now()
  const timeUntilExpiry = expirationTime - now
  const minutesUntilExpiry = timeUntilExpiry / (60 * 1000)

  return minutesUntilExpiry <= minutesBeforeExpiry
}

/**
 * Store JWT tokens
 */
export function storeTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === 'undefined') return

  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)

  // Setup auto-refresh
  setupTokenRefresh()
}

/**
 * Get access token
 */
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

/**
 * Get refresh token
 */
export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

/**
 * Clear JWT tokens
 */
export function clearTokens(): void {
  if (typeof window === 'undefined') return

  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)

  // Cancel refresh timer
  if (refreshTimer) {
    clearTimeout(refreshTimer)
    refreshTimer = null
  }
}

/**
 * Refresh access token using refresh token
 */
export async function refreshAccessToken(): Promise<string | null> {
  // Prevent concurrent refresh requests
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  isRefreshing = true
  refreshPromise = (async () => {
    try {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        throw new Error('No refresh token available')
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        // Refresh token is invalid or expired
        if (response.status === 401) {
          clearTokens()
          clearSession()
          throw new Error('Refresh token expired')
        }
        throw new Error('Token refresh failed')
      }

      const data = await response.json()
      const newAccessToken = data.access_token

      // Store new access token
      localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken)

      // Setup next refresh
      setupTokenRefresh()

      return newAccessToken
    } catch (error) {
      console.error('Failed to refresh token:', error)
      clearTokens()
      return null
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()

  return refreshPromise
}

/**
 * Setup automatic token refresh
 */
function setupTokenRefresh(): void {
  // Clear existing timer
  if (refreshTimer) {
    clearTimeout(refreshTimer)
    refreshTimer = null
  }

  const accessToken = getAccessToken()
  if (!accessToken) return

  const payload = decodeToken(accessToken)
  if (!payload || !payload.exp) return

  // Calculate time until token should be refreshed
  const expirationTime = payload.exp * 1000
  const refreshTime = expirationTime - (REFRESH_BEFORE_EXPIRE_MINUTES * 60 * 1000)
  const delay = refreshTime - Date.now()

  if (delay > 0) {
    refreshTimer = setTimeout(async () => {
      await refreshAccessToken()
    }, delay)
  } else {
    // Token already needs refresh
    refreshAccessToken()
  }
}

/**
 * Get valid access token (auto-refresh if needed)
 */
export async function getValidAccessToken(): Promise<string | null> {
  const accessToken = getAccessToken()

  if (!accessToken) {
    return null
  }

  // Check if token is expiring soon
  if (isTokenExpiringSoon(accessToken, REFRESH_BEFORE_EXPIRE_MINUTES)) {
    return await refreshAccessToken()
  }

  return accessToken
}

/**
 * Login with email and password
 */
export async function login(email: string, password: string): Promise<boolean> {
  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      throw new Error('Login failed')
    }

    const data = await response.json()

    // Store tokens
    storeTokens(data.access_token, data.refresh_token)

    // Store user info
    if (data.user && data.user.id) {
      localStorage.setItem(USER_ID_KEY, data.user.id)
    }

    return true
  } catch (error) {
    console.error('Login error:', error)
    return false
  }
}

/**
 * Register new user
 */
export async function register(email: string, password: string): Promise<boolean> {
  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      throw new Error('Registration failed')
    }

    const data = await response.json()

    // Store tokens
    storeTokens(data.access_token, data.refresh_token)

    // Store user info
    if (data.user && data.user.id) {
      localStorage.setItem(USER_ID_KEY, data.user.id)
    }

    return true
  } catch (error) {
    console.error('Registration error:', error)
    return false
  }
}

/**
 * Logout (revoke current token)
 */
export async function logout(): Promise<void> {
  try {
    const accessToken = getAccessToken()
    if (accessToken) {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      })
    }
  } catch (error) {
    console.error('Logout error:', error)
  } finally {
    // Clear all auth data
    clearTokens()
    clearSession()
  }
}

/**
 * Logout from all devices
 */
export async function logoutAll(): Promise<void> {
  try {
    const accessToken = getAccessToken()
    if (accessToken) {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${API_URL}/auth/logout-all`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      })
    }
  } catch (error) {
    console.error('Logout all error:', error)
  } finally {
    // Clear all auth data
    clearTokens()
    clearSession()
  }
}

/**
 * Initialize auth (setup token refresh on page load)
 */
export function initializeAuth(): void {
  if (typeof window === 'undefined') return

  const accessToken = getAccessToken()
  if (accessToken) {
    setupTokenRefresh()
  }
}

// Initialize auth on module load
if (typeof window !== 'undefined') {
  initializeAuth()
}
