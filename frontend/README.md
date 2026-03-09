# Content Repurposing Platform - Frontend Dashboard

Professional React + TypeScript dashboard with sober pastel design.

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment file
copy .env.example .env

# Edit .env and set your API Gateway URL
# VITE_API_URL=https://your-api-gateway-url.amazonaws.com

# Start development server
npm run dev
```

Visit `http://localhost:3000`

## Features

- 🎨 Professional pastel design (blues, purples, neutrals)
- 🔐 Secure authentication (JWT tokens)
- 📊 Dashboard with stats and quick actions
- ✍️ Style profile management
- 📁 Content library with upload
- ✨ AI content generation
- 📅 Post scheduling
- 📱 Fully responsive

## Tech Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios
- Lucide Icons

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── components/     # Reusable components
│   └── Layout.tsx  # Main layout with sidebar
├── contexts/       # React contexts
│   └── AuthContext.tsx
├── pages/          # Page components
│   ├── Login.tsx
│   ├── Signup.tsx
│   ├── Dashboard.tsx
│   ├── StyleProfile.tsx
│   ├── ContentLibrary.tsx
│   ├── Generate.tsx
│   └── Schedule.tsx
├── services/       # API services
│   └── api.ts
├── App.tsx         # App root
├── main.tsx        # Entry point
└── index.css       # Global styles
```

## Design System

### Colors
- Primary: Soft blues (#0ea5e9)
- Secondary: Gentle purples (#a855f7)
- Neutral: Warm grays
- Success: Soft green
- Error: Soft red

### Components
- Cards with rounded corners
- Smooth transitions
- Clear visual hierarchy
- Accessible color contrast

## Environment Variables

Create a `.env` file:

```
VITE_API_URL=https://your-api-gateway-url.amazonaws.com
```

## Building for Production

```bash
npm run build
```

Output will be in `dist/` directory.

Deploy to:
- AWS S3 + CloudFront
- Vercel
- Netlify
- Any static hosting service

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
