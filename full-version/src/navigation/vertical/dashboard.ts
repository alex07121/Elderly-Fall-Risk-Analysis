export default [
  {
    title: 'Fall Risk System',
    icon: { icon: 'tabler-smart-home' },
    children: [
      {
        title: 'Role Selection',
        to: 'root',
        icon: { icon: 'tabler-layout-dashboard' },
      },
      {
        title: 'Personal Risk Assessment',
        to: 'dashboards-fall-risk',
        icon: { icon: 'tabler-user-heart' },
      },
      {
        title: 'Care Team Dashboard',
        to: 'dashboards-fall-risk-dashboard',
        icon: { icon: 'tabler-activity-heartbeat' },
      },
    ],
    badgeContent: 'AI',
    badgeClass: 'bg-primary',
  },
]
