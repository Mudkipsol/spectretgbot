# SpectreSpoofer Telegram Bot

A Telegram bot interface for the SpectreSpoofer content manipulation stack.

## Deploy to Railway

Follow these steps to deploy the bot to Railway:

### 1. Create Railway Project

1. Go to [Railway](https://railway.app) and sign in
2. Create a new project
3. Connect to your GitHub repository: `https://github.com/Mudkipsol/spectretelegrambot.git`

### 2. Configure Environment Variables

In Railway, go to your project settings and add these environment variables:

```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BASE_URL=https://your-railway-server-url.railway.app  
SERVER_SECRET=your_server_secret_here
SPECTRE_LICENSE_DB=spectre_license_db.sqlite
SMTP_EMAIL=team@spectrespoofer.com
SMTP_PASSWORD=your_smtp_app_password
```

**Important**: Replace the placeholder values with your actual credentials.

### 3. Set Service Type

Since this bot uses long-polling (not webhooks):

1. In Railway, go to your service settings
2. Make sure the service type is set to **Worker** (not Web)
3. Railway will automatically detect the `Procfile` and run the worker process

### 4. Deploy

1. Push your code to the GitHub repository
2. Railway will automatically build and deploy using the Dockerfile
3. Monitor the deployment logs for any issues

### 5. Verify Deployment

1. Check the Railway logs to confirm the bot started successfully
2. Look for the message: `SpectreSpoofer Assistant Bot running (live).`
3. Test the bot in Telegram by sending `/start`

### Storage Considerations

The bot writes files to `bot/downloads/` and `bot/output/` directories. Railway provides ephemeral storage, which means uploaded files and processed outputs will be lost when the service restarts.

If you need persistent storage:
1. Consider using Railway volumes for persistent file storage
2. Or modify the bot to use cloud storage (S3, etc.) for file uploads/outputs

### Troubleshooting

**Bot not responding**: Check Railway logs for startup errors
**FFmpeg errors**: Ensure all system dependencies installed correctly
**File processing fails**: Verify ExifTool and FFmpeg are available in the container

### Technical Details

- **Deployment Method**: Long-polling (no webhook required)
- **Container**: Python 3.11-slim with FFmpeg and ExifTool
- **Service Type**: Worker process (not web service)
- **Entry Point**: `bot/WorkingBot_FIXED.py`
