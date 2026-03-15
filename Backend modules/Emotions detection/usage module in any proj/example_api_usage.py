from DeceptronLib.emotion_processor import process_video_file
import json

# --- CONFIGURATION ---
VIDEO_TO_ANALYZE = "movie.mp4" # Pass your video path here
OUTPUT_DIR = "processed_results"

print(f"--- Starting Analysis on: {VIDEO_TO_ANALYZE} ---")

# 1. Call the function and get EVERYTHING back as a return value
result = process_video_file(VIDEO_TO_ANALYZE, output_folder=OUTPUT_DIR)

if result["status"] == "success":
    print("\n✅ Processing Complete!")
    print(f"📁 Video saved at: {result['output_path']}")
    print(f"🎞️ Total Frames: {result['total_frames']}")
    
    print("\n📊 EMOTION PERCENTAGES:")
    for emotion, percent in result["stats"].items():
        print(f"   - {emotion}: {percent}%")
    
    print("\n⏳ EMOTION TIMELINE (Durations):")
    for event in result["timeline"]:
        duration = event['end'] - event['start'] + 1
        print(f"   - {event['emotion']}: Frame {event['start']} to {event['end']} ({duration} frames)")

    # You can also save this data to a JSON file for other projects to read
    with open("analysis_report.json", "w") as f:
        json.dump(result, f, indent=4)
    print("\n📝 Full details saved to analysis_report.json")

else:
    print(f"❌ Error: {result['message']}")
