import os
import pyembroidery
import threading

FOLDER_PATH = 'input'
OUTPUT_FOLDER = 'output'

def ThreadedConvert(file_path, output_file_path):
    pattern = pyembroidery.read_dst(file_path)
    pyembroidery.write_png(pattern, output_file_path)

for file_name in os.listdir(FOLDER_PATH):
    print(file_name)
    if file_name.endswith('.DST') or file_name.endswith('.dst'):
        file_path = os.path.join(FOLDER_PATH, file_name)
        output_file_name = os.path.splitext(file_name)[0] + '.png'
        output_file_path = os.path.join(OUTPUT_FOLDER, output_file_name)
        thread = threading.Thread(target=ThreadedConvert, args=(file_path, output_file_path))
        thread.start()