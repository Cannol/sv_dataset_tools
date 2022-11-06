from bases.targets import Target
from bases.targets import get_all_targets_max_range
import os

path = r'D:\Sanatar\Desktop\新标注'
out_file = r'D:\Sanatar\Desktop\out-new.csv'
names = os.listdir(path)
names.sort()
Target.SetLength(1)


def get_all_metas(from_path):

    file_list = []
    for root, dirs, files in os.walk(from_path):
        for file in files:
            if file.endswith('.meta'):
                file_list.append(os.path.join(root, file))

    return file_list


contents = []
for name in names:
    # meta_dir = os.path.join(path, name, 'targets')
    meta_dir = get_all_metas(os.path.join(path, name))
    print('==== ', name, len(meta_dir), ' ====')
    contents.append(get_all_targets_max_range(meta_dir))

csv_title = 'vehicle,large,airplane,ship,train,error,left,right,top,bottom\n'
with open(out_file, 'w') as f:
    f.write(csv_title)
    for name, content in zip(names, contents):
        cls, error, left, right, top, bottom = content
        vehicle = cls.get('vehicle', 0)
        large = cls.get('large-vehicle', 0)
        airplane = cls.get('airplane', 0)
        ship = cls.get('ship', 0)
        train = cls.get('train', 0)
        f.write(f'{vehicle},{large},{airplane},{ship},{train},{error},{left},{right},{top},{bottom}\n')





