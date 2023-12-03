import re
import subprocess
import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class ProgressUpdater:
    def __init__(self, total):
        self.total = total
        self.current = 0

    def update(self):
        self.current += 1
        print(f"{self.current}/{self.total}", end="\r")
        sys.stdout.flush()


def perform_time_operation(timestamp_str, operation, operand):
    # Parse the timestamp string
    timestamp_format = "%M:%S.%f"
    timestamp = datetime.strptime(timestamp_str, timestamp_format)

    # Perform the specified operation
    if operation == "add":
        result_timestamp = timestamp + timedelta(seconds=operand)
    elif operation == "subtract":
        if type(operand) == str:
            operand_timedelta = datetime.strptime(operand, timestamp_format) - datetime(1900, 1, 1, 0, 0, 0)
            result_timestamp = timestamp - operand_timedelta
        else:
            result_timestamp = timestamp - timedelta(seconds=operand)
        # Check if the result is negative and adjust accordingly
        if result_timestamp < datetime(1900, 1, 1, 0, 0, 0):
            result_timestamp = datetime(1900, 1, 1, 0, 0, 0)
    elif operation == "multiply":
        result_timestamp = timestamp * operand
    elif operation == "divide":
        result_timestamp = timestamp / operand
    else:
        raise ValueError(
            "Invalid operation. Supported operations: add, subtract, multiply, divide."
        )

    # Format the result as a timestamp string
    result_timestamp_str = result_timestamp.strftime(timestamp_format)[:-3]

    return result_timestamp_str


def read_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    else:
        print(f"Input file {file_path} not found.")
        sys.exit(1)


def process_segment(
    start_time, end_time, speaker_tag, input_video_file, output_path, progress_updater
):
    # Calculate the duration of the segment
    duration = perform_time_operation(end_time, "subtract", start_time)

    # FFmpeg command with explicit start time and duration
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        input_video_file,
        "-ss",
        perform_time_operation(start_time, "subtract", 0),
        "-t",
        duration,
        "-n",
        output_path,
    ]
    # print(ffmpeg_command)

    # Execute FFmpeg command
    result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE)

    # Check if FFmpeg was successful
    if result.returncode != 0:
        print(f"FFmpeg failed for {output_path}.flac")
        # Print the error messages from stderr
        print(result.stderr)
    progress_updater.update()


def combine_flac_files(input_directory, output_file):
    # Get all FLAC files in the input directory
    flac_files = [
        file for file in os.listdir(input_directory) if file.endswith(".flac")
    ]

    # Sort the FLAC files to ensure the correct order
    flac_files.sort()

    # Construct the input file list for ffmpeg
    input_files = [os.path.join(input_directory, file) for file in flac_files]

    # Use ffmpeg to re-encode and concatenate the FLAC files
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        f"concat:{'|'.join(input_files)}",
        "-c:a",
        "flac",
        output_file,
    ]

    # print(ffmpeg_command)

    # Run the ffmpeg command
    subprocess.run(ffmpeg_command, stderr=subprocess.PIPE)


def get_directories(path):
    # Get a list of all items (files and directories) in the given path
    all_items = os.listdir(path)

    # Filter out only directories
    directories = [
        item for item in all_items if os.path.isdir(os.path.join(path, item))
    ]

    return directories


def main():
    # Your regex pattern
    pattern = re.compile(
        r"(\d{2}:\d{2}.\d{0,3}) --> (\d{2}:\d{2}.\d{0,3})\n\[([A-Za-z0-9_]+)\]"
    )

    # Check if the correct number of command line arguments is provided
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_vtt_file> <input_video_file>")
        sys.exit(1)

    # Path to your input VTT file
    input_vtt_file = os.path.join(
        sys.argv[1], Path(sys.argv[2]).with_suffix(".vtt").name
    )

    # Input video file
    input_video_file = sys.argv[2]

    # Read the VTT file
    vtt_content = read_file(input_vtt_file)

    # Find all matches in the VTT content
    matches = pattern.findall(vtt_content)
    curSpeaker = ""
    curStartTime = ""
    curEndTime = ""
    test = ""
    for start_time, end_time, speaker_tag in matches:
        if curSpeaker == speaker_tag:
            curEndTime = end_time
        else:
            if curSpeaker != "":
                test += f"\n{curStartTime} --> {curEndTime}\n[{curSpeaker}]\n"
            curSpeaker = speaker_tag
            curStartTime = start_time
            curEndTime = end_time
    test += f"\n{curStartTime} --> {curEndTime}\n[{curSpeaker}]\n"

    matches = pattern.findall(test)

    # List to store the future objects
    futures = []
    # Progress updater
    progress_updater = ProgressUpdater(len(matches))
    # Iterate through matches and submit FFmpeg commands for parallel execution
    with ThreadPoolExecutor() as executor:
        for start_time, end_time, speaker_tag in matches:
            curSpeaker = os.path.join(sys.argv[1], speaker_tag)
            if not os.path.exists(curSpeaker):
                # If not, create the directory
                os.makedirs(curSpeaker)
            output_path = os.path.join(
                curSpeaker, f"{start_time.replace(':', '')}.flac"
            )

            # Check if the output file already exists
            if not os.path.exists(output_path):
                # Submit the task to the thread pool
                future = executor.submit(
                    process_segment,
                    start_time,
                    end_time,
                    speaker_tag,
                    input_video_file,
                    output_path,
                    progress_updater,
                )
                futures.append(future)
            else:
                print(f"File {output_path} already exists. Skipping.")

    global futuresCount
    futuresCount = len(futures)
    # Wait for all threads to complete
    for future in futures:
        future.result()
    for speaker in get_directories(sys.argv[1]):
        combine_flac_files(
            os.path.join(sys.argv[1], speaker),
            os.path.join(sys.argv[1], speaker + ".flac"),
        )
    print("Done")


if __name__ == "__main__":
    main()
