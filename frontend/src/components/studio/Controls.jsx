export function IconButton({ label, children, onClick, active = false, disabled = false, testId }) {
  return <button data-testid={testId || `icon-${label.toLowerCase().replaceAll(" ", "-")}`} className={`icon-button ${active ? "active" : ""}`} aria-label={label} title={label} onClick={onClick} disabled={disabled}>{children}</button>;
}

export function Pill({ children, tone = "neutral", testId = "status-pill" }) {
  return <span data-testid={testId} className={`pill ${tone}`}>{children}</span>;
}

export function Switch({ on, onChange, label, testId, disabled = false }) {
  return <button className={`switch ${on ? "on" : ""}`} data-testid={testId} aria-label={label} aria-pressed={on} disabled={disabled} onClick={() => onChange(!on)}><span /></button>;
}
