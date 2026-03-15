#!/usr/bin/env python3
"""
Voice and Video Extractor
Extracts voice (audio) and video separately from a video file.
"""

import os
import sys
from pathlib import Path
from moviepy.editor import VideoFileClip
import argparse
from tqdm import tqdm


class MediaExtractor:
    """Extract audio and video from video files separately."""
    
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
    
    def __init__(self, output_dir='extracted_media'):
        """
        Initialize the MediaExtractor.
        
        Args:
            output_dir (str): Directory to store extracted files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def is_supported_format(self, file_path):
        """Check if file format is supported."""
        return Path(file_path).suffix.lower() in self.SUPPORTED_FORMATS
    
    def extract_audio(self, video_path, output_audio_path=None):
        """
        Extract audio from video file.
        
        Args:
            video_path (str): Path to video file
            output_audio_path (str): Output audio file path (optional)
            
        Returns:
            str: Path to extracted audio file
        """
        try:
            print(f"\n📹 Loading video: {video_path}")
            video = VideoFileClip(video_path)
            
            if video.audio is None:
                print("❌ No audio found in this video!")
                return None
            
            if output_audio_path is None:
                video_name = Path(video_path).stem
                output_audio_path = self.output_dir / f"{video_name}_audio.mp3"
            
            print(f"🎵 Extracting audio to: {output_audio_path}")
            video.audio.write_audiofile(
                str(output_audio_path),
                verbose=False,
                logger=None
            )
            video.close()
            
            print(f"✅ Audio extracted successfully!")
            return str(output_audio_path)
            
        except Exception as e:
            print(f"❌ Error extracting audio: {e}")
            return None
    
    def extract_video_without_audio(self, video_path, output_video_path=None):
        """
        Extract video without audio.
        
        Args:
            video_path (str): Path to video file
            output_video_path (str): Output video file path (optional)
            
        Returns:
            str: Path to extracted video file
        """
        try:
            print(f"\n📹 Loading video: {video_path}")
            video = VideoFileClip(video_path)
            
            if output_video_path is None:
                video_name = Path(video_path).stem
                output_video_path = self.output_dir / f"{video_name}_video_no_audio.mp4"
            
            # Set audio to None to remove audio
            video_without_audio = video.without_audio()
            
            print(f"🎬 Extracting video (without audio) to: {output_video_path}")
            video_without_audio.write_videofile(
                str(output_video_path),
                verbose=False,
                logger=None
            )
            video.close()
            video_without_audio.close()
            
            print(f"✅ Video extracted successfully!")
            return str(output_video_path)
            
        except Exception as e:
            print(f"❌ Error extracting video: {e}")
            return None
    
    def extract_both(self, video_path, audio_path=None, video_path_output=None):
        """
        Extract both audio and video separately.
        
        Args:
            video_path (str): Path to video file
            audio_path (str): Output audio path (optional)
            video_path_output (str): Output video path (optional)
            
        Returns:
            tuple: (audio_path, video_path) or (None, None) on failure
        """
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return None, None
        
        if not self.is_supported_format(video_path):
            print(f"❌ Unsupported format. Supported formats: {self.SUPPORTED_FORMATS}")
            return None, None
        
        print(f"\n{'='*60}")
        print(f"🎯 Extracting Media from: {video_path}")
        print(f"{'='*60}")
        
        audio_result = self.extract_audio(video_path, audio_path)
        video_result = self.extract_video_without_audio(video_path, video_path_output)
        
        return audio_result, video_result


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Extract audio and video separately from video files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_media.py input_video.mp4
  python extract_media.py input_video.mp4 -o ./my_extracts
  python extract_media.py video.mkv -a output_audio.mp3 -v output_video.mp4
        """
    )
    
    parser.add_argument('video_file', help='Path to video file')
    parser.add_argument('-o', '--output-dir', default='extracted_media',
                        help='Output directory for extracted files (default: extracted_media)')
    parser.add_argument('-a', '--audio-output', help='Custom audio output path')
    parser.add_argument('-v', '--video-output', help='Custom video output path')
    
    args = parser.parse_args()
    
    extractor = MediaExtractor(output_dir=args.output_dir)
    audio_file, video_file = extractor.extract_both(
        args.video_file,
        audio_path=args.audio_output,
        video_path_output=args.video_output
    )
    
    if audio_file and video_file:
        print(f"\n{'='*60}")
        print("🎉 Extraction Complete!")
        print(f"{'='*60}")
        print(f"📊 Summary:")
        print(f"   Audio file: {audio_file}")
        print(f"   Video file: {video_file}")
        print(f"{'='*60}\n")
    else:
        print("\n❌ Extraction failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
