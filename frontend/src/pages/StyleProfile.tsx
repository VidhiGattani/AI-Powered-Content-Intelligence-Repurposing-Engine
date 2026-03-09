import { useState, useEffect } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Trash2, Eye, X } from 'lucide-react'
import { styleService } from '../services/api'

export default function StyleProfile() {
  const [profile, setProfile] = useState<any>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)
  const [viewingContent, setViewingContent] = useState<any>(null)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const data = await styleService.getStyleProfile()
      setProfile(data)
    } catch (err: any) {
      console.error('Failed to load profile:', err)
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
        const content = event.target?.result as string
        await styleService.uploadStyleContent(file.name, content)
        setSuccess('Style content uploaded successfully!')
        loadProfile()
      }
      reader.readAsText(file)
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this content?')) return
    
    try {
      await styleService.deleteStyleContent(id)
      setSuccess('Content deleted successfully!')
      loadProfile()
    } catch (err: any) {
      setError(err.message || 'Failed to delete content')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  const isReady = profile?.status === 'ready'
  const contentCount = profile?.content_count || 0
  const uploadedContents = profile?.contents || []

  return (
    <div className="max-w-4xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-neutral-800">Style Profile</h1>
        <p className="text-neutral-600 mt-2">
          Upload your writing samples to help AI learn your unique voice
        </p>
      </div>

      {/* Status Card */}
      <div className={`card ${isReady ? 'bg-green-50 border-green-200' : 'bg-primary-50 border-primary-200'}`}>
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {isReady ? (
              <CheckCircle className="w-8 h-8 text-green-600" />
            ) : (
              <AlertCircle className="w-8 h-8 text-primary-600" />
            )}
          </div>
          <div className="ml-4 flex-1">
            <h3 className="text-lg font-semibold text-neutral-800">
              {isReady ? 'Profile Ready!' : 'Profile Incomplete'}
            </h3>
            <p className="text-neutral-600 mt-1">
              {isReady
                ? 'Your style profile is ready. The AI will use these samples to match your writing style.'
                : `Upload at least 3 writing samples (${contentCount}/3 uploaded)`}
            </p>
            <div className="mt-4">
              <div className="w-full bg-neutral-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    isReady ? 'bg-green-500' : 'bg-primary-500'
                  }`}
                  style={{ width: `${Math.min((contentCount / 3) * 100, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
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

      {/* Uploaded Content List */}
      {uploadedContents.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-neutral-800 mb-4">
            Uploaded Content ({uploadedContents.length})
          </h2>
          <div className="space-y-3">
            {uploadedContents.map((content: any) => (
              <div
                key={content.id}
                className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg border border-neutral-200 hover:border-primary-300 transition-colors"
              >
                <div className="flex items-center flex-1 min-w-0">
                  <FileText className="w-5 h-5 text-primary-600 mr-3 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-neutral-800 truncate">
                      {content.filename}
                    </p>
                    <p className="text-sm text-neutral-500">
                      Uploaded {new Date(content.uploaded_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2 ml-4">
                  <button
                    onClick={() => setViewingContent(content)}
                    className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                    title="View content"
                  >
                    <Eye className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => handleDelete(content.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete content"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Section */}
      <div className="card">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          Upload Writing Samples
        </h2>
        <p className="text-neutral-600 mb-6">
          Upload articles, blog posts, or any text that represents your writing style.
          Supported formats: .txt, .md, .pdf, .doc, .docx
        </p>

        <label className="block">
          <div className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center hover:border-primary-400 transition-colors cursor-pointer">
            <Upload className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
            <p className="text-neutral-700 font-medium mb-2">
              Click to upload or drag and drop
            </p>
            <p className="text-sm text-neutral-500">
              TXT, MD, PDF, DOC, DOCX (max 10MB)
            </p>
          </div>
          <input
            type="file"
            className="hidden"
            accept=".txt,.md,.pdf,.doc,.docx"
            onChange={handleFileUpload}
            disabled={uploading}
          />
        </label>

        {uploading && (
          <div className="mt-4 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            <p className="text-sm text-neutral-600 mt-2">Uploading...</p>
          </div>
        )}
      </div>

      {/* Guidelines */}
      <div className="card bg-secondary-50 border-secondary-200">
        <h3 className="text-lg font-semibold text-neutral-800 mb-4">
          Tips for Best Results
        </h3>
        <ul className="space-y-3">
          <li className="flex items-start">
            <CheckCircle className="w-5 h-5 text-secondary-600 mr-3 flex-shrink-0 mt-0.5" />
            <span className="text-neutral-700">
              Upload at least 3 different pieces of content
            </span>
          </li>
          <li className="flex items-start">
            <CheckCircle className="w-5 h-5 text-secondary-600 mr-3 flex-shrink-0 mt-0.5" />
            <span className="text-neutral-700">
              Use content that represents your typical writing style
            </span>
          </li>
          <li className="flex items-start">
            <CheckCircle className="w-5 h-5 text-secondary-600 mr-3 flex-shrink-0 mt-0.5" />
            <span className="text-neutral-700">
              Longer samples (500+ words) work better
            </span>
          </li>
          <li className="flex items-start">
            <CheckCircle className="w-5 h-5 text-secondary-600 mr-3 flex-shrink-0 mt-0.5" />
            <span className="text-neutral-700">
              Include variety: different topics and formats
            </span>
          </li>
        </ul>
      </div>

      {/* View Content Modal */}
      {viewingContent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-neutral-200">
              <h3 className="text-xl font-semibold text-neutral-800">
                {viewingContent.filename}
              </h3>
              <button
                onClick={() => setViewingContent(null)}
                className="p-2 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto flex-1">
              <pre className="whitespace-pre-wrap text-sm text-neutral-700 font-mono">
                {viewingContent.content}
              </pre>
            </div>
            <div className="p-6 border-t border-neutral-200 flex justify-end space-x-3">
              <button
                onClick={() => handleDelete(viewingContent.id)}
                className="btn-secondary text-red-600 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </button>
              <button
                onClick={() => setViewingContent(null)}
                className="btn-primary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
