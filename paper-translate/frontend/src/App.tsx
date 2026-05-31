import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Home } from './pages/Home';
import { Reader } from './pages/Reader';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/reader/:taskId" element={<Reader />} />
      </Routes>
    </Router>
  );
}

export default App;
