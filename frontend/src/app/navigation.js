import { LayoutDashboard, ClipboardPlus, ChartNoAxesCombined, ShieldCheck, BookOpen, Orbit, UsersRound, SlidersHorizontal } from 'lucide-react'

export const navigation = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/check-in', label: 'Daily Check-In', icon: ClipboardPlus },
  { path: '/history', label: 'Health History', icon: ChartNoAxesCombined, title: 'Health history', description: 'Your measurements, with the context that matters.', empty: 'Historical measurements are not available in this workspace yet.' },
  { path: '/assessments', label: 'Assessments & Alerts', icon: ShieldCheck, title: 'Assessments & alerts', description: 'Understand the evidence behind each review.', empty: 'No assessment is available. Health evaluation is not active.' },
  { path: '/guidance', label: 'Guidance', icon: BookOpen, title: 'Health guidance', description: 'Educational context for life beyond Earth.', empty: 'The sourced guidance library is being prepared.' },
  { path: '/hazards', label: 'Spaceflight Hazards', icon: Orbit, title: 'Spaceflight hazards', description: 'Explore the environment around your mission.', empty: 'The educational hazard explorer is being prepared.' },
  { path: '/mission', label: 'Mission & Crew', icon: UsersRound },
  { path: '/demo', label: 'Demo Controls', icon: SlidersHorizontal, title: 'Demo controls', description: 'A workspace for reproducible, fictional scenarios.', empty: 'Simulation is not active. Scenario controls are not available yet.' },
]
