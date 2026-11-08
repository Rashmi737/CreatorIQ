import { useState, useEffect } from 'react'

const STORAGE_KEY = 'creatoriq_active_channel'
const SESSION_STORAGE_KEY = 'lastAnalyzedAccount'
const EVENT_NAME = 'creatoriq:active-channel-changed'

export function getActiveChannel() {
  if (typeof window === 'undefined') return null
  try {
    if (typeof sessionStorage !== 'undefined') {
      const sessionSaved = sessionStorage.getItem(SESSION_STORAGE_KEY)
      if (sessionSaved) return JSON.parse(sessionSaved)
    }
    if (typeof localStorage !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) return JSON.parse(saved)
    }
  } catch (e) {
    console.warn('Failed to parse active channel from storage', e)
  }
  return null
}

export function setActiveChannel(channelData) {
  try {
    if (typeof sessionStorage !== 'undefined') {
      if (channelData) {
        sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(channelData))
      } else {
        sessionStorage.removeItem(SESSION_STORAGE_KEY)
      }
    }
    if (typeof localStorage !== 'undefined') {
      if (channelData) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(channelData))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    }
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: channelData }))
    }
  } catch (e) {
    console.warn('Failed to save active channel', e)
  }
}

export function useActiveChannel() {
  const [data, setData] = useState(() => getActiveChannel())

  useEffect(() => {
    const handleUpdate = (e) => {
      setData(e.detail)
    }
    window.addEventListener(EVENT_NAME, handleUpdate)
    return () => window.removeEventListener(EVENT_NAME, handleUpdate)
  }, [])

  // Safely support both object destructuring and direct property access:
  // 1) const activeChannel = useActiveChannel(); activeChannel?.channel
  // 2) const { activeChannel } = useActiveChannel();
  // 3) const { channel, kpis, latestVideos } = useActiveChannel();
  if (data && typeof data === 'object') {
    return Object.assign({}, data, {
      activeChannel: data,
      setActiveChannel,
      channel: data.channel || null,
      kpis: data.kpis || null,
      latestVideos: Array.isArray(data.latestVideos) ? data.latestVideos : [],
      topPerforming: Array.isArray(data.topPerforming) ? data.topPerforming : [],
    })
  }

  return {
    activeChannel: null,
    setActiveChannel,
    channel: null,
    kpis: null,
    latestVideos: [],
    topPerforming: [],
  }
}

// Support both `import channelStore` and `import useActiveChannel` as default
const channelStore = Object.assign(useActiveChannel, {
  getActiveChannel,
  setActiveChannel,
  useActiveChannel,
})

export default channelStore
