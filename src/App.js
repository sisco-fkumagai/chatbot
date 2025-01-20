import React from 'react';
import Header from './components/Header.js';
import ChatBot from './components/ChatBot.js';
import './App.css';

function App() {
  return (
    <div className="App">
      <Header />
      <main>
        <ChatBot />
      </main>
    </div>
  );
}

export default App;
