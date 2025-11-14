import os
import asyncio
import subprocess
import ffmpeg
from typing import List, Tuple, Optional
import json
import aiofiles

class FFmpegProcessor:
    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(f"{self.temp_dir}/inputs", exist_ok=True)
        os.makedirs(f"{self.temp_dir}/outputs", exist_ok=True)
    
    async def run_ffmpeg_command(self, command: List[str], input_file: str = None) -> bool:
        """Run FFmpeg command asynchronously"""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                print(f"FFmpeg error: {stderr.decode()}")
                return False
            return True
        except Exception as e:
            print(f"Command execution error: {e}")
            return False
    
    # Thumbnail extraction
    async def extract_thumbnail(self, video_path: str, time_sec: float = 10) -> str:
        output_path = f"{self.temp_dir}/outputs/thumbnail_{os.path.basename(video_path)}.jpg"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-ss', str(time_sec),
            '-vframes', '1',
            '-q:v', '2',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Thumbnail extraction failed")
    
    # Video trimming
    async def trim_video(self, video_path: str, start_time: str, end_time: str) -> str:
        output_path = f"{self.temp_dir}/outputs/trimmed_{os.path.basename(video_path)}"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-ss', start_time,
            '-to', end_time,
            '-c', 'copy',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Video trimming failed")
    
    # Video merging
    async def merge_videos(self, video_paths: List[str]) -> str:
        output_path = f"{self.temp_dir}/outputs/merged_videos.mp4"
        
        # Create input file list for FFmpeg
        list_file = f"{self.temp_dir}/inputs/merge_list.txt"
        async with aiofiles.open(list_file, 'w') as f:
            for video_path in video_paths:
                await f.write(f"file '{os.path.abspath(video_path)}'\n")
        
        command = [
            'ffmpeg', '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            os.remove(list_file)
            return output_path
        raise Exception("Video merging failed")
    
    # Audio extraction from video
    async def extract_audio(self, video_path: str, format: str = "mp3") -> str:
        output_path = f"{self.temp_dir}/outputs/audio_{os.path.basename(video_path)}.{format}"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-q:a', '0',
            '-map', 'a',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Audio extraction failed")
    
    # Remove audio from video
    async def remove_audio(self, video_path: str) -> str:
        output_path = f"{self.temp_dir}/outputs/no_audio_{os.path.basename(video_path)}"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-c', 'copy',
            '-an',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Audio removal failed")
    
    # Audio conversion
    async def convert_audio(self, audio_path: str, output_format: str) -> str:
        output_path = f"{self.temp_dir}/outputs/converted_{os.path.basename(audio_path)}.{output_format}"
        
        command = [
            'ffmpeg', '-i', audio_path,
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Audio conversion failed")
    
    # Video splitting
    async def split_video(self, video_path: str, segment_time: str) -> List[str]:
        output_pattern = f"{self.temp_dir}/outputs/split_{os.path.basename(video_path)}_%03d.mp4"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-c', 'copy',
            '-map', '0',
            '-segment_time', segment_time,
            '-f', 'segment',
            '-reset_timestamps', '1',
            '-y', output_pattern
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success:
            # Find all created segments
            output_files = []
            base_name = os.path.basename(video_path).split('.')[0]
            for file in os.listdir(f"{self.temp_dir}/outputs"):
                if file.startswith(f"split_{base_name}_"):
                    output_files.append(f"{self.temp_dir}/outputs/{file}")
            return sorted(output_files)
        raise Exception("Video splitting failed")
    
    # Screenshot capture
    async def take_screenshots(self, video_path: str, timestamps: List[str]) -> List[str]:
        output_files = []
        
        for i, timestamp in enumerate(timestamps):
            output_path = f"{self.temp_dir}/outputs/screenshot_{i}_{os.path.basename(video_path)}.jpg"
            
            command = [
                'ffmpeg', '-i', video_path,
                '-ss', timestamp,
                '-vframes', '1',
                '-q:v', '2',
                '-y', output_path
            ]
            
            success = await self.run_ffmpeg_command(command)
            if success and os.path.exists(output_path):
                output_files.append(output_path)
        
        if output_files:
            return output_files
        raise Exception("Screenshot capture failed")
    
    # Video optimization
    async def optimize_video(self, video_path: str, quality: str = "medium") -> str:
        output_path = f"{self.temp_dir}/outputs/optimized_{os.path.basename(video_path)}"
        
        if quality == "high":
            crf = "18"
            preset = "slow"
        elif quality == "low":
            crf = "28"
            preset = "fast"
        else:  # medium
            crf = "23"
            preset = "medium"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-c:v', 'libx264',
            '-preset', preset,
            '-crf', crf,
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Video optimization failed")
    
    # Merge video with external audio
    async def merge_video_audio(self, video_path: str, audio_path: str) -> str:
        output_path = f"{self.temp_dir}/outputs/merged_av_{os.path.basename(video_path)}"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-i', audio_path,
            '-c', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Video-audio merging failed")
    
    # Add subtitles to video
    async def add_subtitles(self, video_path: str, subtitle_path: str) -> str:
        output_path = f"{self.temp_dir}/outputs/subtitled_{os.path.basename(video_path)}"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-vf', f"subtitles={subtitle_path}",
            '-c:a', 'copy',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Subtitle adding failed")
    
    # Extract subtitles from video
    async def extract_subtitles(self, video_path: str) -> str:
        output_path = f"{self.temp_dir}/outputs/subtitles_{os.path.basename(video_path)}.srt"
        
        command = [
            'ffmpeg', '-i', video_path,
            '-map', '0:s:0',
            '-y', output_path
        ]
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Subtitle extraction failed")
    
    # Get video metadata
    async def get_metadata(self, file_path: str) -> dict:
        command = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return json.loads(stdout.decode())
        raise Exception("Metadata extraction failed")
    
    # Change metadata
    async def change_metadata(self, video_path: str, metadata: dict) -> str:
        output_path = f"{self.temp_dir}/outputs/metadata_{os.path.basename(video_path)}"
        
        command = ['ffmpeg', '-i', video_path]
        
        # Add metadata parameters
        for key, value in metadata.items():
            command.extend(['-metadata', f'{key}={value}'])
        
        command.extend(['-c', 'copy', '-y', output_path])
        
        success = await self.run_ffmpeg_command(command)
        if success and os.path.exists(output_path):
            return output_path
        raise Exception("Metadata change failed")

# Global instance
ffmpeg_processor = FFmpegProcessor()
