# OpenCV People Counter

https://www.pyimagesearch.com/2018/08/13/opencv-people-counter/

```bash
python people_counter.py --prototxt mobilenet_ssd/MobileNetSSD_deploy.prototxt \
	--model mobilenet_ssd/MobileNetSSD_deploy.caffemodel \
	--input videos/vdo_01.mp4 --output output/output_01.avi

python people_counter.py --prototxt mobilenet_ssd/MobileNetSSD_deploy.prototxt \
	--model mobilenet_ssd/MobileNetSSD_deploy.caffemodel \
	--input videos/vdo_01.mp4 --output output/output_02.avi
```

## Troubleshoot

### Multiprocessing causes Python to crash

Crash:

```
objc[40242]: +[__NSPlaceholderDate initialize] may have been in progress in another thread when fork() was called.
objc[40242]: +[__NSPlaceholderDate initialize] may have been in progress in another thread when fork() was called. We cannot safely call it or ignore it in the fork() child process. Crashing instead. Set a breakpoint on objc_initializeAfterForkError to debug.
```

Solution:

```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

https://stackoverflow.com/questions/50168647/multiprocessing-causes-python-to-crash-and-gives-an-error-may-have-been-in-progr

## Reference

[Simple object tracking with OpenCV](https://www.pyimagesearch.com/2018/07/23/simple-object-tracking-with-opencv/)

[Object detection with deep learning and OpenCV](https://www.pyimagesearch.com/2017/09/11/object-detection-with-deep-learning-and-opencv/)
