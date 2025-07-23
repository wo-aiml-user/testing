# REST Express Chat Application

## Overview

This is a full-stack web application built with React on the frontend and Express.js on the backend. It serves as a chat interface for a workflow-based PDF processing system. The application allows users to upload PDF files, start interactive workflows, and maintain conversations with an AI assistant through a FastAPI backend service.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **Routing**: Wouter for lightweight client-side routing
- **State Management**: React Query (TanStack Query) for server state management
- **UI Components**: Radix UI primitives with shadcn/ui styling system
- **Styling**: Tailwind CSS with custom dark theme
- **Form Handling**: React Hook Form with Zod validation

### Backend Architecture
- **Framework**: Express.js with TypeScript
- **Database**: PostgreSQL with Drizzle ORM
- **Session Management**: Express sessions with PostgreSQL store
- **API Pattern**: RESTful API with proxy to FastAPI backend
- **Build System**: ESBuild for production bundling

### Key Components

#### Frontend Components
- **ChatInterface**: Main chat UI with file upload, message history, and sidebar
- **UI Components**: Comprehensive set of reusable components (buttons, inputs, dialogs, etc.)
- **Custom Hooks**: `useChat` for chat state management, `useToast` for notifications

#### Backend Components
- **Routes**: API proxy layer that forwards requests to FastAPI backend
- **Storage**: In-memory storage implementation with user management
- **Vite Integration**: Development server with HMR support

#### Shared Components
- **Schema**: Zod schemas for type-safe API communication
- **Types**: TypeScript definitions for chat messages, sessions, and folders

## Data Flow

1. **File Upload**: User uploads PDF → Frontend sends to `/api/upload` → Proxied to FastAPI backend
2. **Chat Interaction**: User sends message → Frontend calls `/api/sessions/{id}/input` → Proxied to FastAPI
3. **State Management**: React Query manages API state with local storage persistence
4. **Session Persistence**: Chat history and active sessions stored in localStorage

## External Dependencies

### Frontend Dependencies
- **React Ecosystem**: React, React DOM, React Query
- **UI Libraries**: Radix UI components, Lucide React icons
- **Styling**: Tailwind CSS, class-variance-authority, clsx
- **Form Handling**: React Hook Form, Hookform resolvers
- **Utilities**: date-fns, embla-carousel

### Backend Dependencies
- **Express.js**: Core server framework
- **Database**: Drizzle ORM with PostgreSQL driver (@neondatabase/serverless)
- **Session Management**: connect-pg-simple for PostgreSQL sessions
- **Development**: tsx for TypeScript execution, esbuild for building

### Development Tools
- **TypeScript**: Full type safety across the stack
- **Vite**: Fast development server with HMR
- **ESBuild**: Fast production builds
- **Replit Integration**: Runtime error overlay and cartographer plugins

## Deployment Strategy

### Development Environment
- **Frontend**: Vite dev server with HMR on port 3000
- **Backend**: Express server with tsx runtime on port 8000
- **Database**: PostgreSQL (Neon serverless in production)

### Production Build
- **Frontend**: Vite builds to `dist/public` directory
- **Backend**: ESBuild bundles server code to `dist/index.js`
- **Static Serving**: Express serves built frontend files
- **Environment**: NODE_ENV=production with optimized builds

### Configuration
- **Database**: Configured via DATABASE_URL environment variable
- **Backend Integration**: BACKEND_URL environment variable for FastAPI proxy
- **Session Storage**: PostgreSQL-backed sessions for production scalability

### Key Architectural Decisions

1. **Proxy Architecture**: Express acts as a proxy to FastAPI backend, allowing for gradual migration and service separation
2. **Client-Side State**: React Query with localStorage persistence for offline-first chat experience
3. **Component Library**: shadcn/ui provides consistent, accessible UI components
4. **Type Safety**: Full TypeScript coverage with shared schemas between frontend and backend
5. **Dark Theme**: Custom dark theme optimized for chat interface usability
6. **Responsive Design**: Mobile-first approach with adaptive layouts