export default [
  {
    title: 'Dashboards',
    icon: { icon: 'tabler-smart-home' },
    children: [
      {
        title: 'Risk Dashboard',
        to: 'dashboards-fall-risk-dashboard',
        icon: { icon: 'tabler-activity-heartbeat' },
      },
      {
        title: 'Fall Risk XAI',
        to: 'dashboards-fall-risk',
      },
    ],
    badgeContent: '2',
    badgeClass: 'bg-error',
  },
]
