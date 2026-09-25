/**
 * Converts a time string or time range into 12-hour format with AM/PM.
 * Examples:
 *   "13:00" -> "1:00 PM"
 *   "09:00" -> "9:00 AM"
 *   "13:00 PM" -> "1:00 PM"
 *   "13:00 - 14:00" -> "1:00 PM - 2:00 PM"
 *   "13:00 PM - 14:00 PM" -> "1:00 PM - 2:00 PM"
 */
export function formatTime12(timeStr) {
  if (!timeStr) return ''

  if (timeStr.includes('-') || timeStr.includes('–')) {
    const parts = timeStr.split(/[-–]/)
    if (parts.length === 2) {
      return `${formatSingleTime12(parts[0].trim())} - ${formatSingleTime12(parts[1].trim())}`
    }
  }

  return formatSingleTime12(timeStr.trim())
}

function formatSingleTime12(str) {
  if (!str) return ''

  const match = str.match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i)
  if (!match) return str

  let hour = parseInt(match[1], 10)
  const minute = match[2]
  const rawPeriod = match[3] ? match[3].toUpperCase() : null

  let period = rawPeriod
  if (hour > 12) {
    hour = hour - 12
    period = 'PM'
  } else if (hour === 12) {
    if (!period) period = 'PM'
  } else if (hour === 0) {
    hour = 12
    period = 'AM'
  } else {
    if (!period) period = 'AM'
  }

  return `${hour}:${minute} ${period}`
}
