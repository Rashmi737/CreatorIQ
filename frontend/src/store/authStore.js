import { create } from 'zustand'

const TOKEN_KEY = 'creatoriq_token'
const USER_KEY = 'creatoriq_user'

const readStoredValue = (key) => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const getInitialUser = () => {
  const storedUser = readStoredValue(USER_KEY)
  if (storedUser) return storedUser
  const name = localStorage.getItem('user_name')
  const email = localStorage.getItem('user_email')
  const avatar = localStorage.getItem('user_avatar')
  if (name || email) {
    return {
      display_name: name || 'Creator',
      name: name || 'Creator',
      email: email || '',
      avatar_url: avatar || null,
      picture: avatar || null,
      role: 'creator',
    }
  }
  return null
}

const useAuthStore = create((set) => ({
  user: getInitialUser(),
  token: localStorage.getItem('token') || localStorage.getItem(TOKEN_KEY) || null,
  setSession: (nextToken, nextUser) => {
    if (nextToken) {
      localStorage.setItem('token', nextToken)
      localStorage.setItem(TOKEN_KEY, nextToken)
    }
    if (nextUser) {
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
      const userName = nextUser.display_name || nextUser.name || ''
      const userEmail = nextUser.email || ''
      const userAvatar = nextUser.avatar_url || nextUser.picture || ''
      if (userName) localStorage.setItem('user_name', userName)
      if (userEmail) localStorage.setItem('user_email', userEmail)
      if (userAvatar) localStorage.setItem('user_avatar', userAvatar)
    }
    set({ token: nextToken || null, user: nextUser || null })
  },
  clearSession: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('token')
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem('user_name')
    localStorage.removeItem('user_email')
    localStorage.removeItem('user_avatar')
    set({ token: null, user: null })
  },
}))

export default useAuthStore
