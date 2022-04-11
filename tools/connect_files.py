import os
import sys



def move_annos_to(source_path, des_path):
    vids = os.listdir(source_path)
    os.makedirs(des_path, exist_ok=True)
    for i in vids:
        os.makedirs(os.path.join(des_path, i), exist_ok=True)
        s = os.path.join(source_path, i, 'annotations')
        d = os.path.join(des_path, i, 'annotations')
        os.system('mv %s %s' % (s, d))

def create_link(source_path, des_path):
    vids = os.listdir(source_path)

    for i in vids:
        s = os.path.join(source_path, i, 'annotations')
        d = os.path.join(des_path, i, 'annotations')
        os.system('ln -s %s %s' % (d, s))

# move_annos_to(source_path='/data1/IPIU_dataset_v2/first_label',
#               des_path='/data1/IPIU_dataset_v2/annos_1st')

create_link(source_path='/data1/IPIU_dataset_v2/first_label',
            des_path='/data1/IPIU_dataset_v2/target_annos')