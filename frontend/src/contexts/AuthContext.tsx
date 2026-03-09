import React, { createContext, useContext, useState, useEffect } from 'react'
import { authService } from '../services/api'

interface User {
  user_id: string
  email: string
  name: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const userData = localStorage.getItem('user')
    if (token && userData) {
      setUser(JSON.parse(userData))
      setIsAuthenticated(true)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const response = await authService.signin(email, password)
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('user', JSON.stringify({
      user_id: response.user_id,
      email,
      name: response.name || email
    }))
    setUser({
      user_id: response.user_id,
      email,
      name: response.name || email
    })
    setIsAuthenticated(true)
  }

  const signup = async (email: string, password: string, name: string) => {
    await authService.signup(email, password, name)
    // Auto-login after signup
    await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
