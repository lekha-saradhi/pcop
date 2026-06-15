'use client';

import Sidebar from './Sidebar';

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-[#f8fafc]">
      <Sidebar />
      <main className="flex-1 ml-[220px] min-h-screen overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
