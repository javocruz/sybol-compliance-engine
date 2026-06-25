import { useState } from 'react';
import { AnalyzeTab } from './components/AnalyzeTab';
import { AuditTab } from './components/AuditTab';
import { Header } from './components/Header';
import { IssueTab } from './components/IssueTab';
import { QueryTab } from './components/QueryTab';
import { TabNav, type TabId } from './components/TabNav';

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('analyze');
  const [auditRecordId, setAuditRecordId] = useState<string | null>(null);

  const viewAuditRecord = (recordId: string) => {
    setAuditRecordId(recordId);
    setActiveTab('audit');
  };

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    if (tab !== 'audit') {
      setAuditRecordId(null);
    }
  };

  return (
    <div className="app">
      <Header />
      <main className="app-main">
        <TabNav activeTab={activeTab} onTabChange={handleTabChange} />
        {activeTab === 'analyze' && <AnalyzeTab />}
        {activeTab === 'query' && <QueryTab />}
        {activeTab === 'issue' && (
          <IssueTab onViewAuditRecord={viewAuditRecord} />
        )}
        {activeTab === 'audit' && (
          <AuditTab initialRecordId={auditRecordId} />
        )}
      </main>
    </div>
  );
}

export default App;
