# Video-Shorter

AI-powered video shortening application that transcribes video audio, analyzes content with DeepSeek LLM, and clips out irrelevant parts.

## Features

- Upload local video files via web interface
- Automatic audio transcription using Whisper (supports Chinese)
- Content analysis with DeepSeek LLM to identify irrelevant segments
- Intelligent video clipping using FFmpeg
- Download shortened video directly
- Simple, responsive web UI
- No Node.js required

## Requirements

- Python 3.8+
- FFmpeg (for video processing)
- DeepSeek API key (for content analysis)

## Quick Start

### 1. Install Python Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Install FFmpeg

#### Windows:
```bash
# Using winget
winget install FFmpeg.FFmpeg

# Or download from: https://ffmpeg.org/download.html
# Add to PATH if needed
```

#### macOS:
```bash
brew install ffmpeg
```

#### Linux:
```bash
sudo apt-get install ffmpeg
```

### 3. Configure API Key

Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Edit `.env` and add your DeepSeek API key:
```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
```

Get your API key from: https://platform.deepseek.com/

### 4. Run the Application

```bash
python start.py
```

This will:
- Pre-load the Whisper model (~139MB, only on first run)
- Start the FastAPI backend on `http://localhost:8000`
- Start the frontend server on `http://localhost:3000`
- Automatically open the web interface in your browser

**Note:** On the first run, Whisper will download its base model (~139MB). This takes a few minutes but only happens once. The download progress will be shown in the console. Subsequent runs will be much faster since the model is cached.

## Usage

1. Open `http://localhost:3000` in your browser (or it opens automatically)
2. Select a video file (supports: mp4, avi, mov, mkv, flv, webm)
3. Click "Shorten Video"
4. Wait for processing (transcription, analysis, and clipping)
5. Download the shortened video

## How It Works

1. **Transcription**: Whisper converts video audio to text (supports multiple languages)
2. **Analysis**: DeepSeek LLM analyzes the transcript to identify off-topic content
3. **Clipping**: FFmpeg removes the irrelevant segments
4. **Download**: The shortened video is ready for download

## Architecture

```
Video-Shorter/
├── backend/                # Python FastAPI backend
│   ├── main.py            # FastAPI application with Whisper, DeepSeek, FFmpeg
│   ├── requirements.txt    # Python dependencies
│   └── ...
├── frontend/               # Web frontend (HTML/JS)
│   ├── index.html         # Frontend UI
│   └── ...
├── start.py               # Startup script (starts backend + frontend)
├── .env.example           # Environment variables template
└── README.md             # This file
```

## API Documentation

When running, the FastAPI backend provides interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Main Endpoints

- `GET /health` - Health check
- `POST /process` - Upload video and get shortened version

## Troubleshooting

### Whisper model download is slow
On first run, Whisper downloads its base model (~139MB). This is normal and only happens once.
- **Base model** (139M): Fastest, good accuracy - Default
- **Tiny model** (39M): Fastest, lower accuracy - Edit `backend/main.py` to use `whisper.load_model("tiny")`
- **Small model** (466M): Better accuracy
- **Medium model** (1.5G): Even better accuracy
- **Large model** (2.9G): Best accuracy

To change the model, edit `backend/main.py`:
```python
model = whisper.load_model("base")  # Change "base" to "tiny", "small", etc.
```

### FFmpeg not found
Make sure FFmpeg is installed and in your system PATH:
```bash
ffmpeg -version
```

### DeepSeek API errors
- Verify your API key is correct in `.env`
- Check your API account has sufficient credits
- Verify API endpoint URL is correct
- Test with: `curl https://api.deepseek.com/v1/chat/completions -H "Authorization: Bearer YOUR_KEY"`

### Out of memory
Large videos may use lots of memory. Try:
- Processing smaller files first
- Using the "tiny" Whisper model (39MB, faster)
- Closing other applications

### Port already in use
If ports 8000 or 3000 are already in use:
- Edit `backend/main.py` to change the port
- Edit `start.py` to change the frontend port
- Or kill the process using the port: `lsof -i :8000` (Mac/Linux) or `netstat -ano | findstr :8000` (Windows)

### Backend crashes with model error
If Whisper fails to load:
- Check internet connection (needed for model download)
- Clear Whisper cache: Delete `~/.cache/whisper/` folder
- Restart the application
- Try with a smaller model ("tiny")

## Notes

- Processing time depends on video length and complexity
- Longer videos require more transcription time
- DeepSeek API calls depend on network connectivity
- All processing happens locally on your machine
- The application stores temporary files in your system temp directory

## License

Apache License 2.0 - See LICENSE file for details
