import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";
import http from 'http'; // Import the http module

// --- Main Application Setup ---
async function createServer() {
  const app = express();
  // Create an HTTP server from the Express app.
  // This is needed so Vite can hook into it for Hot Module Replacement (HMR).
  const httpServer = http.createServer(app);

  // --- Middleware Setup ---
  // Acknowledge the proxy if you are behind one (e.g., Nginx, Heroku).
  app.set('trust proxy', 1);

  // Body parsers for API routes.
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));
  
  // Custom logging middleware.
  app.use((req, res, next) => {
    if (!req.path.startsWith('/api')) {
      return next(); // Only log API calls
    }
    const start = Date.now();
    res.on("finish", () => {
      const duration = Date.now() - start;
      const logLine = `${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`;
      log(logLine);
    });
    next();
  });


  // --- Vite Setup (Development) or Static File Serving (Production) ---
  if (process.env.NODE_ENV === "development") {
    // In development, Vite handles serving the frontend.
    // This MUST be registered before your API routes to avoid conflicts.
    await setupVite(app, httpServer);
  } else {
    // In production, serve the pre-built static files.
    serveStatic(app);
  }

  // --- API Routes ---
  // Register your API routes AFTER the Vite middleware.
  // This ensures that requests to '/api/...' are handled by your API,
  // and all other requests fall through to Vite.
  registerRoutes(app);


  // --- Error Handling Middleware (must be last) ---
  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    console.error(err.stack); // Log the full error
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";
    res.status(status).json({ message });
  });

  return { app, httpServer };
}


// --- Start the Server ---
createServer().then(({ app, httpServer }) => {
  const port = parseInt(process.env.PORT || '5000', 10);
  httpServer.listen(port, "0.0.0.0", () => {
    log(`serving on port ${port}`);
  });
}).catch(err => {
    console.error("Failed to start server:", err);
    process.exit(1);
});