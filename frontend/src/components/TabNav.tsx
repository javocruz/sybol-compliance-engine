import './TabNav.css';

export type TabId = 'analyze' | 'query' | 'issue' | 'status';

interface TabNavProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

const TABS: { id: TabId; label: string }[] = [
  { id: 'analyze', label: 'Analyze' },
  { id: 'query', label: 'Query' },
  { id: 'issue', label: 'Issue' },
  { id: 'status', label: 'System' },
];

export function TabNav({ activeTab, onTabChange }: TabNavProps) {
  return (
    <nav className="tab-nav" aria-label="Main navigation">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`tab-nav-item${activeTab === tab.id ? ' tab-nav-item--active' : ''}`}
          onClick={() => onTabChange(tab.id)}
          aria-current={activeTab === tab.id ? 'page' : undefined}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
