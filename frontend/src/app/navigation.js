import { LayoutDashboard, ClipboardPlus, ChartNoAxesCombined, ShieldCheck, BookOpen, Orbit, UsersRound, SlidersHorizontal } from 'lucide-react'

export const navigation = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/check-in', label: 'Daily Check-In', icon: ClipboardPlus },
  { path: '/history', label: 'Health History', icon: ChartNoAxesCombined, title: 'Health history', description: 'Your measurements, with the context that matters.', empty: 'Historical measurements are not available in this workspace yet.' },
  { path: '/assessments', label: 'Assessments & Alerts', icon: ShieldCheck },
  { path: '/guidance', label: 'Guidance', icon: BookOpen },
  { path: '/hazards', label: 'Spaceflight Hazards', icon: Orbit },
  { path: '/mission', label: 'Mission & Crew', icon: UsersRound },
  { path: '/demo', label: 'Mission Simulator', icon: SlidersHorizontal },
]
