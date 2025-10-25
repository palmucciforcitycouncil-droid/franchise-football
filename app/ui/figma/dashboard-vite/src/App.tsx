// App.tsx - Updated to showcase Stats Page
import React, { useState } from 'react';
import { StatsPage } from './components/StatsPage';
import { Button } from './components/ui/button';

export default function App() {
  const [currentPage, setCurrentPage] = useState('stats');

  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'roster', label: 'Roster' },
    { id: 'staff', label: 'Staff' },
    { id: 'gm-desk', label: 'GM Desk' },
    { id: 'draft', label: 'Draft' },
    { id: 'playoffs', label: 'Playoffs' },
    { id: 'stats', label: 'Stats' },
    { id: 'hof', label: 'HOF' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">Franchise Football</h1>
            </div>
            
            <nav className="flex space-x-8">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentPage === item.id
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto">
        {currentPage === 'stats' ? (
          <StatsPage />
        ) : (
          <div className="p-8 text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              {navItems.find(item => item.id === currentPage)?.label} Page
            </h2>
            <p className="text-gray-600 mb-6">
              This page is under construction. The Stats page showcases the new Professional Football Stats Platform design.
            </p>
            <Button onClick={() => setCurrentPage('stats')}>
              View Stats Page
            </Button>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <div className="text-center text-gray-500">
            <p>Professional Football Stats Platform - Stats Page Redesign</p>
            <p className="mt-2 text-sm">
              Designed for Sports Analysts, Scouts, and Power Users
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}