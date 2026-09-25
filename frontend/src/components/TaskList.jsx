const PRIORITY_LABELS = { high: '🔴 High', medium: '🟡 Medium', low: '🟢 Low' }

/** Renders the current list of added tasks with remove buttons. */
export default function TaskList({ tasks, onRemove }) {
  if (tasks.length === 0) {
    return <p className="empty-hint">No tasks added yet. Add at least one above.</p>
  }

  return (
    <ul className="task-list" aria-label="Task list">
      {tasks.map((task) => (
        <li key={task.id} className="task-chip">
          <span className="task-chip-name">{task.name}</span>
          <span className={`priority-badge priority-${task.priority}`}>
            {PRIORITY_LABELS[task.priority] ?? task.priority}
          </span>
          {task.deadline && (
            <span className="task-chip-deadline">📅 {task.deadline}</span>
          )}
          <button
            type="button"
            onClick={() => onRemove(task.id)}
            className="btn-remove"
            aria-label={`Remove task: ${task.name}`}
          >
            ✕
          </button>
        </li>
      ))}
    </ul>
  )
}
