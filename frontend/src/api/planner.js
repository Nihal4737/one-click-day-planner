export async function generatePlan(payload) {
  const response = await fetch('/api/generate-plan', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json()

  if (!response.ok || data.error) {
    throw new Error(data.error || 'Failed to generate plan')
  }

  return data.plan || data
}

export async function exportToCalendar(schedule) {
  const response = await fetch('/api/calendar/export', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ schedule }),
  })

  const data = await response.json()

  if (response.status === 401 || data.authenticated === false) {
    return {
      requiresAuth: true,
      authUrl: data.auth_url || '/api/calendar/auth',
      error: data.error || 'Google Calendar authorization required.',
    }
  }

  if (!response.ok || data.error) {
    throw new Error(data.error || 'Failed to export to Google Calendar')
  }

  return data
}

export async function getCalendarAuthUrl() {
  const response = await fetch('/api/calendar/auth')
  const data = await response.json()
  if (!response.ok || data.error) {
    throw new Error(data.error || 'Failed to get authentication URL')
  }
  return data.auth_url
}

export async function getCalendarStatus() {
  const response = await fetch('/api/calendar/status')
  const data = await response.json()
  return data
}

export async function exportToNotion(schedule) {
  const response = await fetch('/api/notion/export', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ schedule }),
  })

  const data = await response.json()

  if (!response.ok || data.error || data.success === false) {
    throw new Error(data.error || 'Failed to export schedule to Notion')
  }

  return data
}

export async function getNotionStatus() {
  const response = await fetch('/api/notion/status')
  const data = await response.json()
  return data
}
