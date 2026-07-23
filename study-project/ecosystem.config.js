const path = require('path');
const fs = require('fs');

// Get the absolute path to the workspace directory
const WORKSPACE_DIR = __dirname;

module.exports = {
  apps: [
    {
      // Backend FastAPI application configuration
      name: "study_backend",
      script: "uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 7800",
      cwd: path.join(WORKSPACE_DIR, "backend"),
      interpreter: path.join(WORKSPACE_DIR, "backend/venv/bin/python"),
      watch: ["app"],
      ignore_watch: [
        "node_modules/",
        "venv/",
        "__pycache__/",
        ".env"
      ],
      max_memory_restart: "400M",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      env: {
        NODE_ENV: "production",
        STATIC_FILES_DIR: path.join(WORKSPACE_DIR, "frontend/dist"),
        FIREBASE_CREDENTIALS_PATH: fs.existsSync(path.join(WORKSPACE_DIR, "firebase_adminsdk_key.json")) 
          ? path.join(WORKSPACE_DIR, "firebase_adminsdk_key.json")
          : path.join(path.dirname(WORKSPACE_DIR), "firebase_adminsdk_key.json")
      },
      error_file: path.join(WORKSPACE_DIR, "logs/backend-error.log"),
      out_file: path.join(WORKSPACE_DIR, "logs/backend-out.log"),
      merge_logs: true,
      time: true
    },
    {
      // Gradio application configuration
      name: "study_gradio",
      script: "app.py",
      cwd: path.join(WORKSPACE_DIR, "gradio_app"),
      interpreter: path.join(WORKSPACE_DIR, "gradio_app/venv/bin/python"),
      watch: ["app.py", "gradio_card.css"],
      ignore_watch: [
        "venv/",
        "__pycache__/",
        ".env",
        "answers/"
      ],
      max_memory_restart: "3400M",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
        HF_TOKEN: process.env.HF_TOKEN || ''
      },
      // Logging configuration
      error_file: path.join(WORKSPACE_DIR, "logs/gradio-error.log"),
      out_file: path.join(WORKSPACE_DIR, "logs/gradio-out.log"),
      merge_logs: true,
      time: true
    }
  ]
}; 