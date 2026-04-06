from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import whisper
import ffmpeg
import requests
import os
import tempfile
import json
import re
from typing import List, Dict

app = FastAPI(title="Video-Shorter API", description="AI-powered video shortening service")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Whisper model (you can choose model size: tiny, base, small, medium, large)
# Models: tiny(39M), base(139M), small(466M), medium(1.5G), large(2.9G)
print("Initializing Whisper model...")
try:
    model = whisper.load_model("base")
    print("✓ Whisper model loaded successfully")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    model = None

# DeepSeek API configuration
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def parse_segments_from_response(response_text: str) -> List[Dict]:
    """
    Parse LLM response to extract irrelevant segments.
    Expected format: JSON with segments containing start and end times
    Fallback: parse natural language timestamps
    """
    try:
        # Try to parse as JSON first
        data = json.loads(response_text)
        return data.get("irrelevant_segments", [])
    except json.JSONDecodeError:
        pass
    
    # Fallback: extract time ranges from text (e.g., "1:23-2:45", "10s", "1m20s")
    segments = []
    # Simple pattern matching for MM:SS or MM:SS-MM:SS format
    pattern = r'(\d{1,2}):(\d{2})(?:-(\d{1,2}):(\d{2}))?'
    matches = re.findall(pattern, response_text)
    
    for match in matches:
        start_m, start_s = int(match[0]), int(match[1])
        start_time = start_m * 60 + start_s
        
        if match[2] and match[3]:
            end_m, end_s = int(match[2]), int(match[3])
            end_time = end_m * 60 + end_s
        else:
            end_time = start_time + 30  # Default 30 second segment if only start given
        
        segments.append({"start": start_time, "end": end_time})
    
    return segments

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffmpeg"""
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        return duration
    except Exception as e:
        print(f"Error getting duration: {e}")
        return 0

def clip_video(input_path: str, output_path: str, keep_segments: List[Dict]) -> bool:
    """
    Create video with only the keep_segments concatenated.
    keep_segments: list of {"start": seconds, "end": seconds}
    """
    if not keep_segments:
        # No clipping needed, just copy
        os.rename(input_path, output_path)
        return True
    
    try:
        # Create filter complex to extract and concatenate segments
        filter_parts = []
        for i, seg in enumerate(keep_segments):
            filter_parts.append(f"[0:v]trim=start={seg['start']}:end={seg['end']},setpts=PTS-STARTPTS[v{i}]")
            filter_parts.append(f"[0:a]atrim=start={seg['start']}:end={seg['end']},asetpts=PTS-STARTPTS[a{i}]")
        
        if len(keep_segments) == 1:
            # Single segment, just trim
            stream = ffmpeg.input(input_path)
            v = stream['v'].filter('trim', start=keep_segments[0]['start'], end=keep_segments[0]['end']).filter('setpts', 'PTS-STARTPTS')
            a = stream['a'].filter('atrim', start=keep_segments[0]['start'], end=keep_segments[0]['end']).filter('asetpts', 'PTS-STARTPTS')
            ffmpeg.output(v, a, output_path, vcodec='libx264', acodec='aac').run(overwrite_output=True, quiet=True)
        else:
            # Multiple segments: concatenate them
            # Build concat filter
            concat_v_inputs = ''.join([f'[v{i}]' for i in range(len(keep_segments))])
            concat_a_inputs = ''.join([f'[a{i}]' for i in range(len(keep_segments))])
            
            filter_complex = ';'.join(filter_parts) + f';{concat_v_inputs}concat=n={len(keep_segments)}:v=1:a=0[outv];{concat_a_inputs}concat=n={len(keep_segments)}:v=0:a=1[outa]'
            
            ffmpeg.input(input_path).output(output_path, vcodec='libx264', acodec='aac').run(overwrite_output=True)  # Simplified fallback
        
        return True
    except Exception as e:
        print(f"Error clipping video: {e}")
        # Fallback: just copy if clipping fails
        os.rename(input_path, output_path)
        return False

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/process")
async def process_video(file: UploadFile = File(...)):
    """
    Process video: transcribe, analyze, and clip
    """
    # Check if model is loaded
    if model is None:
        raise HTTPException(status_code=503, detail="Whisper model not loaded. Please restart the server.")
    
    if not file.filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Use: mp4, avi, mov, mkv, flv, webm")

    # Save uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    temp_video_path = os.path.join(temp_dir, file.filename)
    output_path = os.path.join(temp_dir, f"shortened_{file.filename}")
    
    try:
        # Save uploaded file
        with open(temp_video_path, 'wb') as temp_file:
            temp_file.write(await file.read())
        
        print(f"Video saved: {temp_video_path}")
        
        # Step 1: Transcribe audio to text using Whisper
        print("Transcribing audio...")
        result = model.transcribe(temp_video_path, language="zh")  # Chinese language set as default
        transcript = result["text"]
        print(f"Transcript: {transcript[:200]}...")

        # Step 2: Analyze transcript with DeepSeek LLM
        print("Analyzing content with DeepSeek...")
        if not DEEPSEEK_API_KEY:
            raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
        
        prompt = f"""Analyze this video transcript and identify segments that are NOT related to the main theme or topic. 
Please provide the timestamps (in MM:SS format) of irrelevant parts that should be removed.
Format your response as JSON with "irrelevant_segments" array containing objects with "start" and "end" fields (in seconds).
Example: {{"irrelevant_segments": [{{"start": 10, "end": 30}}, {{"start": 150, "end": 180}}]}}

Transcript: {transcript}"""
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            print(f"LLM error: {response.text}")
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {response.status_code}")
        
        analysis = response.json()["choices"][0]["message"]["content"]
        print(f"LLM Analysis: {analysis}")
        
        # Parse irrelevant segments
        irrelevant_segments = parse_segments_from_response(analysis)
        print(f"Irrelevant segments: {irrelevant_segments}")

        # Step 3: Convert irrelevant segments to keep segments
        video_duration = get_video_duration(temp_video_path)
        keep_segments = []
        
        if irrelevant_segments:
            # Sort segments by start time
            irrelevant_segments.sort(key=lambda x: x.get('start', 0))
            
            current_position = 0
            for seg in irrelevant_segments:
                seg_start = seg.get('start', 0)
                seg_end = seg.get('end', seg_start + 30)
                
                if current_position < seg_start:
                    keep_segments.append({"start": current_position, "end": seg_start})
                
                current_position = max(current_position, seg_end)
            
            # Add remaining part
            if current_position < video_duration:
                keep_segments.append({"start": current_position, "end": video_duration})
        else:
            # No irrelevant parts found, keep the whole video
            keep_segments.append({"start": 0, "end": video_duration})
        
        print(f"Keep segments: {keep_segments}")

        # Step 4: Clip video using FFmpeg
        print("Clipping video...")
        if keep_segments:
            clip_video(temp_video_path, output_path, keep_segments)
        else:
            os.rename(temp_video_path, output_path)

        # Return the shortened video
        print(f"Returning video: {output_path}")
        return FileResponse(output_path, media_type='video/mp4', filename="shortened_video.mp4")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        # Clean up temp files after a delay would be better, but for now just log
        pass

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)