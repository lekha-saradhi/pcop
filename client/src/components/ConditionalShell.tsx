'use client';

import { usePathname } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';

const PUBLIC_ROUTES = ['/', '/login'];

export default function ConditionalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_ROUTES.includes(pathname);

  if (isPublic) return <>{children}</>;

  return (
    <div className="flex min-h-screen bg-[#f8fafc]">
      <Sidebar />
      <main className="flex-1 ml-[220px] min-h-screen overflow-x-hidden">
        {children}
      </main>
    </div>
  );
}
