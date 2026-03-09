import { useState, useEffect } from 'react'
import { Sparkles, AlertCircle, CheckCircle, Copy, RefreshCw } from 'lucide-react'
import { contentService, generationService } from '../services/api'

const PLATFORMS = [
  { id: 'LINKEDIN', name: 'LinkedIn', color: 'bg-blue-100 text-blue-700' },
  { id: 'TWITTER', name: 'Twitter', color: 'bg-sky-100 text-sky-700' },
  { id: 'INSTAGRAM', name: 'Instagram', color: 'bg-pink-100 text-pink-700' },
  { id: 'YOUTUBE_SHORTS', name: 'YouTube Shorts', color: 'bg-red-100 text-red-700' },
]

export default function Generate() {
  const [contents, setContents] = useState<any[]>([])
  const [selectedContent, setSelectedContent] = useState('')
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([])
  const [generating, setGenerating] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadContents()
  }, [])

  const loadContents = async () => {
    try {
      const data = await contentService.listContent(100, 0)
      // Show all uploaded content, regardless of processing status
      setContents(data.items || [])
    } catch (err: any) {
      console.error('Failed to load contents:', err)
    } finally {
      setLoading(false)
    }
  }

  const togglePlatform = (platformId: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(platformId)
        ? prev.filter(p => p !== platformId)
        : [...prev, platformId]
    )
  }

  const handleGenerate = async () => {
    if (!selectedContent || selectedPlatforms.length === 0) {
      setError('Please select content and at least one platform')
      return
    }

    setError('')
    setGenerating(true)
    setResults(null)

    try {
      const data = await generationService.generate(selectedContent, selectedPlatforms)
      setResults(data.results)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate content')
    } finally {
      setGenerating(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
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
        <h1 className="text-3xl font-bold text-neutral-800">Generate Content</h1>
        <p className="text-neutral-600 mt-2">
          Repurpose your content for multiple social media platforms
        </p>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-2 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Selection Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Select Content */}
        <div className="card">
          <h2 className="text-xl font-semibold text-neutral-800 mb-4">
            1. Select Content
          </h2>
          {contents.length === 0 ? (
            <p className="text-neutral-600 text-sm">
              No processed content available. Upload and process content first.
            </p>
          ) : (
            <div className="space-y-2">
              {contents.map((content) => (
                <label
                  key={content.content_id}
                  className={`flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                    selectedContent === content.content_id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-neutral-200 hover:border-neutral-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="content"
                    value={content.content_id}
                    checked={selectedContent === content.content_id}
                    onChange={(e) => setSelectedContent(e.target.value)}
                    className="mr-3"
                  />
                  <span className="text-sm font-medium text-neutral-800">
                    {content.filename}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Select Platforms */}
        <div className="card">
          <h2 className="text-xl font-semibold text-neutral-800 mb-4">
            2. Select Platforms
          </h2>
          <div className="space-y-2">
            {PLATFORMS.map((platform) => (
              <label
                key={platform.id}
                className={`flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  selectedPlatforms.includes(platform.id)
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-neutral-200 hover:border-neutral-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedPlatforms.includes(platform.id)}
                  onChange={() => togglePlatform(platform.id)}
                  className="mr-3"
                />
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${platform.color}`}>
                  {platform.name}
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Generate Button */}
      <div className="flex justify-center">
        <button
          onClick={handleGenerate}
          disabled={generating || !selectedContent || selectedPlatforms.length === 0}
          className="btn-primary px-8 py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
        >
          <Sparkles className="w-5 h-5 mr-2" />
          {generating ? 'Generating...' : 'Generate Content'}
        </button>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold text-neutral-800">Generated Content</h2>
            <div className="flex items-center text-green-600">
              <CheckCircle className="w-5 h-5 mr-2" />
              <span className="text-sm font-medium">Successfully generated</span>
            </div>
          </div>

          {Object.entries(results).map(([platform, result]: [string, any]) => {
            const platformInfo = PLATFORMS.find(p => p.id === platform)
            return (
              <div key={platform} className="card">
                <div className="flex items-center justify-between mb-4">
                  <span className={`px-4 py-2 text-sm font-medium rounded-full ${platformInfo?.color}`}>
                    {platformInfo?.name}
                  </span>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => copyToClipboard(result.text)}
                      className="p-2 text-neutral-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      title="Copy to clipboard"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    <button
                      className="p-2 text-neutral-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      title="Regenerate"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="bg-neutral-50 rounded-lg p-4">
                  <pre className="whitespace-pre-wrap text-sm text-neutral-800 font-sans">
                    {result.text}
                  </pre>
                </div>
                {result.status === 'success' && (
                  <div className="mt-4 flex items-center text-green-600 text-sm">
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Generated successfully
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
