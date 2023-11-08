import cv2
import os

import numpy as np
import matplotlib.pyplot as plt

# img_path = '/data1/VISO_dataset/coco/car/train2017/003010.jpg'
img_path = '/data1/ORSV_coll/pics'
# img_path = '/data2/OTB-100/demo/Jogging.2/0011.jpg'

out_dir = '/data1/ORSV_coll/pics'

img_files = [os.path.join(img_path, file) for file in os.listdir(img_path) if file.endswith('tiff')]

for img_file in img_files:
    print(img_file)
    plt.figure(figsize=(12, 8), dpi=100)
    ax3 = plt.subplot(211)
    ax1 = plt.subplot(223)
    ax2 = plt.subplot(224)

    img = cv2.imread(img_file)
    length = img.shape[0] * img.shape[1]
    x1, x2, x3 = cv2.split(img)
    x1 = np.reshape(x1, -1)
    x2 = np.reshape(x2, -1)
    x3 = np.reshape(x3, -1)

    # x1 = np.random.normal(0, 0.8, 1000)
    # x2 = np.random.normal(-2, 1, 1000)
    # x3 = np.random.normal(3, 2, 1000)
    kwargs = dict(histtype='stepfilled', alpha=0.5, bins=256)
    ax1.hist(x1, color='blue', **kwargs)
    ax1.hist(x2, color='green', **kwargs)
    ax1.hist(x3, color='red', **kwargs)
    # plt.show()

    # plt.figure()
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_gray = np.reshape(img_gray, -1)
    ax2.hist(img_gray, histtype='stepfilled', alpha=1.0, color='gray', bins=256)

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    ax3.imshow(img_rgb)
    ax1.set_title('RGB')
    ax2.set_title('Gray')
    name = os.path.basename(img_file)[:-5]
    plt.suptitle('Histograms of %s' % name)
    # plt.show()
    plt.savefig(os.path.join(out_dir, '%s.pdf' % name))
    plt.close()
