import { Route, Routes } from 'react-router'
import { AppShell } from '../components/layout/AppShell'
import { useMissionData } from '../hooks/useMissionData'
import { Dashboard } from '../pages/Dashboard'
import { MissionCrew } from '../pages/MissionCrew'
import { NotFound, Placeholder } from '../pages/Placeholder'
import { navigation } from './navigation'

export function App() {
  const data = useMissionData()
  return <Routes><Route element={<AppShell data={data} />}>
    <Route index element={<Dashboard />} />
    <Route path="mission" element={<MissionCrew />} />
    {navigation.filter(item => item.empty).map(item => <Route key={item.path} path={item.path} element={<Placeholder {...item} />} />)}
    <Route path="*" element={<NotFound />} />
  </Route></Routes>
}
