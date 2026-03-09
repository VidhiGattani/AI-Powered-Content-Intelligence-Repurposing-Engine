import { useState, useEffect } from 'react'
import { Upload, FileText, Video, Music, Trash2, AlertCircle, CheckCircle } from 'lucide-react'
import { contentService } from '../services/api'
import { format } from 'date-fns'

export default function ContentLibrary() {
  const [contents, setContents] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadContents()
  }, [])

  const loadContents = async () => {
    try {
      const data = await contentService.listContent(100, 0)
      setContents(data.items || [])
    } catch (err: any) {
      console.error('Failed to load contents:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError('')
    setSuccess('')
    setUploading(true)

    try {
      const reader = new FileReader()
      reader.onload = async (event) => {
        const content = btoa(event.target?.result as string)
        await contentService.uploadContent(file.name, content)
        setSuccess('Content uploaded successfully!')
        loadContents()
      }
      reader.readAsBinaryString(file)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this content?')) return

    try {
      await contentService.deleteContent(id)
      setSuccess('Content deleted successfully')
      loadContents()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete content')
    }
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    if (['mp4', 'mov', 'avi'].includes(ext || '')) return Video
    if (['mp3', 'wav'].includes(ext || '')) return Music
    return FileText
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-800">Content Library</h1>
          <p className="text-neutral-600 mt-2">
            Upload and manage your content for repurposing
          </p>
        </div>
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
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      {/* Upload Section */}
      <div className="card">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          Upload New Content
        </h2>
        <p className="text-neutral-600 mb-6">
          Upload videos, audio files, or text documents to repurpose into social media content.
          Supported formats: MP4, MOV, AVI, MP3, WAV, TXT, MD, PDF
        </p>

        <label className="block">
          <div className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center hover:border-primary-400 transition-colors cursor-pointer">
            <Upload className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
            <p className="text-neutral-700 font-medium mb-2">
              Click to upload or drag and drop
            </p>
            <p className="text-sm text-neutral-500">
              Video, Audio, or Text files (max 100MB)
            </p>
          </div>
          <input
            type="file"
            className="hidden"
            accept=".mp4,.mov,.avi,.mp3,.wav,.txt,.md,.pdf"
            onChange={handleFileUpload}
            disabled={uploading}
          />
        </label>

        {uploading && (
          <div className="mt-4 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            <p className="text-sm text-neutral-600 mt-2">Uploading and processing...</p>
          </div>
        )}
      </div>

      {/* Content List */}
      <div className="card">
        <h2 className="text-xl font-semibold text-neutral-800 mb-6">
          Your Content ({contents.length})
        </h2>

        {contents.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
            <p className="text-neutral-600">No content uploaded yet</p>
            <p className="text-sm text-neutral-500 mt-2">
              Upload your first piece of content to get started
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {contents.map((content) => {
              const Icon = getFileIcon(content.filename)
              return (
                <div
                  key={content.content_id}
                  className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors"
                >
                  <div className="flex items-center flex-1 min-w-0">
                    <div className="flex-shrink-0 w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                      <Icon className="w-5 h-5 text-primary-600" />
                    </div>
                    <div className="ml-4 flex-1 min-w-0">
                      <p className="text-sm font-medium text-neutral-800 truncate">
                        {content.filename}
                      </p>
                      <p className="text-xs text-neutral-500 mt-1">
                        Uploaded {content.upload_date ? format(new Date(content.upload_date), 'MMM d, yyyy') : 'Recently'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                      content.status === 'transcribed' 
                        ? 'bg-green-100 text-green-700'
                        : content.status === 'processing'
                        ? 'bg-primary-100 text-primary-700'
                        : 'bg-neutral-200 text-neutral-700'
                    }`}>
                      {content.status || 'uploaded'}
                    </span>
                    <button
                      onClick={() => handleDelete(content.content_id)}
                      className="p-2 text-neutral-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
