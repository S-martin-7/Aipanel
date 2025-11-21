// PM2 Ecosystem Configuration
// Gestión de procesos para AIPanel

module.exports = {
  apps: [
    // Backend API (NestJS)
    {
      name: 'aipanel-backend',
      cwd: './backend',
      script: 'dist/main.js',
      instances: 2, // Usa 2 instancias para balance de carga
      exec_mode: 'cluster',

      // Variables de entorno
      env: {
        NODE_ENV: 'production',
        PORT: process.env.BACKEND_PORT || 4000,
      },

      // Auto restart
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',

      // Logs
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,

      // Tiempos
      min_uptime: '10s',
      max_restarts: 10,

      // Cron para restart diario (opcional)
      cron_restart: '0 4 * * *', // 4 AM todos los días
    },

    // Frontend (Next.js)
    {
      name: 'aipanel-frontend',
      cwd: './frontend',
      script: 'node_modules/next/dist/bin/next',
      args: 'start -p ' + (process.env.FRONTEND_PORT || 3000),
      instances: 1, // Next.js en production usa una instancia
      exec_mode: 'fork',

      // Variables de entorno
      env: {
        NODE_ENV: 'production',
        PORT: process.env.FRONTEND_PORT || 3000,
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
      },

      // Auto restart
      autorestart: true,
      watch: false,
      max_memory_restart: '400M',

      // Logs
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,

      // Tiempos
      min_uptime: '10s',
      max_restarts: 10,
    },

    // Worker para tareas en background (opcional)
    {
      name: 'aipanel-worker',
      cwd: './backend',
      script: 'dist/worker.js', // Crear este archivo si necesitas workers
      instances: 1,
      exec_mode: 'fork',

      env: {
        NODE_ENV: 'production',
        WORKER: 'true',
      },

      autorestart: true,
      watch: false,
      max_memory_restart: '300M',

      error_file: './logs/worker-error.log',
      out_file: './logs/worker-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },
  ],

  // Configuración de deployment (opcional)
  deploy: {
    production: {
      user: 'deploy',
      host: ['your-vps-ip'],
      ref: 'origin/main',
      repo: 'git@github.com:username/aipanel.git',
      path: '/var/www/aipanel',
      'post-deploy': 'npm install && pm2 reload ecosystem.config.js --env production',
    },
  },
};
