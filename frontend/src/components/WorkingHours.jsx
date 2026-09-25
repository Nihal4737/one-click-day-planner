/** Working hours start/end time selectors. */
export default function WorkingHours({ startTime, endTime, onChange }) {
  return (
    <div className="working-hours-row">
      <label htmlFor="wh-start" className="field-label">
        From
      </label>
      <input
        id="wh-start"
        type="time"
        value={startTime}
        onChange={(e) => onChange('startTime', e.target.value)}
        className="input-text input-time"
        aria-label="Working hours start"
      />
      <span className="time-separator">to</span>
      <input
        id="wh-end"
        type="time"
        value={endTime}
        onChange={(e) => onChange('endTime', e.target.value)}
        className="input-text input-time"
        aria-label="Working hours end"
      />
    </div>
  )
}
