import { useState } from 'react'
import { formatTime12 } from '../utils/formatTime'

/** Fixed commitments section: add/remove named time blocks. */
export default function FixedCommitments({ commitments, onAdd, onRemove }) {
  const [name, setName] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')

  function handleAdd() {
    const trimmed = name.trim()
    if (!trimmed || !start || !end) return
    onAdd({ name: trimmed, start, end })
    setName('')
    setStart('')
    setEnd('')
  }

  return (
    <div className="commitments-section">
      <div className="task-input-row">
        <input
          id="commitment-name"
          type="text"
          placeholder="e.g. Team standup"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input-text"
          aria-label="Commitment name"
        />
        <input
          id="commitment-start"
          type="time"
          value={start}
          onChange={(e) => setStart(e.target.value)}
          className="input-text input-time"
          aria-label="Commitment start time"
        />
        <span className="time-separator">to</span>
        <input
          id="commitment-end"
          type="time"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
          className="input-text input-time"
          aria-label="Commitment end time"
        />
        <button
          id="add-commitment-btn"
          type="button"
          onClick={handleAdd}
          className="btn btn-secondary"
          disabled={!name.trim() || !start || !end}
        >
          + Add
        </button>
      </div>

      {commitments.length > 0 && (
        <ul className="task-list" aria-label="Fixed commitments list">
          {commitments.map((c) => (
            <li key={c.id} className="task-chip">
              <span className="task-chip-name">{c.name}</span>
              <span className="task-chip-deadline">
                {formatTime12(`${c.start} - ${c.end}`)}
              </span>
              <button
                type="button"
                onClick={() => onRemove(c.id)}
                className="btn-remove"
                aria-label={`Remove commitment: ${c.name}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
