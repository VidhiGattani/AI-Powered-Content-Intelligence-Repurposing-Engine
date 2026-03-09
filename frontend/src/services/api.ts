import axios from 'axios'
import * as mockApi from './mockApi'

// Use VITE_API_URL from environment variables
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://l69mf04tsj.execute-api.us-east-1.amazonaws.com/prod'
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true' || false // Real backend enabled

export { API_BASE_URL }

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Helper to use mock or real API
const useMockOrReal = <T>(mockFn: () => Promise<T>, realFn: () => Promise<T>): Promise<T> => {
  if (MOCK_MODE) {
    console.log('Using MOCK API')
    return mockFn()
  }
  console.log('Using REAL API')
  return realFn()
}

export const authService = {
  signup: async (email: string, password: string, name: string) => {
    console.log('[API] Signup called with:', { email, name, MOCK_MODE, API_BASE_URL })
    return useMockOrReal(
      () => mockApi.mockAuthService.signup(email, password, name),
      async () => {
        console.log('[API] Making real API call to:', `${API_BASE_URL}/auth/signup`)
        console.log('[API] Request body:', { email, password })
        try {
          const response = await api.post('/auth/signup', { email, password })
          console.log('[API] Signup response:', response.data)
          return response.data
        } catch (error: any) {
          console.error('[API] Signup error:', error)
          console.error('[API] Error response:', error.response?.data)
          console.error('[API] Error status:', error.response?.status)
          throw error
        }
      }
    )
  },
  signin: async (email: string, password: string) => {
    return useMockOrReal(
      () => mockApi.mockAuthService.signin(email, password),
      async () => {
        const response = await api.post('/auth/signin', { email, password })
        return response.data
      }
    )
  },
  signout: async () => {
    return useMockOrReal(
      () => mockApi.mockAuthService.signout(),
      async () => {
        const response = await api.post('/auth/signout')
        return response.data
      }
    )
  },
}

export const styleService = {
  uploadStyleContent: async (filename: string, content: string) => {
    return useMockOrReal(
      () => mockApi.mockStyleService.uploadStyleContent(filename, content),
      async () => {
        const response = await api.post('/style-content', { filename, content })
        return response.data
      }
    )
  },
  getStyleProfile: async () => {
    return useMockOrReal(
      () => mockApi.mockStyleService.getStyleProfile(),
      async () => {
        const response = await api.get('/style-profile')
        return response.data
      }
    )
  },
  deleteStyleContent: async (id: string) => {
    return useMockOrReal(
      () => mockApi.mockStyleService.deleteStyleContent(id),
      async () => {
        const response = await api.delete(`/style-content/${id}`)
        return response.data
      }
    )
  },
}

export const contentService = {
  uploadContent: async (filename: string, content: string) => {
    return useMockOrReal(
      () => mockApi.mockContentService.uploadContent(filename, content),
      async () => {
        const response = await api.post('/content', { filename, content })
        return response.data
      }
    )
  },
  listContent: async (limit = 10, offset = 0) => {
    return useMockOrReal(
      () => mockApi.mockContentService.listContent(limit, offset),
      async () => {
        const response = await api.get('/content', { params: { limit, offset } })
        return response.data
      }
    )
  },
  getContent: async (id: string) => {
    return useMockOrReal(
      () => mockApi.mockContentService.getContent(id),
      async () => {
        const response = await api.get(`/content/${id}`)
        return response.data
      }
    )
  },
  deleteContent: async (id: string) => {
    return useMockOrReal(
      () => mockApi.mockContentService.deleteContent(id),
      async () => {
        const response = await api.delete(`/content/${id}`)
        return response.data
      }
    )
  },
}

export const generationService = {
  generate: async (contentId: string, platforms: string[]) => {
    return useMockOrReal(
      () => mockApi.mockGenerationService.generate(contentId, platforms),
      async () => {
        const response = await api.post('/generate', { content_id: contentId, platforms })
        return response.data
      }
    )
  },
  regenerate: async (id: string) => {
    return useMockOrReal(
      () => mockApi.mockGenerationService.regenerate(id),
      async () => {
        const response = await api.post(`/regenerate/${id}`)
        return response.data
      }
    )
  },
  getGenerated: async (id: string) => {
    return useMockOrReal(
      () => mockApi.mockGenerationService.getGenerated(id),
      async () => {
        const response = await api.get(`/generated/${id}`)
        return response.data
      }
    )
  },
  editContent: async (id: string, editedText: string) => {
    return useMockOrReal(
      () => mockApi.mockGenerationService.editContent(id, editedText),
      async () => {
        const response = await api.put(`/generated/${id}/edit`, { edited_text: editedText })
        return response.data
      }
    )
  },
  approveContent: async (id: string) => {
    return useMockOrReal(
      () => mockApi.mockGenerationService.approveContent(id),
      async () => {
        const response = await api.post(`/generated/${id}/approve`)
        return response.data
      }
    )
  },
}

export const seoService = {
  generateTitles: async (content: string, platform: string) => {
    return useMockOrReal(
      () => mockApi.mockSeoService.generateTitles(content, platform),
      async () => {
        const response = await api.post('/seo/titles', { content, platform })
        return response.data
      }
    )
  },
  generateHashtags: async (content: string, platform: string) => {
    return useMockOrReal(
      () => mockApi.mockSeoService.generateHashtags(content, platform),
      async () => {
        const response = await api.post('/seo/hashtags', { content, platform })
        return response.data
      }
    )
  },
  generateAltText: async (imageDescription: string) => {
    return useMockOrReal(
      () => mockApi.mockSeoService.generateAltText(imageDescription),
      async () => {
        const response = await api.post('/seo/alt-text', { image_description: imageDescription })
        return response.data
      }
    )
  },
}

export const scheduleService = {
  createSchedule: async (
    generatedContentId: string,
    platform: string,
    scheduledTime: string,
    timezone: string
  ) => {
    return useMockOrReal(
      () => mockApi.mockScheduleService.createSchedule(generatedContentId, platform, scheduledTime, timezone),
      async () => {
        const response = await api.post('/schedule', {
          generated_content_id: generatedContentId,
          platform,
          scheduled_time: scheduledTime,
          timezone,
        })
        return response.data
      }
    )
  },
  listSchedules: async () => {
    return useMockOrReal(
      () => mockApi.mockScheduleService.listSchedules(),
      async () => {
        const response = await api.get('/schedule')
        return response.data
      }
    )
  },
  deleteSchedule: async (id: string) => {
    return useMockOrReal(
      () => mockApi.mockScheduleService.deleteSchedule(id),
      async () => {
        const response = await api.delete(`/schedule/${id}`)
        return response.data
      }
    )
  },
  getOptimalTimes: async (platform: string, timezone: string) => {
    return useMockOrReal(
      () => mockApi.mockScheduleService.getOptimalTimes(platform, timezone),
      async () => {
        const response = await api.get('/schedule/optimal-times', {
          params: { platform, timezone },
        })
        return response.data
      }
    )
  },
}

export default api
