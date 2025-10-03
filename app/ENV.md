# Environment Configuration

The app reads environment variables from the `.env` file in the **project root** (one level up).

## Setup

```bash
# From project root
cp .env.template .env
# Edit .env and add your configuration
```

## Development Mode

To run the app locally without OAuth2:

1. Edit `.env` in the project root
2. Add this line:
   ```env
   DEV_MODE=true
   ```
3. Run the app:
   ```bash
   cd app
   python app.py
   ```

## Configuration Reference

See `../.env.template` for all available options:

- **DEV_MODE** - Set to `true` to bypass OAuth2 (development only)
- **FLASK_ENV** - Set to `development` or `production`
- **DEBUG** - Enable Flask debug mode
- **PORT** - Server port (default: 8000)
- **SECRET_KEY** - Flask secret key for sessions
- **EMAILS_FILE_PATH** - Path to authorized emails file
- **LOG_FILE_PATH** - Path to access log file

## Security Note

⚠️ **Never commit `.env` to git!** It contains sensitive credentials.

The `.env` file is already in `.gitignore`.
