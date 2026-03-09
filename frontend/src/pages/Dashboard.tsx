import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Upload, 
  FileText, 
  Sparkles, 
  Calendar,
  TrendingUp,
  Clock,
  CheckCircle
} from 'lucide-react'
import { contentService, scheduleService, styleService } from '../services/api'

export default function Dashboard() {
  const [stats, setStats] = useState({
    contentCount: 0,
    generatedCount: 0,
    scheduledCount: 0,
    styleProfileReady: false
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      const [contentData, scheduleData, styleData] = await Promise.all([
        contentService.listContent(100, 0).catch(() => ({ items: [] })),
        scheduleService.listSchedules().catch(() => ({ schedules: [] })),
        styleService.getStyleProfile().catch(() => ({ status: 'incomplete' }))
      ])

      setStats({
        contentCount: contentData.items?.length || 0,
        generatedCount: 0, // Would need to track this
        scheduledCount: scheduleData.schedules?.length || 0,
        styleProfileReady: styleData.status === 'ready'
      })
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const quickActions = [
    {
      title: 'Upload Content',
      description: 'Add new video, audio, or text',
      icon: Upload,
      href: '/content',
      color: 'primary'
    },
    {
      title: 'Build Style Profile',
      description: 'Upload your writing samples',
      icon: FileText,
      href: '/style-profile',
      color: 'secondary'
    },
    {
      title: 'Generate Content',
      description: 'Repurpose for social media',
      icon: Sparkles,
      href: '/generate',
      color: 'primary'
    },
    {
      title: 'Schedule Posts',
      description: 'Plan your content calendar',
      icon: Calendar,
      href: '/schedule',
      color: 'secondary'
    }
  ]

  const statCards = [
    {
      title: 'Content Uploaded',
      value: stats.contentCount,
      icon: FileText,
      color: 'bg-primary-100 text-primary-600'
    },
    {
      title: 'Posts Generated',
      value: stats.generatedCount,
      icon: Sparkles,
      color: 'bg-secondary-100 text-secondary-600'
    },
    {
      title: 'Scheduled Posts',
      value: stats.scheduledCount,
      icon: Clock,
      color: 'bg-primary-100 text-primary-600'
    },
    {
      title: 'Style Profile',
      value: stats.styleProfileReady ? 'Ready' : 'Setup',
      icon: CheckCircle,
      color: stats.styleProfileReady 
        ? 'bg-green-100 text-green-600' 
        : 'bg-neutral-100 text-neutral-600'
    }
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-neutral-800">Dashboard</h1>
        <p className="text-neutral-600 mt-2">
          Welcome back! Here's what's happening with your content.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.title} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-neutral-600">{stat.title}</p>
                  <p className="text-2xl font-bold text-neutral-800 mt-2">
                    {stat.value}
                  </p>
                </div>
                <div className={`p-3 rounded-lg ${stat.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.title}
                to={action.href}
                className="card hover:shadow-md transition-shadow group"
              >
                <div className={`inline-flex p-3 rounded-lg mb-4 ${
                  action.color === 'primary' 
                    ? 'bg-primary-100 text-primary-600 group-hover:bg-primary-200' 
                    : 'bg-secondary-100 text-secondary-600 group-hover:bg-secondary-200'
                } transition-colors`}>
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                  {action.title}
                </h3>
                <p className="text-sm text-neutral-600">{action.description}</p>
              </Link>
            )
          })}
        </div>
      </div>

      {/* Getting Started */}
      {!stats.styleProfileReady && (
        <div className="card bg-gradient-to-r from-primary-50 to-secondary-50 border-primary-200">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <TrendingUp className="w-8 h-8 text-primary-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                Complete Your Style Profile
              </h3>
              <p className="text-neutral-600 mb-4">
                Upload at least 3 writing samples to help our AI learn your unique voice and style.
                This will make your generated content sound more authentic.
              </p>
              <Link to="/style-profile" className="btn-primary inline-block">
                Set Up Style Profile
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
