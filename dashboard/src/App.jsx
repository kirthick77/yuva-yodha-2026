import React, { useState } from 'react'
import LivePowerDraw from './pages/LivePowerDraw.jsx'
import FaultAlerts from './pages/FaultAlerts.jsx'
import ScheduleView from './pages/ScheduleView.jsx'
import AuditReport from './pages/AuditReport.jsx'
import CarbonReport from './pages/CarbonReport.jsx'

const NAV_ITEMS = [
  { id: 'live-power', label: 'Live Power Draw', icon: '⚡' },
  { id: 'fault-alerts', label: 'Fault Alerts', icon: '🔔' },
  { id: 'schedule', label: 'Schedule View', icon: '📅' },
  { id: 'audit', label: 'Audit Report', icon: '📋' },
  { id: 'carbon', label: 'Carbon Report', icon: '🌿' },
]

const PAGE_MAP = {
  'live-power': LivePowerDraw,
  'fault-alerts': FaultAlerts,
  'schedule': ScheduleView,
  'audit': AuditReport,
  'carbon': CarbonReport,
}

export default function App() {
  const [activePage, setActivePage] = useState('live-power')
  const ActiveComponent = PAGE_MAP[activePage]

  return (
    <>
      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside className="sidebar" id="sidebar">
        <div className="sidebar-brand">
          <h1>
            <span className="brand-icon">⚙</span>
            <span>EnergyOS</span>
          </h1>
          <p>Factory Monitoring</p>
        </div>

        <nav className="sidebar-nav" id="main-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              id={`nav-${item.id}`}
              className={`nav-item ${activePage === item.id ? 'active' : ''}`}
              onClick={() => setActivePage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          Schneider 2026 Hackathon Demo
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────── */}
      <main className="main-content" id="main-content">
        <div className="fade-in" key={activePage}>
          <ActiveComponent />
        </div>
      </main>
    </>
  )
}
