import { useState } from 'react';
import { AnalyzeTab } from './components/AnalyzeTab';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { IssueTab } from './components/IssueTab';
import { QueryTab } from './components/QueryTab';
import { StatusTab } from './components/StatusTab';
import { TabNav, type TabId } from './components/TabNav';
import './App.css';

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
        {activeTab === 'status' && <StatusTab />}
      </main>
      <Footer />
    </div>
  );
}

export default App;
