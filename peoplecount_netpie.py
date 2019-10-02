import cv2
import imutils
from imutils.video import VideoStream
import time
import argparse
from counter_utils import *

# Global variables
# initialize the frame dimensions (we'll set them as soon as we read
# the first frame from the video)
W = None
H = None
frameSize = (600, 800)
areaFrame = None
MinContourArea = None
MaxContourArea = None

# line's position
OffsetY = 0
OffsetX = 0
sizeLong = 0
padding = 0
margin = 0


def setInitialVaraible(w, h):
    global W, H, frameSize, areaFrame, MinContourArea, MaxContourArea, OffsetX, OffsetY, sizeLong, padding, margin
    # Set initial frame size.
    W = w
    H = h
    frameSize = (w, h)
    areaFrame = frameSize[0] * frameSize[1]

    # minimum size 0.01%/maximum size 0.1%
    MinContourArea = areaFrame * 0.05
    MaxContourArea = areaFrame * 0.5

    # line's position
    OffsetY = int(frameSize[1] * 0.6)
    # OffsetY = 0
    OffsetX = -30
    sizeLong = int(frameSize[0] * 0.4)
    # padding = frameSize[1] * 0.02
    margin = frameSize[1] * 0.03


# tracking variable
pointMove = []
firstTrack = []
statusMove = []

# define counting number of people
countPeople = 0

idle_time = 0

# object for BackgroundSubtractor
fgbg = cv2.createBackgroundSubtractorMOG2(
    history=2000, varThreshold=100, detectShadows=False)
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", help="path to the video file")
args = vars(ap.parse_args())
# How sizeLong have we been tracking


# Initialize mutithreading the video stream.
if args["video"] is None:
    camera = VideoStream(src=0, usePiCamera=True,
                         resolution=frameSize, framerate=32).start()
else:
    camera = cv2.VideoCapture(args["video"])

time.sleep(2.0)


# Get the next frame.
while True:
    # If using a webcam instead of the Pi Camera,
    if args["video"] is None:
        Frame = camera.read()
    # If using a video file
    else:
        _, Frame = camera.read()
        # cannot fetch Frame
        if (Frame is None):
            break
        Frame = imutils.resize(Frame, width=500)

    # cannot fetch Frame
    if (Frame is None):
        break

    # if the frame dimensions are empty, set them
    if W is None or H is None:
        (h, w) = Frame.shape[:2]
        setInitialVaraible(w, h)

    # gray-scale convertion and Gaussian blur filter applying
    Gray = cv2.cvtColor(Frame, cv2.COLOR_BGR2GRAY)
    ret, Gray = cv2.threshold(Gray, 40, 100, cv2.THRESH_BINARY)
    if idle_time < 2:
        idle_time += 1
        continue
        # OffsetY += 15
    fgmask = fgbg.apply(Gray)
    fgmask = cv2.erode(fgmask, None, 20)

    cnts = cv2.findContours(
        fgmask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    # plot reference lines (entrance and exit lines)
    centerLine = (int(frameSize[0] / 2 - OffsetX), int(frameSize[1] - OffsetY))
    CoorExitLine1 = (centerLine[0] - sizeLong, centerLine[1])
    CoorExitLine2 = (centerLine[0] + sizeLong, centerLine[1])
    cv2.line(Frame, CoorExitLine1, CoorExitLine2, (0, 0, 255), 2)
    Line = (CoorExitLine1[0], CoorExitLine1[1], CoorExitLine2[0] -
            CoorExitLine1[0], CoorExitLine2[1] - CoorExitLine2[1])

    # check all found countours
    for c in cnts:
        Area = cv2.contourArea(c)
        rec = cv2.boundingRect(c)
        p1, p2 = definePoint12(rec)
        cv2.rectangle(Frame, p1, p2, (0, 255, 200), 2)
        if Area > MaxContourArea:
            continue
        elif Area < MinContourArea:
            break

        # find object's centroid
        ObjectCentroid = setCenter(rec)
        indexTrack = TrackMove(rec, Line)

        (x, y, w, h) = firstTrack[indexTrack]
        colorB = 0
        colorR = 0
        firstCenter = setCenter(firstTrack[indexTrack])

        if CheckLineCrossing(firstCenter, CoorExitLine1, CoorExitLine2):
            colorR = 255
        else:
            colorB = 255

        cv2.rectangle(Frame, p1, p2, (colorB, int(
            (indexTrack + 1) * 70), colorR), 2)

        if abs(firstCenter[1] - CoorExitLine1[1]) > margin and abs(ObjectCentroid[1] - CoorExitLine1[1]) > margin:
            if not CheckLineCrossing(firstCenter, CoorExitLine1, CoorExitLine2) and CheckLineCrossing(ObjectCentroid,
                                                                                                      CoorExitLine1,
                                                                                                      CoorExitLine2):
                countPeople -= 1
                firstTrack[indexTrack] = rec
            elif not CheckLineCrossing(ObjectCentroid, CoorExitLine1, CoorExitLine2) and CheckLineCrossing(firstCenter,
                                                                                                           CoorExitLine1,
                                                                                                           CoorExitLine2):
                countPeople += 1
                firstTrack[indexTrack] = rec
    for i in range(len(statusMove)):
        if statusMove[i] <= 0:
            popIndex(firstTrack, pointMove, statusMove, i)
            break

    # Write entrance and exit counter values on frame and shows it
    cv2.putText(Frame, "count: {}".format(str(countPeople)), (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (250, 0, 1), 2)

    cv2.imshow("Original Frame", Frame)
    for i in range(len(statusMove)):
        statusMove[i] -= 1
    idle_time += 1
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    # cv2.waitKey(0)

# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()
