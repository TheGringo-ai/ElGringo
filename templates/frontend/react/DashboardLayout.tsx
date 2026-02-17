/**
 * Dashboard Layout Component
 * ==========================
 * Complete dashboard shell with sidebar, header, and content area.
 *
 * Dependencies:
 *   npm install lucide-react
 *
 * Usage:
 *   <DashboardLayout
 *     navigation={navItems}
 *     user={{ name: 'John', email: 'john@example.com' }}
 *   >
 *     <YourContent />
 *   </DashboardLayout>
 */

import React, { useState } from 'react';
import {
  Menu, X, Bell, Search, ChevronDown, LogOut, Settings, User,
  Home, Folder, Users, BarChart2, FileText, Calendar, MessageSquare,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: number;
  children?: NavItem[];
}

interface UserInfo {
  name: string;
  email: string;
  avatar?: string;
  role?: string;
}

interface DashboardLayoutProps {
  children: React.ReactNode;
  navigation: NavItem[];
  user: UserInfo;
  logo?: React.ReactNode;
  onLogout?: () => void;
}

// ============================================================================
// DEFAULT NAVIGATION
// ============================================================================

export const defaultNavigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Projects', href: '/projects', icon: Folder, badge: 3 },
  { name: 'Team', href: '/team', icon: Users },
  { name: 'Reports', href: '/reports', icon: BarChart2 },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Calendar', href: '/calendar', icon: Calendar },
  { name: 'Messages', href: '/messages', icon: MessageSquare, badge: 12 },
];

// ============================================================================
// SIDEBAR
// ============================================================================

interface SidebarProps {
  navigation: NavItem[];
  isOpen: boolean;
  currentPath?: string;
  logo?: React.ReactNode;
}

function Sidebar({ navigation, isOpen, currentPath = '/', logo }: SidebarProps) {
  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 transform transition-transform duration-200 ease-in-out
        lg:translate-x-0 lg:static lg:inset-auto
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-gray-800">
        {logo || (
          <span className="text-xl font-bold text-white">AppName</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="mt-6 px-3">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const isActive = currentPath === item.href;
            const Icon = item.icon;

            return (
              <li key={item.name}>
                <a
                  href={item.href}
                  className={`
                    flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                    ${isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'}
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="flex-1">{item.name}</span>
                  {item.badge && (
                    <span className={`
                      px-2 py-0.5 text-xs rounded-full
                      ${isActive ? 'bg-blue-500' : 'bg-gray-700'}
                    `}>
                      {item.badge}
                    </span>
                  )}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom section */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-800">
        <a
          href="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white"
        >
          <Settings className="w-5 h-5" />
          Settings
        </a>
      </div>
    </aside>
  );
}

// ============================================================================
// HEADER
// ============================================================================

interface HeaderProps {
  user: UserInfo;
  onMenuClick: () => void;
  onLogout?: () => void;
}

function Header({ user, onMenuClick, onLogout }: HeaderProps) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 flex items-center h-16 px-4 bg-white border-b border-gray-200 gap-4">
      {/* Mobile menu button */}
      <button
        onClick={onMenuClick}
        className="lg:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Search */}
      <div className="flex-1 max-w-lg">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100"
          >
            {user.avatar ? (
              <img src={user.avatar} alt="" className="w-8 h-8 rounded-full" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium text-sm">
                {user.name.charAt(0)}
              </div>
            )}
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-gray-900">{user.name}</p>
              <p className="text-xs text-gray-500">{user.role || user.email}</p>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-500" />
          </button>

          {/* Dropdown */}
          {userMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setUserMenuOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                <a
                  href="/profile"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  <User className="w-4 h-4" />
                  Profile
                </a>
                <a
                  href="/settings"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  <Settings className="w-4 h-4" />
                  Settings
                </a>
                <hr className="my-1 border-gray-200" />
                <button
                  onClick={onLogout}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

// ============================================================================
// MAIN LAYOUT
// ============================================================================

export function DashboardLayout({
  children,
  navigation,
  user,
  logo,
  onLogout,
}: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex">
        {/* Sidebar */}
        <Sidebar
          navigation={navigation}
          isOpen={sidebarOpen}
          logo={logo}
        />

        {/* Main content */}
        <div className="flex-1 flex flex-col min-h-screen">
          <Header
            user={user}
            onMenuClick={() => setSidebarOpen(!sidebarOpen)}
            onLogout={onLogout}
          />

          <main className="flex-1 p-6">
            {children}
          </main>

          {/* Footer */}
          <footer className="py-4 px-6 border-t border-gray-200 text-center text-sm text-gray-500">
            &copy; {new Date().getFullYear()} Your Company. All rights reserved.
          </footer>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// PAGE HEADER COMPONENT
// ============================================================================

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}

// ============================================================================
// STATS CARD COMPONENT
// ============================================================================

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon?: React.ElementType;
}

export function StatCard({ title, value, change, changeType = 'neutral', icon: Icon }: StatCardProps) {
  const changeColors = {
    positive: 'text-green-600 bg-green-100',
    negative: 'text-red-600 bg-red-100',
    neutral: 'text-gray-600 bg-gray-100',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {Icon && <Icon className="w-5 h-5 text-gray-400" />}
      </div>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
      {change && (
        <p className={`mt-2 text-sm font-medium px-2 py-0.5 rounded-full inline-block ${changeColors[changeType]}`}>
          {change}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

export function DashboardExample() {
  const user = {
    name: 'John Doe',
    email: 'john@example.com',
    role: 'Administrator',
  };

  return (
    <DashboardLayout
      navigation={defaultNavigation}
      user={user}
      onLogout={() => console.log('Logout')}
    >
      <PageHeader
        title="Dashboard"
        description="Welcome back, John!"
        actions={
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            New Project
          </button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <StatCard title="Total Projects" value={24} change="+12%" changeType="positive" icon={Folder} />
        <StatCard title="Team Members" value={8} change="+2" changeType="positive" icon={Users} />
        <StatCard title="Tasks Completed" value={156} change="+23%" changeType="positive" icon={FileText} />
        <StatCard title="Hours Tracked" value="1,240" change="-5%" changeType="negative" icon={Calendar} />
      </div>

      {/* Add more content here */}
    </DashboardLayout>
  );
}
