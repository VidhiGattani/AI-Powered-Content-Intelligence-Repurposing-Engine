import { useState, useEffect } from 'react'
import { Calendar, Clock, Trash2, AlertCircle, CheckCircle, Mail } from 'lucide-react'
import { scheduleService } from '../services/api'
import { format } from 'date-fns'

const PLATFORMS = [
  { id: 'LINKEDIN', name: 'LinkedIn' },
  { id: 'TWITTER', name: 'Twitter' },
  { id: 'INSTAGRAM', name: 'Instagram' },
  { id: 'YOUTUBE_SHORTS', name: 'YouTube Shorts' },
]

export default function Schedule() {
  const [schedules, setSchedules] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [availableContent, setAvailableContent] = useState<any[]>([])

  // Form state
  const [generatedContentId, setGeneratedContentId] = useState('')
  const [platform, setPlatform] = useState('')
  const [scheduledTime, setScheduledTime] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    loadSchedules()
    loadAvailableContent()
  }, [])

  const loadSchedules = async () => {
    try {
      const data = await scheduleService.listSchedules()
      setSchedules(data.schedules || [])
    } catch (err: any) {
      console.error('Failed to load schedules:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableContent = async () => {
    try {
      // Get generated content from localStorage (mock mode)
      const stored = localStorage.getItem('mock_generated')
      if (stored) {
        const generated = JSON.parse(stored)
        setAvailableContent(generated)
      }
    } catch (err) {
      console.error('Failed to load available content:', err)
    }
  }

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setCreating(true)

    try {
      const result = await scheduleService.createSchedule(
        generatedContentId,
        platform,
        scheduledTime,
        'Asia/Kolkata' // Fixed to IST
      )
      setSuccess(result.message || 'Schedule created successfully! Confirmation email sent.')
      setGeneratedContentId('')
      setPlatform('')
      setScheduledTime('')
      loadSchedules()
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to create schedule')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return

    try {
      await scheduleService.deleteSchedule(id)
      setSuccess('Schedule deleted successfully')
      loadSchedules()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete schedule')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-neutral-800">Schedule Posts</h1>
        <p className="text-neutral-600 mt-2">
          Plan and schedule your content for optimal engagement (Indian Standard Time)
        </p>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-2 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {success && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-start">
          <CheckCircle className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-green-700">{success}</p>
            {success.includes('email') && (
              <div className="flex items-center mt-2 text-xs text-green-600">
                <Mail className="w-4 h-4 mr-1" />
                Email notification sent to your registered email
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Schedule Form */}
      <div className="card">
        <h2 className="text-xl font-semibold text-neutral-800 mb-6">
          Create New Schedule
        </h2>
        
        {availableContent.length === 0 ? (
          <div className="text-center py-8 bg-neutral-50 rounded-lg">
            <AlertCircle className="w-12 h-12 text-neutral-400 mx-auto mb-3" />
            <p className="text-neutral-600 font-medium">No generated content available</p>
            <p className="text-sm text-neutral-500 mt-1">
              Generate content first from the Generate page
            </p>
          </div>
        ) : (
          <form onSubmit={handleCreateSchedule} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Select Generated Content
                </label>
                <select
                  value={generatedContentId}
                  onChange={(e) => {
                    setGeneratedContentId(e.target.value)
                    // Auto-select platform based on content
                    const selected = availableContent.find(c => c.generated_id === e.target.value)
                    if (selected) setPlatform(selected.platform)
                  }}
                  className="input"
                  required
                >
                  <option value="">Choose content to schedule</option>
                  {availableContent.map((content) => (
                    <option key={content.generated_id} value={content.generated_id}>
                      {content.platform} - {content.text.substring(0, 60)}... ({content.status})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-neutral-500 mt-1">
                  Select from your generated content
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Platform
                </label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="input"
                  required
                  disabled={!!generatedContentId}
                >
                  <option value="">Select platform</option>
                  {PLATFORMS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-neutral-500 mt-1">
                  Auto-filled from selected content
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Scheduled Time (IST)
                </label>
                <input
                  type="datetime-local"
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  className="input"
                  required
                />
                <p className="text-xs text-neutral-500 mt-1">
                  Indian Standard Time (Asia/Kolkata)
                </p>
              </div>
            </div>

            <div className="flex items-start p-4 bg-primary-50 border border-primary-200 rounded-lg">
              <Mail className="w-5 h-5 text-primary-600 mr-3 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-primary-700">
                <p className="font-medium">Email Notification</p>
                <p className="mt-1">You'll receive a confirmation email when the schedule is created.</p>
              </div>
            </div>

            <button
              type="submit"
              disabled={creating}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? 'Creating...' : 'Create Schedule & Send Notification'}
            </button>
          </form>
        )}
      </div>

      {/* Scheduled Posts */}
      <div className="card">
        <h2 className="text-xl font-semibold text-neutral-800 mb-6">
          Scheduled Posts ({schedules.length})
        </h2>

        {schedules.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
            <p className="text-neutral-600">No scheduled posts yet</p>
            <p className="text-sm text-neutral-500 mt-2">
              Create your first schedule to plan your content
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {schedules.map((schedule) => (
              <div
                key={schedule.schedule_id}
                className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors"
              >
                <div className="flex items-center flex-1 min-w-0">
                  <div className="flex-shrink-0 w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                    <Calendar className="w-5 h-5 text-primary-600" />
                  </div>
                  <div className="ml-4 flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-neutral-800">
                        {schedule.platform_name || schedule.platform}
                      </span>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        schedule.status === 'scheduled'
                          ? 'bg-primary-100 text-primary-700'
                          : schedule.status === 'sent'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-neutral-200 text-neutral-700'
                      }`}>
                        {schedule.status}
                      </span>
                      {schedule.notification_sent && (
                        <span className="text-xs text-green-600 flex items-center">
                          <Mail className="w-3 h-3 mr-1" />
                          Notified
                        </span>
                      )}
                    </div>
                    <div className="flex items-center text-xs text-neutral-500 mt-1">
                      <Clock className="w-3 h-3 mr-1" />
                      {schedule.scheduled_time 
                        ? format(new Date(schedule.scheduled_time), 'MMM d, yyyy h:mm a')
                        : 'Not scheduled'} IST
                    </div>
                    {schedule.content_preview && (
                      <p className="text-xs text-neutral-500 mt-1 truncate">
                        {schedule.content_preview}
                      </p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(schedule.schedule_id)}
                  className="p-2 text-neutral-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors ml-4"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Optimal Times Info */}
      <div className="card bg-secondary-50 border-secondary-200">
        <h3 className="text-lg font-semibold text-neutral-800 mb-4">
          Best Times to Post (IST)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium text-neutral-700 mb-2">LinkedIn</p>
            <p className="text-sm text-neutral-600">Tuesday-Thursday, 9 AM - 12 PM</p>
          </div>
          <div>
            <p className="text-sm font-medium text-neutral-700 mb-2">Twitter</p>
            <p className="text-sm text-neutral-600">Monday-Friday, 8 AM - 10 AM</p>
          </div>
          <div>
            <p className="text-sm font-medium text-neutral-700 mb-2">Instagram</p>
            <p className="text-sm text-neutral-600">Wednesday-Friday, 11 AM - 1 PM</p>
          </div>
          <div>
            <p className="text-sm font-medium text-neutral-700 mb-2">YouTube Shorts</p>
            <p className="text-sm text-neutral-600">Friday-Sunday, 6 PM - 9 PM</p>
          </div>
        </div>
      </div>
    </div>
  )
}
