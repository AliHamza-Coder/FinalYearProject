import os
import sys
from modules.camera_engine import run_camera_analysis
from modules.video_engine import process_video

def main():
    """
    EntryPoint for the Deceptron Emotion Detection application.
    Allows user to choose between Live Camera and Video Processing.
    """
    print("====================================")
    print("   DECEPTRON EMOTION DETECTION      ")
    print("====================================")
    print("1. Live Camera Detection")
    print("2. Process Video File")
    print("q. Quit")
    
    choice = input("\nSelect an option: ").strip().lower()

    if choice == '1':
        try:
            run_camera_analysis()
        except KeyboardInterrupt:
            print("\nStopped by user.")
    
    elif choice == '2':
        video_path = input("Enter the path to your video file: ").strip()
        # Remove quotes if user dragged and dropped the file
        video_path = video_path.replace('"', '').replace("'", "")
        
        if os.path.exists(video_path):
            try:
                process_video(video_path)
            except Exception as e:
                print(f"Error during video processing: {e}")
        else:
            print(f"Error: File '{video_path}' not found.")
            
    elif choice == 'q':
        print("Exiting...")
        sys.exit()
    else:
        print("Invalid choice. Please run again.")

if __name__ == "__main__":
    main()
