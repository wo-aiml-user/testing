import type { Express } from "express";
import { createServer, type Server } from "http";
import { createProxyMiddleware } from 'http-proxy-middleware';

export async function registerRoutes(app: Express): Promise<Server> {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

  app.use('/api', createProxyMiddleware({
    target: backendUrl,
    changeOrigin: true,
    pathRewrite: {
      '^/api': '', 
    },
    logLevel: 'debug',
  }));

  const httpServer = createServer(app);
  return httpServer;
}