'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, Users, Activity, BrainCircuit,
  Send, BarChart3, Workflow, Shield, LogOut,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

const NAV_GROUPS = [
  {
    label: null,
    items: [{ href: '/dashboard', label: 'Overview', icon: LayoutDashboard }],
  },
  {
    label: 'Intelligence',
    items: [
      { href: '/customers', label: 'Customers',      icon: Users      },
      { href: '/signals',   label: 'Signal Monitor', icon: Activity   },
    ],
  },
  {
    label: 'Models',
    items: [
      { href: '/models', label: 'CHRONOS Models', icon: BrainCircuit },
    ],
  },
  {
    label: 'Operations',
    items: [
      { href: '/outreach',  label: 'Outreach Hub', icon: Send      },
      { href: '/analytics', label: 'Analytics',    icon: BarChart3 },
      { href: '/pipeline',  label: 'Pipeline',     icon: Workflow  },
    ],
  },
  {
    label: 'Admin',
    items: [
      { href: '/reviews', label: 'Reviews', icon: Shield, roles: ['manager', 'admin'] as const },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const initials = (name: string) =>
    name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

  const handleLogout = () => { logout(); window.location.href = '/login'; };

  const isActive = (href: string) =>
    href === '/dashboard'
      ? pathname === '/dashboard'
      : pathname === href || pathname.startsWith(href + '/');

  return (
    <aside className="w-[220px] shrink-0 h-screen fixed top-0 left-0 flex flex-col bg-[#0f2d5c] text-white select-none z-40">
      {/* Logo */}
      <div className="h-14 flex items-center px-5 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-white flex items-center justify-center">
            <span className="text-[#0f2d5c] text-[10px] font-black tracking-tight">NG</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[13px] font-bold tracking-tight leading-tight">PCOP</span>
            <span className="text-[9px] text-white/50 leading-tight">NextGenHacks · 2026</span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter(item => {
            if (!('roles' in item) || !item.roles) return true;
            return user && item.roles.includes(user.role as 'manager' | 'admin');
          });
          if (!visibleItems.length) return null;
          return (
            <div key={group.label ?? 'top'} className="mb-4">
              {group.label && (
                <p className="text-[9px] font-semibold uppercase tracking-widest text-white/35 px-3 py-1 mb-0.5">
                  {group.label}
                </p>
              )}
              {visibleItems.map(item => {
                const Icon  = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium mb-0.5 transition-all duration-150 ${
                      active
                        ? 'bg-white/12 text-white'
                        : 'text-white/60 hover:text-white hover:bg-white/8'
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-white' : 'text-white/50'}`} />
                    <span>{item.label}</span>
                    {active && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-sky-400" />
                    )}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-white/10">
        <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
          <div className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center text-[10px] font-bold shrink-0">
            {user ? initials(user.name) : 'U'}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-[11px] font-semibold text-white truncate">{user?.name || 'User'}</span>
            <span className="text-[9px] text-white/40 capitalize">{user?.role || 'guest'}</span>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-1.5 rounded-md text-[12px] text-white/50 hover:text-white hover:bg-white/8 transition-all duration-150"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
