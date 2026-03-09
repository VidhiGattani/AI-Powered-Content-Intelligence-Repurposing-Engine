import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import StyleProfile from './pages/StyleProfile'
import ContentLibrary from './pages/ContentLibrary'
import Generate from './pages/Generate'
import Schedule from './pages/Schedule'
import Layout from './components/Layout'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="style-profile" element={<StyleProfile />} />
            <Route path="content" element={<ContentLibrary />} />
            <Route path="generate" element={<Generate />} />
            <Route path="schedule" element={<Schedule />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App
