import asyncio
import os
import json
import subprocess
from typing import Dict, Any, List, Optional
from config import config

class FFmpegHandler:
    def __init__(self):
        self.ffmpeg = config.FFMPEG_PATH
        self.ffprobe = config.FFPROBE_PATH
    
    async def run_command(self, cmd: List[str]) -> str:
        """Run FFmpeg command"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")
        
        return stdout.decode()
    
    async def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Get media information"""
        cmd = [
            self.ffprobe,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = await self.run_command(cmd)
        return json.loads(result)
    
    async def extract_thumbnail(self, video_path: str, time: str = "00:00:01") -> str:
        """Extract thumbnail from video"""
        output = os.path.join(config.TEMP_DIR, f"thumb_{os.path.basename(video_path)}.jpg")
        
        cmd = [
            self.ffmpeg,
            '-i', video_path,
            '-ss', time,
            '-vframes', '1',
            '-q:v', '2',
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        return output
    
    async def extract_audio(self, video_path: str, format: str = "mp3", bitrate: str = "192k") -> str:
        """Extract audio from video"""
        base = os.path.splitext(os.path.basename(video_path))[0]
        output = os.path.join(config.TEMP_DIR, f"{base}.{format}")
        
        cmd = [
            self.ffmpeg,
            '-i', video_path,
            '-q:a', '0',
            '-map', 'a',
            '-b:a', bitrate,
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        return output
    
    async def remove_audio(self, video_path: str) -> str:
        """Remove audio from video"""
        output = os.path.join(config.TEMP_DIR, f"muted_{os.path.basename(video_path)}")
        
        cmd = [
            self.ffmpeg,
            '-i', video_path,
            '-c', 'copy',
            '-an',
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        return output
    
    async def trim_video(self, video_path: str, start: str, end: str) -> str:
        """Trim video"""
        output = os.path.join(config.TEMP_DIR, f"trimmed_{os.path.basename(video_path)}")
        
        cmd = [
            self.ffmpeg,
            '-i', video_path,
            '-ss', start,
            '-to', end,
            '-c', 'copy',
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        return output
    
    async def convert_video(self, input_path: str, output_format: str, 
                          quality: Optional[Dict] = None) -> str:
        """Convert video format"""
        base = os.path.splitext(os.path.basename(input_path))[0]
        output = os.path.join(config.TEMP_DIR, f"{base}.{output_format}")
        
        cmd = [self.ffmpeg, '-i', input_path]
        
        if quality:
            if 'resolution' in quality:
                cmd.extend(['-s', quality['resolution']])
            if 'bitrate' in quality:
                cmd.extend(['-b:v', quality['bitrate']])
        
        cmd.extend(['-c:v', 'libx264', '-preset', 'medium', output, '-y'])
        
        await self.run_command(cmd)
        return output
    
    async def merge_videos(self, video_paths: List[str]) -> str:
        """Merge multiple videos"""
        output = os.path.join(config.TEMP_DIR, "merged.mp4")
        
        # Create concat file
        concat_file = os.path.join(config.TEMP_DIR, "concat.txt")
        with open(concat_file, 'w') as f:
            for path in video_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        cmd = [
            self.ffmpeg,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        os.remove(concat_file)
        return output
    
    async def compress_video(self, video_path: str, target_size_mb: int) -> str:
        """Compress video"""
        output = os.path.join(config.TEMP_DIR, f"compressed_{os.path.basename(video_path)}")
        
        # Get duration
        info = await self.get_media_info(video_path)
        duration = float(info['format']['duration'])
        
        # Calculate bitrate
        target_bitrate = int((target_size_mb * 8192) / duration)
        
        cmd = [
            self.ffmpeg,
            '-i', video_path,
            '-c:v', 'libx264',
            '-b:v', f'{target_bitrate}k',
            '-preset', 'medium',
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        return output
    
    async def convert_audio(self, audio_path: str, output_format: str, 
                          bitrate: str = "192k") -> str:
        """Convert audio format"""
        base = os.path.splitext(os.path.basename(audio_path))[0]
        output = os.path.join(config.TEMP_DIR, f"{base}.{output_format}")
        
        cmd = [
            self.ffmpeg,
            '-i', audio_path,
            '-b:a', bitrate,
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        return output
    
    async def merge_audio(self, audio_paths: List[str]) -> str:
        """Merge multiple audio files"""
        output = os.path.join(config.TEMP_DIR, "merged_audio.mp3")
        
        # Create concat file
        concat_file = os.path.join(config.TEMP_DIR, "audio_concat.txt")
        with open(concat_file, 'w') as f:
            for path in audio_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        cmd = [
            self.ffmpeg,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        os.remove(concat_file)
        return output
    
    async def adjust_audio(self, audio_path: str, speed: float = 1.0, 
                         volume: float = 1.0) -> str:
        """Adjust audio speed and volume"""
        output = os.path.join(config.TEMP_DIR, f"adjusted_{os.path.basename(audio_path)}")
        
        filters = []
        if speed != 1.0:
            filters.append(f"atempo={speed}")
        if volume != 1.0:
            filters.append(f"volume={volume}")
        
        cmd = [self.ffmpeg, '-i', audio_path]
        if filters:
            cmd.extend(['-af', ','.join(filters)])
        cmd.extend(['-c:a', 'libmp3lame', output, '-y'])
        
        await self.run_command(cmd)
        return output
    
    async def create_gif(self, video_path: str, start: str, duration: str, 
                        fps: int = 10, width: int = 480) -> str:
        """Create GIF from video"""
        output = os.path.join(config.TEMP_DIR, f"gif_{os.path.basename(video_path)}.gif")
        
        cmd = [
            self.ffmpeg,
            '-i', video_path,
            '-ss', start,
            '-t', duration,
            '-vf', f"fps={fps},scale={width}:-1:flags=lanczos",
            '-c:v', 'gif',
            output,
            '-y'
        ]
        
        await self.run_command(cmd)
        return output
