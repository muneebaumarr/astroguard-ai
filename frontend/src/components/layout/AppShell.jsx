import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { ArrowUpRight, Menu, Shield, X } from 'lucide-react'
import { navigation } from '../../app/navigation'
import { AstronautSelector } from '../astronauts/AstronautSelector'
import { DemoBadge } from '../common/States'

export function AppShell({ data }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const current = navigation.find(item => item.path === location.pathname)
  const connected = data.status === 'ready'
  const mission = data.status === 'ready' ? data.profile.mission : null

  return <div className="application">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
      <NavLink to="/" className="brand" onClick={() => setMenuOpen(false)} aria-label="AstroGuard home">
        <span className="brand-mark"><Shield size={24} strokeWidth={1.6} /><i /></span>
        <span>ASTROGUARD<span className="brand-ai">AI</span><small>CREW HEALTH SYSTEMS</small></span>
      </NavLink>
      <div className="sidebar-mission"><span className="eyebrow">MISSION WORKSPACE</span>
        <strong>{mission?.name || 'Crew workspace'}</strong><span className="muted">Fictional mission environment</span></div>
      <span className="nav-caption">WORKSPACE</span>
      <nav aria-label="Main navigation" id="main-navigation">
        {navigation.map(({ path, label, icon: Icon }) => <NavLink key={path} to={path} end={path === '/'} onClick={() => setMenuOpen(false)}
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Icon size={18} strokeWidth={1.65} /><span>{label}</span></NavLink>)}
      </nav>
      <div className="sidebar-bottom"><div className="protocol-mark"><Shield size={17} />Designed around the crew</div>
        <p>Monitor. Assess.<br />Understand. Act.</p><span className="version">ASTROGUARD / EDUCATIONAL PROTOTYPE</span></div>
    </aside>
    <div className="workspace">
      <header className="topbar">
        <div className="breadcrumb"><button className="icon-button mobile-menu" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
          aria-expanded={menuOpen} aria-controls="main-navigation" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={21} /> : <Menu size={21} />}</button>
          <span>CREW WORKSPACE</span><span className="slash">/</span><strong>{current?.label || 'Page not found'}</strong></div>
        <div className="header-right"><span className={`connection ${connected ? 'connected' : ''}`} role="status"><i />
          {data.status === 'loading' ? 'Connecting' : connected ? 'API connected' : 'API unavailable'}</span><DemoBadge /></div>
      </header>
      <main id="main-content" tabIndex={-1}>
        <div className="workspace-toolbar"><div className="eyebrow"><span className="tiny-cross">+</span> PERSONAL HEALTH WORKSPACE</div>
          <AstronautSelector astronauts={data.astronauts} selectedId={data.selectedId} onSelect={data.setSelectedId} disabled={data.status !== 'ready'} /></div>
        <Outlet context={data} />
      </main>
      <footer className="footer"><span><span className="footer-dot" />Fictional data · Educational prototype</span>
        <span>Not a medical device or a substitute for crew medical care.<ArrowUpRight size={13} aria-hidden="true" /></span></footer>
    </div>
  </div>
}
