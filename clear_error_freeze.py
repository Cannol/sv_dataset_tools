import os

from bases.targets import Target

path = r'D:\Sanatar\Desktop\xiufu'
out = r'D:\Sanatar\Desktop\xiufu-test'
os.makedirs(out, exist_ok=True)
Target.SetLength(1)
Target.SetGlobalOffsize(0, 0, 12000, 5000)


def get_all_metas(from_path):

    file_list = []
    for root, dirs, files in os.walk(from_path):
        for file in files:
            if file.endswith('.meta'):
                file_list.append(os.path.join(root, file))

    return file_list


metas = get_all_metas(path)
for meta in metas:
    name = os.path.basename(os.path.dirname(os.path.dirname(meta)))
    try:
        target = Target.MakeNewFromJsonFile(meta)
        out_dir = os.path.join(out, name, 'targets')
        os.makedirs(out_dir, exist_ok=True)
        target.save_file(out_dir, base_path=True)
    except:
        print('Error Skip--> %s' % meta)
