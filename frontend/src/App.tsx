import { useState } from 'react';
import { AnalyzeTab } from './components/AnalyzeTab';
import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { IssueTab } from './components/IssueTab';
import { PageHero } from './components/PageHero';
import { QueryTab } from './components/QueryTab';
import { StatusTab } from './components/StatusTab';
import { SybolBackground } from './components/SybolBackground';
import { TabNav, type TabId } from './components/TabNav';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('analyze');

  return (
    <div className="app">
      <SybolBackground />
      <Header />
      <main className="app-main">
        <PageHero activeTab={activeTab} />
        <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
        <div className="app-content">
          {activeTab === 'analyze' && <AnalyzeTab />}
          {activeTab === 'query' && <QueryTab />}
          {activeTab === 'issue' && <IssueTab />}
          {activeTab === 'status' && <StatusTab />}
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default App;
