import { useState, useEffect } from 'react'
import { formatTime12 } from '../utils/formatTime'
import { exportToCalendar, getCalendarAuthUrl, exportToNotion } from '../api/planner'

const TYPE_STYLES = {
  task: 'block-task',
  fixed_commitment: 'block-commitment',
  break: 'block-break',
}

const TYPE_ICONS = {
  task: '📋',
  fixed_commitment: '📌',
  break: '☕',
}

const PRIORITY_BADGE = {
  high: <span className="priority-badge priority-high">🔴 High</span>,
  medium: <span className="priority-badge priority-medium">🟡 Medium</span>,
  low: <span className="priority-badge priority-low">🟢 Low</span>,
}

/** Renders the AI-generated day schedule as chronological time blocks. */
export default function Schedule({ plan }) {
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState(null)
  const [exportError, setExportError] = useState(null)

  const [exportingNotion, setExportingNotion] = useState(false)
  const [notionSuccess, setNotionSuccess] = useState(null)
  const [notionError, setNotionError] = useState(null)

  useEffect(() => {
    // Check if redirected back from Google OAuth callback
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('calendar_auth') === 'success') {
      setExportSuccess('Google Calendar connected! Click Export to sync your schedule.')
      // Clean up URL parameter cleanly
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [])

  if (!plan) {
    return (
      <div className="schedule-empty">
        <div className="empty-icon">🗓️</div>
        <p>Your schedule will appear here.</p>
        <p className="empty-hint">Fill in your tasks and working hours, then click <strong>Generate My Day</strong>.</p>
      </div>
    )
  }

  const { summary, schedule = [], unassigned_tasks = [] } = plan

  async function handleExportCalendar() {
    setExporting(true)
    setExportSuccess(null)
    setExportError(null)

    try {
      const res = await exportToCalendar(schedule)
      if (res.requiresAuth) {
        // Redirect to Google OAuth URL
        const authUrl = res.authUrl || (await getCalendarAuthUrl())
        window.location.href = authUrl
        return
      }
      setExportSuccess(res.message || 'Successfully exported to Google Calendar!')
    } catch (err) {
      setExportError(err.message || 'Failed to export schedule to Google Calendar.')
    } finally {
      setExporting(false)
    }
  }

  async function handleExportNotion() {
    setExportingNotion(true)
    setNotionSuccess(null)
    setNotionError(null)

    try {
      const res = await exportToNotion(schedule)
      setNotionSuccess(res.message || 'Successfully exported to Notion!')
    } catch (err) {
      setNotionError(err.message || 'Failed to export schedule to Notion.')
    } finally {
      setExportingNotion(false)
    }
  }

  return (
    <div className="schedule-output">
      <div className="schedule-header-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', gap: '12px', flexWrap: 'wrap' }}>
        {summary && <p className="schedule-summary" style={{ margin: 0, flex: 1, minWidth: '200px' }}>{summary}</p>}
        {schedule.length > 0 && (
          <div className="export-button-group" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary btn-export-calendar"
              onClick={handleExportCalendar}
              disabled={exporting}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                fontSize: '0.875rem',
                fontWeight: '600',
                borderRadius: '8px',
                border: '1px solid #4285F4',
                backgroundColor: 'rgba(66, 133, 244, 0.15)',
                color: '#60a5fa',
                cursor: exporting ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {exporting ? 'Exporting…' : '📅 Export to Google Calendar'}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-export-notion"
              onClick={handleExportNotion}
              disabled={exportingNotion}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                fontSize: '0.875rem',
                fontWeight: '600',
                borderRadius: '8px',
                border: '1px solid #a855f7',
                backgroundColor: 'rgba(168, 85, 247, 0.15)',
                color: '#c084fc',
                cursor: exportingNotion ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {exportingNotion ? 'Exporting…' : '📝 Export to Notion'}
            </button>
          </div>
        )}
      </div>

      {exportSuccess && (
        <div className="export-banner export-success" style={{ padding: '10px 14px', marginBottom: '16px', borderRadius: '8px', background: 'rgba(34, 197, 94, 0.15)', border: '1px solid rgba(34, 197, 94, 0.3)', color: '#4ade80', fontSize: '0.875rem' }}>
          ✅ {exportSuccess}
        </div>
      )}

      {exportError && (
        <div className="export-banner export-error" style={{ padding: '10px 14px', marginBottom: '16px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', fontSize: '0.875rem' }}>
          ⚠️ {exportError}
        </div>
      )}

      {notionSuccess && (
        <div className="export-banner export-success notion-banner" style={{ padding: '10px 14px', marginBottom: '16px', borderRadius: '8px', background: 'rgba(34, 197, 94, 0.15)', border: '1px solid rgba(34, 197, 94, 0.3)', color: '#4ade80', fontSize: '0.875rem' }}>
          ✅ {notionSuccess}
        </div>
      )}

      {notionError && (
        <div className="export-banner export-error notion-banner" style={{ padding: '10px 14px', marginBottom: '16px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', fontSize: '0.875rem' }}>
          ⚠️ {notionError}
        </div>
      )}

      <div className="schedule-timeline">
        {schedule.map((item, i) => (
          <div
            key={i}
            className={`schedule-block ${TYPE_STYLES[item.type] ?? 'block-task'}`}
          >
            <div className="block-time">
              <span className="block-icon">{TYPE_ICONS[item.type] ?? '📋'}</span>
              {formatTime12(item.time_slot)}
            </div>
            <div className="block-body">
              <div className="block-title">{item.title}</div>
              <div className="block-meta">
                {item.priority && PRIORITY_BADGE[item.priority.toLowerCase()]}
                {item.notes && <span className="block-notes">{item.notes}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {unassigned_tasks && unassigned_tasks.length > 0 && (
        <div className="unassigned-section">
          <h3 className="unassigned-title">⚠️ Tasks that didn&apos;t fit today</h3>
          <ul className="unassigned-list">
            {unassigned_tasks.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
