import { AlertCircle, LoaderCircle, Orbit } from 'lucide-react'

export function LoadingState({ children = 'Loading mission data…' }) {
  return <div className="state" role="status"><LoaderCircle className="spin" size={25} /><p>{children}</p></div>
}

export function ErrorState({ message, onRetry }) {
  return <div className="state error-state" role="alert"><AlertCircle size={27} /><h2>Connection interrupted</h2>
    <p>{message}</p><button className="button" onClick={onRetry}>Retry connection</button></div>
}

export function EmptyState({ title, children }) {
  return <div className="state"><Orbit size={30} /><h2>{title}</h2><p>{children}</p></div>
}

export function DemoBadge() {
  return <span className="demo-badge"><span />Fictional demo</span>
}
