import os
import pyembroidery
import json
import threading
import shutil
import re
from queue import Queue

# ? Configurations
Input_Directory = "input"
Output_folder = "output"
Saparate_Preview = False
Clean_Input_Directory = True
Record_JSON_File = os.path.join(Output_folder, "records.json")
LogPrefix = "DSTtoIMAGE >> "
ConcurrentConversionLimit = 4
ConcurrentConversion = True

Preview_File_Extension = "png"
DST_File_Extensions = ["dst", "DST"]

Blouse_FolderRegexs = ["blz", "blouse"]
C_FolderRegexs = ["c"]
Pallu_FolderRegexs = ["pallu", "pALU"]
Skirt_FolderRegexs = ["skirt", "skt"]
Debug = []
Records = {}

# @ Program Starts Here
task_queue = Queue()


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"
    
class Emojis:
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    INFO = "🔍"
    PROCESSING = "🔄"
    SKIP = "⏭️ "

def remove_color_codes(text):
    """Remove ANSI color codes from the text."""
    return re.sub(r'\033\[[0-9;]*m', '', text)

def log(message, level="info"):
    """
    Logs messages with colors based on the level.
    Levels: info, warning, error, success, processing, skip
    """
    color_map = {
        "info": Colors.BLUE,
        "warning": Colors.YELLOW,
        "error": Colors.RED,
        "success": Colors.GREEN,
        "processing": Colors.CYAN,
        "skip": Colors.MAGENTA,
    }
    
    emoji_map = {
        "info": Emojis.INFO,
        "warning": Emojis.WARNING,
        "error": Emojis.ERROR,
        "success": Emojis.SUCCESS,
        "processing": Emojis.PROCESSING,
        "skip": Emojis.SKIP,
    }

    prefix_color = color_map.get(level, Colors.GRAY)
    styled_message = f"{prefix_color}{LogPrefix}{emoji_map.get(level, '')} {message}{Colors.RESET}"

    print(styled_message)
    
    clean_message = remove_color_codes(styled_message)
    Debug.append(clean_message)

def save_debug_log():
    """Save the debug log to a file."""
    with open("Debug.log", "w", encoding="utf-8") as f:
        f.write("\n".join(Debug))
    log("Debug log saved", level="success")

def save_records():
    """Saves current records to the JSON file."""
    with open(Record_JSON_File, "w", encoding="utf-8") as f:
        json.dump(Records, f, indent=4)
        log(f"Records saved in {Record_JSON_File}", level="success")

def compile_dst_file(file_path, output_folder, design_name, file_type):
    """Processes a DST file and generates the preview image."""
    if file_path.endswith(tuple(DST_File_Extensions)):
        try:
            pattern = pyembroidery.read_dst(file_path)
            output_file_name = f"{file_type}.{Preview_File_Extension}"
            output_file_path = os.path.join(output_folder, design_name, output_file_name)

            pyembroidery.write_png(pattern, output_file_path)

            if design_name not in Records:
                Records[design_name] = {}
            Records[design_name][file_type] = len(pattern)

            log(f"{file_type} file converted: {file_path}", level="success")
        except Exception as e:
            log(f"Error processing {file_path}: {e}", level="error")
    else:
        log(f"Invalid file type (not DST): {file_path}", level="error")

def worker():
    while True:
        task = task_queue.get()
        if task is None:
            break
        log(f"Processing {task[3]}: {task[0]}", level="processing")
        file_path, output_folder, design_name, file_type = task
        compile_dst_file(file_path, output_folder, design_name, file_type)
        task_queue.task_done()

def process_folder(folder_path):
    """Processes a folder containing design files."""
    design_name = os.path.basename(folder_path)
    log(f"Processing Folder: {design_name}", level="processing")

    if not os.path.exists(Output_folder):
        os.makedirs(Output_folder)

    design_output_folder = os.path.join(Output_folder, design_name)
    if not os.path.exists(design_output_folder):
        os.makedirs(design_output_folder)

    files_found = {"blouse": False, "c": False, "pallu": False, "skirt": False}

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        for file_type, regex_list in {
            "Blouse": Blouse_FolderRegexs,
            "C": C_FolderRegexs,
            "Pallu": Pallu_FolderRegexs,
            "Skirt": Skirt_FolderRegexs,
        }.items():
            if any(regex.lower() in file_name.lower() for regex in regex_list):
                renamed_file_path = os.path.join(
                    design_output_folder, f"{file_type}.{DST_File_Extensions[0].lower()}"
                )
                preview_file_path = os.path.join(
                    design_output_folder, f"{file_type}.{Preview_File_Extension}"
                )

                if not os.path.exists(renamed_file_path):
                    if os.path.exists(file_path):
                        shutil.copy(file_path, renamed_file_path)
                        log(f"Copied and renamed: {file_path} -> {renamed_file_path}", level="success")
                    else:
                        log(f"Missing source file for {file_type} in input: {file_path}", level="warning")
                        if design_name in Records and file_type in Records[design_name]:
                            del Records[design_name][file_type]
                            log(f"Removed {file_type} record for {design_name}", level="warning")
                        continue

                if (
                    design_name in Records
                    and file_type in Records[design_name]
                    and os.path.exists(preview_file_path)
                ):
                    log(f"Skipping {file_type} for {design_name} (already processed)", level="skip")
                    files_found[file_type.lower()] = True
                else:
                    log(f"Queuing {file_type} for {design_name}", level="processing")
                    task_queue.put((renamed_file_path, Output_folder, design_name, file_type))
                    files_found[file_type.lower()] = True

    for file_type, found in files_found.items():
        if not found:
            log(f"Missing {file_type.capitalize()} for {design_name}", level="warning")
            if design_name in Records and file_type.capitalize() in Records[design_name]:
                del Records[design_name][file_type.capitalize()]
                log(f"Updated records: Removed {file_type} for {design_name}", level="warning")

def load_records():
    """Loads existing records from the JSON file."""
    global Records
    if os.path.exists(Record_JSON_File):
        with open(Record_JSON_File, "r", encoding="utf-8") as f:
            Records = json.load(f)
            log("Records loaded from existing JSON file")
    else:
        log("No existing records file found, starting fresh")

def process_input_folder(input_directory):
    """Processes all folders in the input directory."""
    load_records()

    for _ in range(ConcurrentConversionLimit):
        threading.Thread(target=worker, daemon=True).start()

    for item in os.listdir(input_directory):
        design_folder_path = os.path.join(input_directory, item)
        if os.path.isdir(design_folder_path):
            process_folder(design_folder_path)
        else:
            log(f"Skipping non-folder item: {design_folder_path}", level="skip")

    task_queue.join()
    save_records()
    save_debug_log()

# ! Main Part
try:
    process_input_folder(Input_Directory)
except KeyboardInterrupt:
    log("KeyboardInterrupt: Exiting Program", level="error")
    save_records()
    save_debug_log()
    exit(0)