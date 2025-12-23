import os
from utils.ffmpeg_utils import FFmpegHandler

class VideoTrimmer:
    @staticmethod
    async def trim_video(input_path: str, start_time: str, end_time: str) -> str:
        """Trim video between start and end times"""
        ffmpeg = FFmpegHandler()
        return await ffmpeg.trim_video(input_path, start_time, end_time)
    
    @staticmethod
    async def auto_trim(video_path: str, threshold: float = 0.1) -> str:
        """Auto-trim silent parts"""
        # This is a simplified version
        # In production, you'd analyze audio for silence
        ffmpeg = FFmpegHandler()
        
        # Get video info
        info = await ffmpeg.get_media_info(video_path)
        duration = float(info['format']['duration'])
        
        # For now, just trim first and last 5%
        start = duration * 0.05
        end = duration * 0.95
        
        start_str = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d}"
        end_str = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d}"
        
        return await ffmpeg.trim_video(video_path, start_str, end_str)
    
    @staticmethod
    async def trim_by_scenes(video_path: str, scene_count: int = 10) -> list:
        """Trim video into scenes"""
        # This would use scene detection
        # For now, split equally
        ffmpeg = FFmpegHandler()
        
        info = await ffmpeg.get_media_info(video_path)
        duration = float(info['format']['duration'])
        segment_duration = duration / scene_count
        
        segments = []
        for i in range(scene_count):
            start = i * segment_duration
            end = (i + 1) * segment_duration
            
            start_str = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d}"
            end_str = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d}"
            
            segment = await ffmpeg.trim_video(video_path, start_str, end_str)
            segments.append(segment)
        
        return segments
