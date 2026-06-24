import { useState } from 'react';
import { AnalyzeTab } from './components/AnalyzeTab';
import { Header } from './components/Header';
import { IssueTab } from './components/IssueTab';
import { QueryTab } from './components/QueryTab';
import { TabNav, type TabId } from './components/TabNav';

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('analyze');

  return (
    <div className="app">
      <Header />
      <main className="app-main">
        <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
        {activeTab === 'analyze' && <AnalyzeTab />}
        {activeTab === 'query' && <QueryTab />}
        {activeTab === 'issue' && <IssueTab />}
      </main>
    </div>
  );
}

export default App;
