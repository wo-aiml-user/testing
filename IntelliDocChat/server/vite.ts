import { createServer as createViteServer } from "vite";
import express, { Express } from "express";
import path from "path";
import http from "http";
import fs from 'fs/promises';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const projectRoot = path.resolve(__dirname, '..');

export async function setupVite(app: Express, server: http.Server) {
  const vite = await createViteServer({
    // We pass the config file path directly to the server instance.
    // This ensures it uses the aliases and plugins we defined.
    configFile: path.resolve(projectRoot, 'vite.config.ts'), 
    server: { 
        middlewareMode: true,
        hmr: { server } 
    },
    appType: 'custom',
  });

  // IMPORTANT: We tell Express to serve static files from the 'client' directory.
  // This allows the browser to fetch files like main.tsx directly.
  app.use(express.static(path.resolve(projectRoot, 'client')));
  
  // Use the Vite middleware.
  app.use(vite.middlewares);

  // The SPA fallback remains the same, serving the correct index.html.
  app.use('*', async (req, res, next) => {
    try {
      const url = req.originalUrl;
      const template = await fs.readFile(
        path.resolve(projectRoot, 'client/index.html'),
        'utf-8'
      );
      const html = await vite.transformIndexHtml(url, template);
      res.status(200).set({ 'Content-Type': 'text/html' }).end(html);
    } catch (e) {
      vite.ssrFixStacktrace(e as Error);
      next(e);
    }
  });

  return { app, vite };
}

export function serveStatic(app: Express) {
    const staticPath = path.resolve(projectRoot, "dist", "public");
    app.use(express.static(staticPath));
    app.get('*', (_req, res) => {
        res.sendFile(path.resolve(staticPath, 'index.html'));
    });
}

export function log(message: string) {
  console.log(`${new Date().toLocaleTimeString()} [express] ${message}`);
}