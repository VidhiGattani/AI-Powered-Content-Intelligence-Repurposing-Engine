import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { 
  LayoutDashboard, 
  FileText, 
  Upload, 
  Sparkles, 
  Calendar, 
  LogOut,
  User
} from 'lucide-react'

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Style Profile', href: '/style-profile', icon: User },
    { name: 'Content Library', href: '/content', icon: FileText },
    { name: 'Generate', href: '/generate', icon: Sparkles },
    { name: 'Schedule', href: '/schedule', icon: Calendar },
  ]

  const isActive = (path: string) => {
    return location.pathname === path
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-secondary-50 to-neutral-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-neutral-200 shadow-sm">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center h-16 px-6 border-b border-neutral-200">
            <Upload className="w-8 h-8 text-primary-500" />
            <span className="ml-3 text-xl font-semibold text-neutral-800">
              ContentAI
            </span>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                    isActive(item.href)
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-neutral-200">
            <div className="flex items-center justify-between px-4 py-3 bg-neutral-50 rounded-lg">
              <div className="flex items-center min-w-0">
                <div className="flex-shrink-0 w-8 h-8 bg-primary-200 rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium text-primary-700">
                    {user?.name?.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="ml-3 min-w-0">
                  <p className="text-sm font-medium text-neutral-800 truncate">
                    {user?.name}
                  </p>
                  <p className="text-xs text-neutral-500 truncate">
                    {user?.email}
                  </p>
                </div>
              </div>
              <button
                onClick={logout}
                className="flex-shrink-0 p-2 text-neutral-500 hover:text-neutral-700 hover:bg-neutral-200 rounded-lg transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
