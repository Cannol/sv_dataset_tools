import os
import shutil

def find_all(root_path, post_fix):
    out = []
    for r, folder, files in os.walk(root_path):
        for f in files:
            if f.endswith(post_fix):
                out.append(os.path.join(r, f))
    out.sort()
    return out

path1 = '/data1/IPIUSVX-Det-v1-COCO'
out_path = '/data1/IPIUSVX-Det-v1-COCO_json_only'

for file in find_all(path1, '.json'):
    folder_name = os.path.basename(os.path.dirname(file))
    file_name = os.path.basename(file)
    folder_name = folder_name[:-8] + '20221106'
    save_path = os.path.join(out_path, folder_name)
    os.makedirs(save_path, exist_ok=True)
    shutil.copy(file, os.path.join(save_path, file_name))
