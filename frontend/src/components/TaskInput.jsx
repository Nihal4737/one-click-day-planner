import { useState } from 'react'

const PRIORITY_OPTIONS = ['high', 'medium', 'low']

/** Single task input row with name, priority, and deadline. */
export default function TaskInput({ onAdd }) {
  const [name, setName] = useState('')
  const [priority, setPriority] = useState('medium')
  const [deadline, setDeadline] = useState('')

  function handleAdd() {
    const trimmed = name.trim()
    if (!trimmed) return
    onAdd({ name: trimmed, priority, deadline })
    setName('')
    setPriority('medium')
    setDeadline('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleAdd()
  }

  return (
    <div className="task-input-row">
      <input
        id="task-name"
        type="text"
        placeholder="e.g. Write project proposal"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={handleKeyDown}
        className="input-text"
        aria-label="Task name"
      />
      <select
        id="task-priority"
        value={priority}
        onChange={(e) => setPriority(e.target.value)}
        className="input-select"
        aria-label="Task priority"
      >
        {PRIORITY_OPTIONS.map((p) => (
          <option key={p} value={p}>
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </option>
        ))}
      </select>
      <input
        id="task-deadline"
        type="date"
        value={deadline}
        onChange={(e) => setDeadline(e.target.value)}
        className="input-text input-date"
        aria-label="Task deadline"
      />
      <button
        id="add-task-btn"
        type="button"
        onClick={handleAdd}
        className="btn btn-secondary"
        disabled={!name.trim()}
      >
        + Add Task
      </button>
    </div>
  )
}
