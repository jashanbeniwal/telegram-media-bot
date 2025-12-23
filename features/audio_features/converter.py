import os
from utils.ffmpeg_utils import FFmpegHandler
from config import config

class AudioConverter:
    @staticmethod
    async def convert_format(input_path: str, output_format: str, 
                           quality: str = "medium") -> str:
        """Convert audio to different format"""
        ffmpeg = FFmpegHandler()
        
        quality_settings = config.AUDIO_QUALITIES.get(quality, config.AUDIO_QUALITIES["medium"])
        bitrate = quality_settings["bitrate"]
        
        return await ffmpeg.convert_audio(input_path, output_format, bitrate)
    
    @staticmethod
    async def adjust_parameters(input_path: str, speed: float = 1.0,
                              volume: float = 1.0, pitch: float = 1.0) -> str:
        """Adjust audio parameters"""
        ffmpeg = FFmpegHandler()
        
        # Speed and volume adjustment
        output = await ffmpeg.adjust_audio(input_path, speed, volume)
        
        # Pitch adjustment (requires additional processing)
        if pitch != 1.0:
            base = os.path.splitext(os.path.basename(output))[0]
            final_output = os.path.join(config.TEMP_DIR, f"pitch_{base}.mp3")
            
            cmd = [
                config.FFMPEG_PATH,
                '-i', output,
                '-af', f'asetrate=44100*{pitch},aresample=44100',
                final_output,
                '-y'
            ]
            
            await ffmpeg.run_command(cmd)
            os.remove(output)
            return final_output
        
        return output
    
    @staticmethod
    async def apply_effect(input_path: str, effect: str, intensity: float = 1.0) -> str:
        """Apply audio effect"""
        ffmpeg = FFmpegHandler()
        
        effects = {
            "8d": f"apulsator=hz=0.08",
            "reverb": f"aecho=0.8:0.9:{int(1000*intensity)}:{int(500*intensity)}",
            "chorus": f"chorus=0.7:0.9:55:0.4:0.25:{intensity}",
            "flanger": f"flanger=delay=0:depth=2:regen=0:width=71:speed=0.5:shape=sin:phase=25",
            "phaser": f"aphaser=in_gain=0.4:out_gain=0.74:delay=3:decay=0.4:speed=0.5:type=t"
        }
        
        effect_filter = effects.get(effect, "")
        if not effect_filter:
            return input_path
        
        base = os.path.splitext(os.path.basename(input_path))[0]
        output = os.path.join(config.TEMP_DIR, f"{effect}_{base}.mp3")
        
        cmd = [
            config.FFMPEG_PATH,
            '-i', input_path,
            '-af', effect_filter,
            output,
            '-y'
        ]
        
        await ffmpeg.run_command(cmd)
        return output
