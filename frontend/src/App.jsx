import { useState } from 'react'
import TaskInput from './components/TaskInput'
import TaskList from './components/TaskList'
import WorkingHours from './components/WorkingHours'
import FixedCommitments from './components/FixedCommitments'
import Schedule from './components/Schedule'
import { generatePlan } from './api/planner'
import { formatTime12 } from './utils/formatTime'
import './App.css'

let nextId = 1
function uid() { return nextId++ }

export default function App() {
  // ── Task state ──────────────────────────────────────────────────────────────
  const [tasks, setTasks] = useState([])

  function addTask(task) {
    setTasks((prev) => [...prev, { ...task, id: uid() }])
  }
  function removeTask(id) {
    setTasks((prev) => prev.filter((t) => t.id !== id))
  }

  // ── Working hours state ─────────────────────────────────────────────────────
  const [workingHours, setWorkingHours] = useState({ startTime: '09:00', endTime: '17:00' })

  function handleWorkingHoursChange(field, value) {
    setWorkingHours((prev) => ({ ...prev, [field]: value }))
  }

  // ── Fixed commitments state ─────────────────────────────────────────────────
  const [commitments, setCommitments] = useState([])

  function addCommitment(c) {
    setCommitments((prev) => [...prev, { ...c, id: uid() }])
  }
  function removeCommitment(id) {
    setCommitments((prev) => prev.filter((c) => c.id !== id))
  }

  // ── Plan / UI state ─────────────────────────────────────────────────────────
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // ── Validation ──────────────────────────────────────────────────────────────
  function validate() {
    if (tasks.length === 0) return 'Add at least one task before generating.'
    if (!workingHours.startTime || !workingHours.endTime)
      return 'Please set your working hours start and end times.'
    if (workingHours.startTime >= workingHours.endTime)
      return 'Working hours end time must be after start time.'
    return null
  }

  // ── Generate plan ───────────────────────────────────────────────────────────
  async function handleGenerate() {
    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }

    setError(null)
    setLoading(true)
    setPlan(null)

    const payload = {
      tasks: tasks.map((t) => t.name),
      priorities: tasks.map((t) => t.priority),
      deadlines: tasks.filter((t) => t.deadline).map((t) => `${t.name}: ${t.deadline}`),
      working_hours: `${formatTime12(workingHours.startTime)} - ${formatTime12(workingHours.endTime)}`,
      fixed_commitments: commitments.map((c) => `${c.name} (${formatTime12(c.start)} - ${formatTime12(c.end)})`),
    }

    try {
      const result = await generatePlan(payload)
      setPlan(result)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const hasValidInput = tasks.length > 0 && workingHours.startTime && workingHours.endTime

  return (
    <div className="app-container">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-icon">🗓️</div>
        <h1 className="app-title">One-Click Day Planner</h1>
        <p className="app-subtitle">
          Tell us your goals — we&apos;ll turn them into a practical, AI-powered daily schedule.
        </p>
      </header>

      <main className="app-main">
        <div className="planner-grid">
          {/* ── Left Panel: Inputs ── */}
          <div className="panel panel-inputs">

            {/* Tasks */}
            <section className="card" aria-labelledby="tasks-heading">
              <h2 id="tasks-heading" className="card-title">
                <span className="card-icon">✅</span> Tasks &amp; Goals
              </h2>
              <p className="card-hint">What do you need to accomplish today?</p>
              <TaskInput onAdd={addTask} />
              <TaskList tasks={tasks} onRemove={removeTask} />
            </section>

            {/* Working Hours */}
            <section className="card" aria-labelledby="hours-heading">
              <h2 id="hours-heading" className="card-title">
                <span className="card-icon">⏰</span> Available Working Hours
              </h2>
              <p className="card-hint">When are you available to work today?</p>
              <WorkingHours
                startTime={workingHours.startTime}
                endTime={workingHours.endTime}
                onChange={handleWorkingHoursChange}
              />
            </section>

            {/* Fixed Commitments */}
            <section className="card" aria-labelledby="commitments-heading">
              <h2 id="commitments-heading" className="card-title">
                <span className="card-icon">📌</span> Fixed Commitments
                <span className="optional-tag">optional</span>
              </h2>
              <p className="card-hint">Meetings or appointments that are already locked in.</p>
              <FixedCommitments
                commitments={commitments}
                onAdd={addCommitment}
                onRemove={removeCommitment}
              />
            </section>

            {/* Generate Button */}
            <div className="generate-area">
              <button
                id="generate-btn"
                type="button"
                className="btn btn-primary btn-generate"
                onClick={handleGenerate}
                disabled={loading || !hasValidInput}
              >
                {loading ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    Generating…
                  </>
                ) : (
                  '⚡ Generate My Day'
                )}
              </button>
              {!hasValidInput && !loading && (
                <p className="generate-hint">Add at least one task and set working hours to continue.</p>
              )}
            </div>

            {/* Error banner */}
            {error && (
              <div className="error-banner" role="alert">
                <span className="error-icon">⚠️</span>
                <span>{error}</span>
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => setError(null)}
                  aria-label="Dismiss error"
                >
                  ✕
                </button>
              </div>
            )}
          </div>

          {/* ── Right Panel: Schedule Output ── */}
          <div className="panel panel-schedule">
            <section className="card card-schedule" aria-labelledby="schedule-heading">
              <h2 id="schedule-heading" className="card-title">
                <span className="card-icon">🗓️</span> Your Day
                {loading && <span className="loading-badge">Generating…</span>}
              </h2>
              {loading ? (
                <div className="schedule-loading">
                  <div className="loading-pulse" aria-hidden="true" />
                  <div className="loading-pulse loading-pulse-short" aria-hidden="true" />
                  <div className="loading-pulse" aria-hidden="true" />
                  <p className="loading-text">AI is crafting your schedule…</p>
                </div>
              ) : (
                <Schedule plan={plan} />
              )}
            </section>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Powered by Gemini AI &mdash; One-Click Day Planner</p>
      </footer>
    </div>
  )
}
