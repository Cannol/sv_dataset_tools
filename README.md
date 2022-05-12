# 卫星视频标注工具
2022.5.12 更新 第一版发布内测版本 V1.1 beta
- 修复了文件保存bug，并加入了新的自动保存机制
- 为操作界面添加了更多可视化效果，标注过程更清晰容易


# Python环境需求(没有标注具体版本的安装默认最新即可)
- python == 3.8.*
- opencv-python == 4.5.5.62
- numpy == 1.22.*
- matplotlib
- coloredlogs
- opencv-contrib-python == 4.5.5.64
- pillow
- pyyaml
- tqdm

我们提供了requirement.txt文件，您可以直接在python环境中通过pip来安装他们：
``` shell
pip install -r requirement.txt -i https://mirrors.aliyun.com/pypi/simple
```

# 配置与进入

## 配置文件video_target_selector.yaml
在配置完成上述环境之后，您还需要修改configs/video_target_selector.yaml文件
下面是一个配置模板，如果您的配置文件不小心被损坏，可以重新copy一份覆盖：

``` yaml
VideoFilePath: '/data1/ORSV/part2/ori/JL103B_MSS_20180104153259_100003219_102_001_L1B_MSS.avi'
ImageSequence: '.tiff'  # 如果上面的路径是视频文件，则该项无效
SaveToDirectory: 'annotations'    # 标注数据将保存在该文件夹中annotations文件夹内，其他辅助数据将存放在此路径
TargetFolderName: 'targets'   # 存放标注目标的文件夹

SelectArea: [4000,4000,6000,5000]   # x,y, xx ,yy
AnnotatorWinHeight: 600
AnnotatorWinWidth: 1200
TargetClasses:
  - ['vehicle', [255, 0, 0]]
  - ['large-vehicle', [0, 255, 0]]
  - ['ship', [0, 0, 255]]
  - ['airplane', [255, 255, 0]]
  - ['train', [255, 0 ,255]]

CacheDirectory: 'tmp'
CacheImage: '.tiff'

WindowSize: [1200, 600]  # 主界面的窗口尺寸，不要修改

VideoFormat: ['.mp4', '.MP4', '.avi', '.AVI']  # 视频格式，不要修改
ErrorFrame: 'skip'   # skip, interpolation, stop  # 不要修改

# Frame Settings
StartScale: 1.0   # 不要修改
ScaleList: null    # 不要修改

AutoSaving: 10000 # 自动保存间隔的毫秒数 1秒 = 1000毫秒，如果设置为0或小于0的数则取消自动保存（手动保存模式需要手动按保存按键或退出的时候自动保存）
```

其中您可以修改的是：
- VideoFilePath：视频的完整路径
- ImageSequence：如果VideoFilePath为视频文件，则无需设置此项；如果VideoFilePath是一个图片序列所在文件夹，那么请设置此项为文件夹中目标图像的后缀
- SaveToDirectory：打算将标注软件产生的输出保存到的路径（相对路径默认为相对于项目所在文件夹）
- TargetFolderName：标注结果存放的文件夹名称
- SelectArea：打算标注的区域（相对于VideoFilePath视频的crop区域）[左上角x1，左上角y1，右上角x2，右上角y2] 注意：0 <= x1 < x2 < video_width; 0 <= y1 < y2 < video_height
- AnnotatorWinHeight，AnnotatorWinWidth: 标注时候可见的（经过缩放后的）视野范围的高和宽，即窗口的大小
- TargetClasses： 目标类别名称不要修改，您可以修改后面的颜色显示，[bule，green，red]
- CacheDirectory：缓存存放的目录（绝对路径和相对路径均可）
- CacheImage：缓存图像保存的格式，建议tiff，最小的无损图像
- AutoSaving：自动保存的时间间隔，建议10s，不建议太频繁


## 运行程序
运行程序请在项目根目录下运行（即在sv_dataset_tools文件夹中运行，不要在其他目录或子文件夹中运行）
```
python run_video_annotator.py
```


# 主界面


# 按键矫正
为了适应在不同操作系统环境下的按键映射差异，我们为按键加入了矫正操作，在主界面按b即可进入，进入后按照上面的中文提示进行按键（一定要看提示操作噢！）
- 

# 多目标标注模式

## 按键设置
- a/s/d/f：后退一帧，前进一帧，后退10帧，前进10帧
- ESC：退出程序，根据提示，再按ESC取消退出，按Enter回车确认退出，注意：退出的时候会再次执行保存结果操作，以防止自动保存未生效；另外一定要注意，一定要通过ESC正常途径退出，切忌直接kill掉程序，可能会导致结果保存出现问题！
- 