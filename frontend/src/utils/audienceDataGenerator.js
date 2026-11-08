// Dynamic audience intelligence generator tailored to searched YouTube channels
export function deriveChannelAudienceAnalytics(activeChannelData) {
  if (!activeChannelData || !activeChannelData.channel) {
    return null
  }

  const channel = activeChannelData.channel
  const kpis = activeChannelData.kpis || {}
  const videos = Array.isArray(activeChannelData.latestVideos) ? activeChannelData.latestVideos : []

  const channelName = channel.name || 'Creator'
  const handle = channel.handle || ''
  const subscribers = Number(channel.subscribers || kpis.subscribers || 100000)
  const totalViews = Number(channel.totalViews || kpis.totalViews || 5000000)
  const baseEngagement = parseFloat(kpis.engagementRate) || 7.5

  // 1. Analyze Channel Category from Name, Handle & Video Titles
  const textCorpus = [
    channelName,
    handle,
    ...videos.map((v) => v.title || ''),
  ].join(' ').toLowerCase()

  const isTech = /dev|code|program|google|tech|software|ai|python|javascript|cloud|api|mkbhd|marques|fireship|linux|hardware|engineering/.test(textCorpus)
  const isGaming = /game|gaming|play|minecraft|gta|roblox|pokemon|esports|twitch|stream|speedrun|pewdiepie|ign|nintendo|playstation/.test(textCorpus)
  const isScience = /science|physics|math|veritasium|kurzgesagt|ted|academy|documentary|explained|space|history|philosophy|vsauce|3blue1brown/.test(textCorpus)
  const isEntertainment = /mrbeast|challenge|prank|extreme|survive|dude perfect|vlog|stunt|comedy|fun|beast|impossible|win|cash/.test(textCorpus)
  const isFinance = /finance|money|invest|crypto|stock|wealth|business|market|startup|economy|income/.test(textCorpus)

  // 2. Derive Niche Profile
  let niche = 'General Creator & Lifestyle'
  let demographics = []
  let genderSplit = []
  let countries = []
  let contentCategories = []
  let optimalWindow = '17:00 – 20:00 UTC'
  let peakStartHour = 17
  let peakEndHour = 20

  if (isTech) {
    niche = 'Tech & Software Engineering'
    optimalWindow = '15:00 – 19:00 UTC'
    peakStartHour = 15
    peakEndHour = 19
    demographics = [
      { age: '13-17', male: 3.4, female: 1.2, other: 0.4, total: 5.0 },
      { age: '18-24', male: 26.2, female: 7.2, other: 1.4, total: 34.8 },
      { age: '25-34', male: 33.4, female: 8.6, other: 1.8, total: 43.8 },
      { age: '35-44', male: 9.2, female: 2.2, other: 0.4, total: 11.8 },
      { age: '45-54', male: 2.4, female: 0.6, other: 0.2, total: 3.2 },
      { age: '55+', male: 1.0, female: 0.3, other: 0.1, total: 1.4 },
    ]
    genderSplit = [
      { name: 'Male', value: 75.6, color: '#0284c7' },
      { name: 'Female', value: 20.1, color: '#ec4899' },
      { name: 'Non-binary / Other', value: 4.3, color: '#8b5cf6' },
    ]
    countries = [
      { country: 'United States', code: 'US', flag: '🇺🇸', percentage: 34.6 },
      { country: 'India', code: 'IN', flag: '🇮🇳', percentage: 27.8 },
      { country: 'Germany', code: 'DE', flag: '🇩🇪', percentage: 8.5 },
      { country: 'United Kingdom', code: 'GB', flag: '🇬🇧', percentage: 7.4 },
      { country: 'Canada', code: 'CA', flag: '🇨🇦', percentage: 6.1 },
      { country: 'Australia', code: 'AU', flag: '🇦🇺', percentage: 4.3 },
      { country: 'Others', code: 'OTHER', flag: '🌐', percentage: 11.3 },
    ]
    contentCategories = [
      { type: 'Tutorials & Code Walkthroughs', engagementRate: +(baseEngagement * 1.25).toFixed(1), viewsMultiplier: 0.32 },
      { type: 'Architecture Deep Dives', engagementRate: +(baseEngagement * 1.16).toFixed(1), viewsMultiplier: 0.28 },
      { type: 'Release Notes & Keynotes', engagementRate: +(baseEngagement * 1.06).toFixed(1), viewsMultiplier: 0.42 },
      { type: 'Quick Shorts & Dev Tips', engagementRate: +(baseEngagement * 0.94).toFixed(1), viewsMultiplier: 0.54 },
      { type: 'Live Q&A & Keynote Sessions', engagementRate: +(baseEngagement * 0.86).toFixed(1), viewsMultiplier: 0.20 },
    ]
  } else if (isEntertainment) {
    niche = 'Entertainment & Viral Challenges'
    optimalWindow = '16:00 – 20:00 UTC'
    peakStartHour = 16
    peakEndHour = 20
    demographics = [
      { age: '13-17', male: 17.8, female: 10.2, other: 0.8, total: 28.8 },
      { age: '18-24', male: 25.8, female: 14.4, other: 1.0, total: 41.2 },
      { age: '25-34', male: 12.6, female: 6.8, other: 0.5, total: 19.9 },
      { age: '35-44', male: 4.6, female: 2.1, other: 0.2, total: 6.9 },
      { age: '45-54', male: 1.5, female: 0.8, other: 0.1, total: 2.4 },
      { age: '55+', male: 0.5, female: 0.3, other: 0.0, total: 0.8 },
    ]
    genderSplit = [
      { name: 'Male', value: 62.8, color: '#0284c7' },
      { name: 'Female', value: 34.6, color: '#ec4899' },
      { name: 'Non-binary / Other', value: 2.6, color: '#8b5cf6' },
    ]
    countries = [
      { country: 'United States', code: 'US', flag: '🇺🇸', percentage: 41.2 },
      { country: 'India', code: 'IN', flag: '🇮🇳', percentage: 16.5 },
      { country: 'United Kingdom', code: 'GB', flag: '🇬🇧', percentage: 11.2 },
      { country: 'Brazil', code: 'BR', flag: '🇧🇷', percentage: 9.4 },
      { country: 'Canada', code: 'CA', flag: '🇨🇦', percentage: 7.1 },
      { country: 'Mexico', code: 'MX', flag: '🇲🇽', percentage: 5.8 },
      { country: 'Others', code: 'OTHER', flag: '🌐', percentage: 8.8 },
    ]
    contentCategories = [
      { type: 'Mega Challenges & Stunts', engagementRate: +(baseEngagement * 1.32).toFixed(1), viewsMultiplier: 0.65 },
      { type: 'Quick Viral Shorts', engagementRate: +(baseEngagement * 1.18).toFixed(1), viewsMultiplier: 0.85 },
      { type: 'Philanthropy & Giveaways', engagementRate: +(baseEngagement * 1.09).toFixed(1), viewsMultiplier: 0.52 },
      { type: 'Behind-the-Scenes & Vlogs', engagementRate: +(baseEngagement * 0.92).toFixed(1), viewsMultiplier: 0.36 },
      { type: 'Collaborations & Guest Stars', engagementRate: +(baseEngagement * 0.85).toFixed(1), viewsMultiplier: 0.44 },
    ]
  } else if (isScience) {
    niche = 'Science, Education & Discovery'
    optimalWindow = '17:00 – 21:00 UTC'
    peakStartHour = 17
    peakEndHour = 21
    demographics = [
      { age: '13-17', male: 4.1, female: 1.7, other: 0.2, total: 6.0 },
      { age: '18-24', male: 23.6, female: 9.8, other: 1.4, total: 34.8 },
      { age: '25-34', male: 26.2, female: 11.4, other: 1.3, total: 38.9 },
      { age: '35-44', male: 9.6, female: 4.2, other: 0.4, total: 14.2 },
      { age: '45-54', male: 2.8, female: 1.1, other: 0.1, total: 4.0 },
      { age: '55+', male: 1.4, female: 0.6, other: 0.1, total: 2.1 },
    ]
    genderSplit = [
      { name: 'Male', value: 67.7, color: '#0284c7' },
      { name: 'Female', value: 28.8, color: '#ec4899' },
      { name: 'Non-binary / Other', value: 3.5, color: '#8b5cf6' },
    ]
    countries = [
      { country: 'United States', code: 'US', flag: '🇺🇸', percentage: 37.8 },
      { country: 'United Kingdom', code: 'GB', flag: '🇬🇧', percentage: 14.2 },
      { country: 'India', code: 'IN', flag: '🇮🇳', percentage: 12.6 },
      { country: 'Canada', code: 'CA', flag: '🇨🇦', percentage: 9.4 },
      { country: 'Germany', code: 'DE', flag: '🇩🇪', percentage: 8.1 },
      { country: 'Australia', code: 'AU', flag: '🇦🇺', percentage: 6.3 },
      { country: 'Others', code: 'OTHER', flag: '🌐', percentage: 11.6 },
    ]
    contentCategories = [
      { type: 'Documentary Deep Dives', engagementRate: +(baseEngagement * 1.30).toFixed(1), viewsMultiplier: 0.42 },
      { type: 'Physical Experiments', engagementRate: +(baseEngagement * 1.18).toFixed(1), viewsMultiplier: 0.48 },
      { type: 'Visual Math & Explanations', engagementRate: +(baseEngagement * 1.08).toFixed(1), viewsMultiplier: 0.32 },
      { type: 'Micro-Theories & Shorts', engagementRate: +(baseEngagement * 0.95).toFixed(1), viewsMultiplier: 0.58 },
      { type: 'Expert Interviews & Discussions', engagementRate: +(baseEngagement * 0.82).toFixed(1), viewsMultiplier: 0.22 },
    ]
  } else if (isGaming) {
    niche = 'Gaming & Esports'
    optimalWindow = '18:00 – 23:00 UTC'
    peakStartHour = 18
    peakEndHour = 23
    demographics = [
      { age: '13-17', male: 18.5, female: 7.2, other: 0.7, total: 26.4 },
      { age: '18-24', male: 31.4, female: 11.2, other: 1.3, total: 43.9 },
      { age: '25-34', male: 14.6, female: 5.6, other: 0.7, total: 20.9 },
      { age: '35-44', male: 4.1, female: 1.6, other: 0.2, total: 5.9 },
      { age: '45-54', male: 1.3, female: 0.5, other: 0.1, total: 1.9 },
      { age: '55+', male: 0.7, female: 0.2, other: 0.1, total: 1.0 },
    ]
    genderSplit = [
      { name: 'Male', value: 70.6, color: '#0284c7' },
      { name: 'Female', value: 26.3, color: '#ec4899' },
      { name: 'Non-binary / Other', value: 3.1, color: '#8b5cf6' },
    ]
    countries = [
      { country: 'United States', code: 'US', flag: '🇺🇸', percentage: 36.5 },
      { country: 'United Kingdom', code: 'GB', flag: '🇬🇧', percentage: 13.4 },
      { country: 'Germany', code: 'DE', flag: '🇩🇪', percentage: 10.2 },
      { country: 'Brazil', code: 'BR', flag: '🇧🇷', percentage: 8.8 },
      { country: 'Canada', code: 'CA', flag: '🇨🇦', percentage: 8.1 },
      { country: 'Australia', code: 'AU', flag: '🇦🇺', percentage: 6.4 },
      { country: 'Others', code: 'OTHER', flag: '🌐', percentage: 16.6 },
    ]
    contentCategories = [
      { type: 'Speedruns & Mod Challenges', engagementRate: +(baseEngagement * 1.25).toFixed(1), viewsMultiplier: 0.44 },
      { type: 'Clips & Funny Moments Shorts', engagementRate: +(baseEngagement * 1.15).toFixed(1), viewsMultiplier: 0.68 },
      { type: 'Live Stream Highlights', engagementRate: +(baseEngagement * 1.05).toFixed(1), viewsMultiplier: 0.36 },
      { type: 'Walkthroughs & Guides', engagementRate: +(baseEngagement * 0.92).toFixed(1), viewsMultiplier: 0.28 },
      { type: 'First Impressions & Reviews', engagementRate: +(baseEngagement * 0.85).toFixed(1), viewsMultiplier: 0.24 },
    ]
  } else if (isFinance) {
    niche = 'Finance & Wealth Building'
    optimalWindow = '13:00 – 17:00 UTC'
    peakStartHour = 13
    peakEndHour = 17
    demographics = [
      { age: '13-17', male: 2.1, female: 0.7, other: 0.2, total: 3.0 },
      { age: '18-24', male: 22.4, female: 7.2, other: 1.4, total: 31.0 },
      { age: '25-34', male: 35.8, female: 10.4, other: 1.8, total: 48.0 },
      { age: '35-44', male: 9.8, female: 3.8, other: 0.4, total: 14.0 },
      { age: '45-54', male: 2.2, female: 0.6, other: 0.2, total: 3.0 },
      { age: '55+', male: 0.8, female: 0.2, other: 0.0, total: 1.0 },
    ]
    genderSplit = [
      { name: 'Male', value: 73.1, color: '#0284c7' },
      { name: 'Female', value: 22.9, color: '#ec4899' },
      { name: 'Non-binary / Other', value: 4.0, color: '#8b5cf6' },
    ]
    countries = [
      { country: 'United States', code: 'US', flag: '🇺🇸', percentage: 42.4 },
      { country: 'United Kingdom', code: 'GB', flag: '🇬🇧', percentage: 15.2 },
      { country: 'Canada', code: 'CA', flag: '🇨🇦', percentage: 11.4 },
      { country: 'India', code: 'IN', flag: '🇮🇳', percentage: 10.8 },
      { country: 'Australia', code: 'AU', flag: '🇦🇺', percentage: 7.2 },
      { country: 'Singapore', code: 'SG', flag: '🇸🇬', percentage: 4.8 },
      { country: 'Others', code: 'OTHER', flag: '🌐', percentage: 8.2 },
    ]
    contentCategories = [
      { type: 'Market Analysis & Deep Dives', engagementRate: +(baseEngagement * 1.28).toFixed(1), viewsMultiplier: 0.40 },
      { type: 'Investment Case Studies', engagementRate: +(baseEngagement * 1.18).toFixed(1), viewsMultiplier: 0.35 },
      { type: 'Macro Economic Breakdowns', engagementRate: +(baseEngagement * 1.08).toFixed(1), viewsMultiplier: 0.45 },
      { type: 'Quick Money Tips & Shorts', engagementRate: +(baseEngagement * 0.96).toFixed(1), viewsMultiplier: 0.55 },
      { type: 'Portfolio Reviews & Live Q&A', engagementRate: +(baseEngagement * 0.88).toFixed(1), viewsMultiplier: 0.22 },
    ]
  } else {
    niche = 'General Creator & Lifestyle'
    optimalWindow = '17:00 – 20:00 UTC'
    peakStartHour = 17
    peakEndHour = 20
    demographics = [
      { age: '13-17', male: 7.2, female: 7.4, other: 0.6, total: 15.2 },
      { age: '18-24', male: 20.8, female: 22.4, other: 1.6, total: 44.8 },
      { age: '25-34', male: 13.2, female: 14.8, other: 1.2, total: 29.2 },
      { age: '35-44', male: 3.6, female: 4.1, other: 0.3, total: 8.0 },
      { age: '45-54', male: 1.0, female: 1.0, other: 0.1, total: 2.1 },
      { age: '55+', male: 0.3, female: 0.3, other: 0.1, total: 0.7 },
    ]
    genderSplit = [
      { name: 'Female', value: 50.0, color: '#ec4899' },
      { name: 'Male', value: 46.1, color: '#0284c7' },
      { name: 'Non-binary / Other', value: 3.9, color: '#8b5cf6' },
    ]
    countries = [
      { country: 'United States', code: 'US', flag: '🇺🇸', percentage: 36.4 },
      { country: 'India', code: 'IN', flag: '🇮🇳', percentage: 18.2 },
      { country: 'United Kingdom', code: 'GB', flag: '🇬🇧', percentage: 14.5 },
      { country: 'Canada', code: 'CA', flag: '🇨🇦', percentage: 9.8 },
      { country: 'Germany', code: 'DE', flag: '🇩🇪', percentage: 7.3 },
      { country: 'Australia', code: 'AU', flag: '🇦🇺', percentage: 5.8 },
      { country: 'Others', code: 'OTHER', flag: '🌐', percentage: 8.0 },
    ]
    contentCategories = [
      { type: 'Tutorials & How-To Guides', engagementRate: +(baseEngagement * 1.20).toFixed(1), viewsMultiplier: 0.34 },
      { type: 'Quick Shorts & Reels', engagementRate: +(baseEngagement * 1.12).toFixed(1), viewsMultiplier: 0.60 },
      { type: 'In-Depth Reviews & Tests', engagementRate: +(baseEngagement * 1.02).toFixed(1), viewsMultiplier: 0.30 },
      { type: 'Behind-the-Scenes & Vlogs', engagementRate: +(baseEngagement * 0.94).toFixed(1), viewsMultiplier: 0.25 },
      { type: 'Live Q&A & Community Chat', engagementRate: +(baseEngagement * 0.85).toFixed(1), viewsMultiplier: 0.18 },
    ]
  }

  // Refine peak hour window using real upload history if available
  if (videos.length > 0) {
    const uploadHours = []
    videos.forEach((v) => {
      if (v.publishedAt) {
        try {
          const h = new Date(v.publishedAt).getUTCHours()
          uploadHours.push(h)
        } catch {
          // ignore
        }
      }
    })
    if (uploadHours.length >= 3) {
      const avgHour = Math.round(uploadHours.reduce((a, b) => a + b, 0) / uploadHours.length)
      peakStartHour = Math.max(0, avgHour - 1)
      peakEndHour = Math.min(23, avgHour + 2)
      optimalWindow = `${String(peakStartHour).padStart(2, '0')}:00 – ${String(peakEndHour).padStart(2, '0')}:00 UTC`
    }
  }

  // 3. Compute Country Reach Numbers
  const enrichedCountries = countries.map((c) => ({
    ...c,
    viewers: Math.round(subscribers * (c.percentage / 100)),
    formattedReach: formatCompactNumber(Math.round(subscribers * (c.percentage / 100))),
  }))

  // 4. Content Categories with Benchmarks & Highest Converting
  const sortedCategories = [...contentCategories].sort((a, b) => b.engagementRate - a.engagementRate)
  const highestConverting = sortedCategories[0]

  // 5. 24-Hour Peak Activity Curve
  const activeHours = []
  const peakCenter = (peakStartHour + peakEndHour) / 2
  for (let h = 0; h < 24; h++) {
    const dist1 = Math.min(Math.abs(h - peakCenter), 24 - Math.abs(h - peakCenter))
    const dist2 = Math.min(Math.abs(h - 11), 24 - Math.abs(h - 11))
    let density = 14 + 78 * Math.exp(-0.5 * Math.pow(dist1 / 2.8, 2)) + 22 * Math.exp(-0.5 * Math.pow(dist2 / 2.5, 2))
    density = Math.min(100, Math.max(8, Math.round(density)))
    const activeAudience = Math.round((subscribers * 0.08) * (density / 100))
    activeHours.push({
      hour: `${String(h).padStart(2, '0')}:00`,
      density,
      activeAudience,
      isPeak: h >= peakStartHour && h <= peakEndHour,
    })
  }

  // 6. Growth & Engagement Over Time (Dual-Axis Scale)
  const growthTimeSeries = []
  const periods = ['6 Wk Ago', '5 Wk Ago', '4 Wk Ago', '3 Wk Ago', '2 Wk Ago', 'Last Wk', 'Current']
  const startSubs = Math.round(subscribers * 0.93)
  const totalSubDelta = subscribers - startSubs

  periods.forEach((period, idx) => {
    const progress = idx / (periods.length - 1)
    const currentSubs = Math.round(startSubs + totalSubDelta * (progress + Math.sin(progress * Math.PI) * 0.05))
    const engVariance = Math.sin(idx * 1.3) * 0.45
    const engRate = +Math.max(1.0, (baseEngagement + engVariance)).toFixed(1)

    growthTimeSeries.push({
      period,
      subscribers: currentSubs,
      formattedSubscribers: formatCompactNumber(currentSubs),
      engagementRate: engRate,
      views: Math.round(currentSubs * 2.4),
    })
  })

  // 7. Device Usage Platform Breakdown (Mobile 64%, Desktop 24%, Smart TV 9%, Tablet 3%)
  const deviceUsage = [
    { device: 'Mobile (Phone)', icon: '📱', percentage: 64.0, share: 64.0, viewers: Math.round(subscribers * 0.640), formattedViewers: formatCompactNumber(Math.round(subscribers * 0.640)), color: '#0284c7' },
    { device: 'Desktop / Laptop', icon: '💻', percentage: 24.0, share: 24.0, viewers: Math.round(subscribers * 0.240), formattedViewers: formatCompactNumber(Math.round(subscribers * 0.240)), color: '#10b981' },
    { device: 'Smart TV & Connected Devices', icon: '📺', percentage: 9.0, share: 9.0, viewers: Math.round(subscribers * 0.090), formattedViewers: formatCompactNumber(Math.round(subscribers * 0.090)), color: '#8b5cf6' },
    { device: 'Tablet', icon: '📲', percentage: 3.0, share: 3.0, viewers: Math.round(subscribers * 0.030), formattedViewers: formatCompactNumber(Math.round(subscribers * 0.030)), color: '#f59e0b' },
  ]

  const totalImpressions = kpis.totalImpressions || (totalViews > 0 ? Math.round(totalViews / 0.065) : Math.round(subscribers * 15.4))
  const estimatedReach = kpis.estimatedReach || (totalViews > 0 ? Math.round(totalViews * 0.72) : Math.round(subscribers * 3.8))

  const dominantDemographic = Array.isArray(demographics) && demographics.length > 0
    ? demographics.reduce((max, d) => ((d.total || 0) > (max?.total || 0) ? d : max), demographics[1] || demographics[0])
    : { age: '18-24', total: 45.0, male: 26.2, female: 7.2, other: 1.4 }

  return {
    niche,
    channelName,
    subscribers,
    totalViews,
    baseEngagement,
    totalImpressions,
    estimatedReach,
    deviceUsage,
    demographics,
    dominantDemographic,
    genderSplit,
    countries: enrichedCountries,
    contentCategories: sortedCategories,
    highestConverting,
    activeHours,
    optimalWindow,
    peakStartHour,
    peakEndHour,
    growthTimeSeries,
  }
}

function formatCompactNumber(num) {
  if (typeof num !== 'number' || isNaN(num)) return '0'
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(num)
}
