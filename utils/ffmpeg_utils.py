import asyncio
import os
import subprocess
import json
from typing import Optional, Dict, Any, List, Tuple
import logging

from config import config

logger = logging.getLogger(__name__)

class FFmpegHandler:
    def __init__(self):
        self.ffmpeg_path = config.FFMPEG_PATH
        self.ffprobe_path = config.FFPROBE_PATH
        self.progress_handlers = {}
    
    async def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Get media information using ffprobe"""
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFprobe error: {stderr.decode()}")
            
            return json.loads(stdout.decode())
            
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            raise
    
    async def extract_thumbnail(self, video_path: str, time: str = "00:00:01") -> str:
        """Extract thumbnail from video at specified time"""
        output_path = os.path.join(config.TEMP_DIR, f"thumbnail_{os.path.basename(video_path)}.jpg")
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-ss', time,
            '-vframes', '1',
            '-q:v', '2',
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Extracting thumbnail")
        return output_path
    
    async def remove_audio(self, video_path: str) -> str:
        """Remove audio from video"""
        output_path = os.path.join(config.TEMP_DIR, f"muted_{os.path.basename(video_path)}")
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-c:v', 'copy',
            '-an',
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Removing audio")
        return output_path
    
    async def extract_audio(self, video_path: str, output_format: str = "mp3", bitrate: str = "192k") -> str:
        """Extract audio from video"""
        output_path = os.path.join(
            config.TEMP_DIR,
            f"audio_{os.path.splitext(os.path.basename(video_path))[0]}.{output_format}"
        )
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-q:a', '0',
            '-map', 'a',
            '-b:a', bitrate,
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Extracting audio")
        return output_path
    
    async def trim_video(self, video_path: str, start_time: str, end_time: str) -> str:
        """Trim video between start and end times"""
        output_path = os.path.join(config.TEMP_DIR, f"trimmed_{os.path.basename(video_path)}")
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-ss', start_time,
            '-to', end_time,
            '-c', 'copy',
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Trimming video")
        return output_path
    
    async def merge_videos(self, video_paths: List[str]) -> str:
        """Merge multiple videos"""
        output_path = os.path.join(config.TEMP_DIR, "merged_video.mp4")
        
        # Create concat file
        concat_file = os.path.join(config.TEMP_DIR, "concat_list.txt")
        with open(concat_file, 'w') as f:
            for path in video_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        cmd = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Merging videos")
        os.remove(concat_file)
        return output_path
    
    async def convert_video(self, input_path: str, output_format: str, 
                          quality: Optional[Dict[str, Any]] = None) -> str:
        """Convert video to different format"""
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(config.TEMP_DIR, f"{base_name}.{output_format}")
        
        cmd = [self.ffmpeg_path, '-i', input_path]
        
        if quality:
            if 'resolution' in quality:
                cmd.extend(['-s', quality['resolution']])
            if 'bitrate' in quality:
                cmd.extend(['-b:v', quality['bitrate']])
            if 'fps' in quality:
                cmd.extend(['-r', str(quality['fps'])])
        
        cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-c:a', 'aac', output_path, '-y'])
        
        await self.run_command(cmd, f"Converting to {output_format}")
        return output_path
    
    async def merge_audio_video(self, video_path: str, audio_path: str) -> str:
        """Merge video with new audio"""
        output_path = os.path.join(config.TEMP_DIR, f"merged_av_{os.path.basename(video_path)}")
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Merging audio and video")
        return output_path
    
    async def add_subtitle(self, video_path: str, subtitle_path: str) -> str:
        """Add subtitle to video"""
        output_path = os.path.join(config.TEMP_DIR, f"subtitled_{os.path.basename(video_path)}")
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-vf', f"subtitles='{subtitle_path}'",
            '-c:a', 'copy',
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Adding subtitle")
        return output_path
    
    async def compress_video(self, video_path: str, target_size_mb: int) -> str:
        """Compress video to target size"""
        output_path = os.path.join(config.TEMP_DIR, f"compressed_{os.path.basename(video_path)}")
        
        # Get video duration
        info = await self.get_media_info(video_path)
        duration = float(info['format']['duration'])
        
        # Calculate target bitrate
        target_bitrate_kbps = int((target_size_mb * 8192) / duration)
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-c:v', 'libx264',
            '-b:v', f'{target_bitrate_kbps}k',
            '-preset', 'medium',
            '-c:a', 'aac',
            '-b:a', '128k',
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, "Compressing video")
        return output_path
    
    async def split_video(self, video_path: str, segment_duration: int) -> List[str]:
        """Split video into segments of specified duration"""
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_pattern = os.path.join(config.TEMP_DIR, f"{base_name}_%03d.mp4")
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-c', 'copy',
            '-map', '0',
            '-segment_time', str(segment_duration),
            '-f', 'segment',
            '-reset_timestamps', '1',
            output_pattern,
            '-y'
        ]
        
        await self.run_command(cmd, "Splitting video")
        
        # Get list of created segments
        segments = []
        for i in range(100):  # Assuming max 100 segments
            seg_path = os.path.join(config.TEMP_DIR, f"{base_name}_{i:03d}.mp4")
            if os.path.exists(seg_path):
                segments.append(seg_path)
            else:
                break
        
        return segments
    
    async def adjust_audio(self, audio_path: str, speed: float = 1.0, 
                          volume: float = 1.0, bass: float = 0.0, 
                          treble: float = 0.0) -> str:
        """Adjust audio parameters"""
        output_path = os.path.join(config.TEMP_DIR, f"adjusted_{os.path.basename(audio_path)}")
        
        filters = []
        
        if speed != 1.0:
            filters.append(f"atempo={speed}")
        
        if volume != 1.0:
            filters.append(f"volume={volume}")
        
        if bass != 0.0:
            filters.append(f"equalizer=f=100:t=q:w=0.5:g={bass}")
        
        if treble != 0.0:
            filters.append(f"equalizer=f=10000:t=q:w=0.5:g={treble}")
        
        cmd = [self.ffmpeg_path, '-i', audio_path]
        
        if filters:
            cmd.extend(['-af', ','.join(filters)])
        
        cmd.extend(['  -c:a', 'libmp3lame', '-q:a', '2', output_path, '-y'])
        
        await self.run_command(cmd, "Adjusting audio")
        return output_path
    
    async def convert_audio(self, audio_path: str, output_format: str,
                          bitrate: str = "192k", sample_rate: str = "44100") -> str:
        """Convert audio to different format"""
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_path = os.path.join(config.TEMP_DIR, f"{base_name}.{output_format}")
        
        cmd = [
            self.ffmpeg_path,
            '-i', audio_path,
            '-b:a', bitrate,
            '-ar', sample_rate,
            output_path,
            '-y'
        ]
        
        await self.run_command(cmd, f"Converting audio to {output_format}")
        return output_path
    
    async def run_command(self, cmd: List[str], operation_name: str) -> str:
        """Run FFmpeg command with progress tracking"""
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Read output in real-time for progress
            stderr_lines = []
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                
                line_str = line.decode('utf-8', errors='ignore').strip()
                stderr_lines.append(line_str)
                
                # Parse progress from FFmpeg output
                if "time=" in line_str:
                    # Extract time progress
                    # This is a simplified progress parser
                    pass
            
            await process.wait()
            
            if process.returncode != 0:
                error_msg = '\n'.join(stderr_lines[-10:])  # Last 10 lines
                raise Exception(f"FFmpeg error ({operation_name}): {error_msg}")
            
            return '\n'.join(stderr_lines)
            
        except Exception as e:
            logger.error(f"Error in {operation_name}: {e}")
            raise
    
    def parse_progress(self, line: str) -> Optional[float]:
        """Parse progress percentage from FFmpeg output"""
        # FFmpeg progress format: time=00:01:23.45
        import re
        
        time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
        if time_match:
            # Convert to seconds and calculate percentage
            # This requires knowing total duration
            pass
        
        return None
