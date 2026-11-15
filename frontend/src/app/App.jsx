import { Route, Routes } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { useMissionData } from '../hooks/useMissionData'
import { Dashboard } from '../pages/Dashboard'
import { MissionCrew } from '../pages/MissionCrew'
import { NotFound, Placeholder } from '../pages/Placeholder'
import { navigation } from './navigation'
import { DailyCheckin } from '../pages/DailyCheckin'
import { MissionSimulator } from '../pages/MissionSimulator'
import { Assessments } from '../pages/Assessments'

export function App() {
  const data = useMissionData()
  return <Routes><Route element={<AppShell data={data} />}>
    <Route index element={<Dashboard />} />
    <Route path="mission" element={<MissionCrew />} />
    <Route path="check-in" element={<DailyCheckin />} />
    <Route path="demo" element={<MissionSimulator />} />
    <Route path="assessments" element={<Assessments />} />
    {navigation.filter(item => item.empty).map(item => <Route key={item.path} path={item.path} element={<Placeholder {...item} />} />)}
    <Route path="*" element={<NotFound />} />
  </Route></Routes>
}
