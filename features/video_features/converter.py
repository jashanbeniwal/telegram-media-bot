import os
from utils.ffmpeg_utils import FFmpegHandler
from config import config

class VideoConverter:
    @staticmethod
    async def convert_format(input_path: str, output_format: str, 
                           quality: str = "medium") -> str:
        """Convert video to different format"""
        ffmpeg = FFmpegHandler()
        
        quality_settings = config.VIDEO_QUALITIES.get(quality, config.VIDEO_QUALITIES["720p"])
        
        return await ffmpeg.convert_video(input_path, output_format, quality_settings)
    
    @staticmethod
    async def convert_to_gif(input_path: str, start_time: str = "00:00:00",
                           duration: str = "00:00:05", fps: int = 10,
                           width: int = 480) -> str:
        """Convert video to GIF"""
        ffmpeg = FFmpegHandler()
        return await ffmpeg.create_gif(input_path, start_time, duration, fps, width)
    
    @staticmethod
    async def compress_video(input_path: str, target_size_mb: int) -> str:
        """Compress video to target size"""
        ffmpeg = FFmpegHandler()
        return await ffmpeg.compress_video(input_path, target_size_mb)
    
    @staticmethod
    async def optimize_video(input_path: str) -> str:
        """Optimize video for web"""
        ffmpeg = FFmpegHandler()
        
        # Get original info
        info = await ffmpeg.get_media_info(input_path)
        
        # Determine optimal settings
        width = next((s.get('width') for s in info.get('streams', []) 
                     if s.get('codec_type') == 'video'), 1920)
        
        if width > 1920:
            resolution = "1920x1080"
        elif width > 1280:
            resolution = "1280x720"
        elif width > 854:
            resolution = "854x480"
        else:
            resolution = "640x360"
        
        quality_settings = {"resolution": resolution, "bitrate": "1500k"}
        
        base = os.path.splitext(os.path.basename(input_path))[0]
        output = os.path.join(config.TEMP_DIR, f"optimized_{base}.mp4")
        
        cmd = [
            config.FFMPEG_PATH,
            '-i', input_path,
            '-s', resolution,
            '-b:v', '1500k',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            output,
            '-y'
        ]
        
        await ffmpeg.run_command(cmd)
        return output
