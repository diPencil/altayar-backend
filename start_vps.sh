#!/bin/bash

# AltayarVIP VPS Startup Script

echo "🚀 Starting deployment setup..."

# 1. Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install it first."
    exit 1
fi

# 2. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
echo "⬇️ Installing dependencies..."
pip install -r requirements.txt

# 5. Setup Environment Variables
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env from production example..."
    cp .env.production.example .env
    echo "⚠️ IMPORTANT: Please edit .env file and set your secure keys and database URL!"
else
    echo "✅ .env file already exists."
fi

# 6. Apply Database Migrations (if using alembic)
# echo "🗄️ Applying database migrations..."
# alembic upgrade head

# 7. Start the Server
echo "🔥 Starting Uvicorn Server..."
# Run in background with nohup, logging to server.log
nohup uvicorn server:app --host 0.0.0.0 --port 8082 > server.log 2>&1 &

echo "✅ Server started in background! Check server.log for output."
echo "   PID: $!"
