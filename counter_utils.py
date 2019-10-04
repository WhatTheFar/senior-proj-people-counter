import cv2
import numpy as np
import imutils
from imutils.video import VideoStream
import time


def start_simple_counter(video, debug, output, on_people_count):
    def check_line_crossing(center_move, coor_exit_line1, coor_exit_line2):
        (x, y) = center_move
        # outside
        if (y > coor_exit_line1[1]) and (x >= coor_exit_line1[0]):
            return True
        # inside
        else:
            return False

    def auto_pop(arr, length):
        if len(arr) > length:
            arr.pop(0)

    def define_point12(rec):
        return (rec[0], rec[1]), (rec[2] + rec[0], rec[3] + rec[1])

    def set_center(box):
        return int(box[0] + box[2] / 2), int(box[1] + box[3] / 2)

    def find_distance(rec1, rec2):
        distance = 10000
        if rec1 is not None and rec2 is not None:
            center_rec1 = set_center(rec1)
            center_rec2 = set_center(rec2)
            diff_min_x = abs(center_rec1[0] - center_rec2[0])
            diff_min_y = abs(center_rec1[1] - center_rec2[1])
            distance = (pow(diff_min_x, 2) + pow(diff_min_y, 2)) ** (1 / 2)
        return distance

    def find_track(bbox, focus):
        index = -1
        if point_move:
            # set dif of last
            last = point_move[len(point_move) - 1][len(point_move[len(point_move) - 1]) - 1]
            distance_min = find_distance(last, bbox)
            index = len(point_move) - 1
            for i in range(len(point_move) - 1):
                rec = point_move[i][len(point_move[i]) - 1]
                distance = find_distance(rec, bbox)
                if distance < distance_min:
                    index = i
                    distance_min = distance
            rec = point_move[index][len(point_move[index]) - 1]
            pdistance = find_distance(focus, bbox)

            distance_max = int(0.003 * pdistance ** (2))
            if rec[2] * rec[3] > bbox[2] * bbox[3]:
                max = ((pow(rec[2], 2) + pow(rec[3], 2)) ** (1 / 2)) / 2
            else:
                max = ((pow(bbox[2], 2) + pow(bbox[3], 2)) ** (1 / 2)) / 2
            if distance_min >= distance_max + max:
                index = -1
        return index

    def track_move(rec, pfocus):
        nonlocal point_move, first_track, status_move
        # find track
        index_track = find_track(rec, pfocus)
        p1, p2 = define_point12(rec)
        # set new track
        if index_track == -1:
            index_track = len(first_track)
            first_track.append(rec)
            point_move.append([])
            point_move[index_track].append(rec)
            status_move.append(30)
        else:
            point_move[index_track].append(rec)
            status_move[index_track] = 30
        auto_pop(point_move[index_track], 2)
        return index_track

    def pop_index(first_track, point_move, status_move, i):
        first_track.pop(i)
        point_move.pop(i)
        status_move.pop(i)

    def check_mark(frame, frame_size, size_long, offset_y, offset_x):
        # load the Frame
        # frameSize1 = (600, 450)
        area_frame = frame_size[0] * frame_size[1]

        # define the list of boundaries
        boundary = ([40, 150, 30], [80, 210, 160])

        marks = []
        (lower, upper) = boundary
        # create NumPy arrays from the boundaries
        lower = np.array(lower, dtype="uint8")
        upper = np.array(upper, dtype="uint8")

        # find the colors within the specified boundaries and apply
        # the mask
        image_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(image_hsv, lower, upper)
        output = cv2.bitwise_and(frame, frame, mask=mask)
        # Dilate image and find all the contours
        cnts = cv2.findContours(
            mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
        for cnt in cnts:
            Area = cv2.contourArea(cnt)
            if Area < area_frame * 0.00037 or Area > area_frame * 0.00074:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)
            if w > h * 1.3:
                marks.append(set_center((x, y, w, h)))
        if len(marks) >= 2:
            if marks[1][0] < marks[0][0]:
                tmp = marks[0]
                marks[0] = marks[1]
                marks[1] = tmp
            size_long = int(abs(marks[0][0] - marks[1][0]) / 2)
            offset_y = int(frame_size[1] - (marks[0][1] + marks[1][1]) / 2)
            offset_x = int(frame_size[0] / 2 - (marks[0][0] + size_long))
            # break
        return size_long, offset_y, offset_x

    # Global variables
    # initialize the frame dimensions (we'll set them as soon as we read
    # the first frame from the video)
    w = None
    h = None
    frame_size = (600, 800)
    area_frame = None
    min_contour_area = None
    max_contour_area = None

    # line's position
    offset_y = 0
    offset_x = 0
    size_long = 0
    padding = 0
    margin = 0

    def set_initial_variable(new_w, new_h):
        nonlocal w, h, frame_size, area_frame, min_contour_area, max_contour_area, \
            offset_x, offset_y, size_long, padding, margin
        # Set initial frame size.
        w = new_w
        h = new_h
        frame_size = (w, h)
        area_frame = frame_size[0] * frame_size[1]

        # minimum size 0.01%/maximum size 0.1%
        min_contour_area = area_frame * 0.05
        max_contour_area = area_frame * 0.5

        # line's position
        offset_y = int(frame_size[1] * 0.6)
        # OffsetY = 0
        offset_x = -30
        size_long = int(frame_size[0] * 0.4)
        # padding = frame_size[1] * 0.02
        margin = frame_size[1] * 0.03

    # tracking variable
    point_move = []
    first_track = []
    status_move = []

    # define counting number of people
    people_count = 0

    idle_time = 0

    # object for BackgroundSubtractor
    fgbg = cv2.createBackgroundSubtractorMOG2(history=2000, varThreshold=100, detectShadows=False)

    # Initialize mutithreading the video stream.
    if video is None:
        camera = VideoStream(src=0, usePiCamera=True, resolution=frame_size, framerate=32).start()
    else:
        camera = cv2.VideoCapture(video)

    # initialize the video writer (we'll instantiate later if need be)
    writer = None

    # Debug variables
    fgmask_original = None

    time.sleep(2.0)

    # Get the next frame.
    while True:
        # If using a webcam instead of the Pi Camera,
        if video is None:
            frame = camera.read()
        # If using a video file
        else:
            _, frame = camera.read()
            # cannot fetch Frame
            if frame is None:
                break
            frame = imutils.resize(frame, width=500)

        # cannot fetch Frame
        if frame is None:
            break

        # if the frame dimensions are empty, set them
        if w is None or h is None:
            (h, w) = frame.shape[:2]
            set_initial_variable(w, h)

        # if we are supposed to be writing a video to disk, initialize the writer
        if output is not None and writer is None:
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(output, fourcc, 30, (w, h), True)

        # gray-scale conversion and Gaussian blur filter applying
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret, gray = cv2.threshold(gray, 40, 100, cv2.THRESH_BINARY)
        if idle_time < 2:
            idle_time += 1
            continue
            # OffsetY += 15
        fgmask = fgbg.apply(gray)

        if debug:
            fgmask_original = fgmask.copy()

        fgmask = cv2.erode(fgmask, None, 20)

        cnts = cv2.findContours(
            fgmask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

        # plot reference lines (entrance and exit lines)
        center_line = (int(frame_size[0] / 2 - offset_x), int(frame_size[1] - offset_y))
        coor_exit_line1 = (center_line[0] - size_long, center_line[1])
        coor_exit_line2 = (center_line[0] + size_long, center_line[1])
        cv2.line(frame, coor_exit_line1, coor_exit_line2, (0, 0, 255), 2)
        line = (coor_exit_line1[0], coor_exit_line1[1], coor_exit_line2[0] -
                coor_exit_line1[0], coor_exit_line2[1] - coor_exit_line2[1])

        # check all found countours
        for c in cnts:
            area = cv2.contourArea(c)
            rec = cv2.boundingRect(c)
            p1, p2 = define_point12(rec)
            cv2.rectangle(frame, p1, p2, (0, 255, 200), 2)
            if area > max_contour_area:
                continue
            elif area < min_contour_area:
                break

            # find object's centroid
            object_centroid = set_center(rec)
            index_track = track_move(rec, line)

            (x, y, w, h) = first_track[index_track]
            color_b = 0
            color_r = 0
            first_center = set_center(first_track[index_track])

            if check_line_crossing(first_center, coor_exit_line1, coor_exit_line2):
                color_r = 255
            else:
                color_b = 255

            cv2.rectangle(frame, p1, p2, (color_b, int(
                (index_track + 1) * 70), color_r), 2)

            if abs(first_center[1] - coor_exit_line1[1]) > margin and abs(
                    object_centroid[1] - coor_exit_line1[1]) > margin:
                if not check_line_crossing(first_center, coor_exit_line1, coor_exit_line2) and check_line_crossing(
                        object_centroid,
                        coor_exit_line1,
                        coor_exit_line2):
                    first_track[index_track] = rec

                    people_diff = 1

                elif not check_line_crossing(object_centroid, coor_exit_line1, coor_exit_line2) and check_line_crossing(
                        first_center,
                        coor_exit_line1,
                        coor_exit_line2):
                    first_track[index_track] = rec

                    people_diff = -1

                else:
                    people_diff = 0

                if people_diff != 0:
                    # call on_people_count callback
                    if on_people_count is not None:
                        new_people_count = on_people_count(people_diff)
                        if new_people_count is not None:
                            people_count = new_people_count
                        else:
                            people_count += people_diff
                    else:
                        people_count += people_diff

        for i in range(len(status_move)):
            if status_move[i] <= 0:
                pop_index(first_track, point_move, status_move, i)
                break

        # Write entrance and exit counter values on frame and shows it
        cv2.putText(frame, "count: {}".format(str(people_count)), (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (250, 0, 1), 2)

        # check to see if we should write the frame to disk
        if writer is not None:
            writer.write(frame)

        if debug:
            cv2.imshow("Grey", gray)
            cv2.moveWindow('Grey', 719, 605)
            if fgmask_original is not None:
                cv2.imshow("Mask Original", fgmask_original)
                cv2.moveWindow('Mask Original', 719, 0)
            cv2.imshow("Mask", fgmask)
            cv2.moveWindow('Mask', 719, 315)

            cv2.imshow("Original Frame", frame)
            cv2.moveWindow('Original Frame', 0, 0)

            # Don't wait for key
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

            # Wait for key
            k = cv2.waitKey(0) & 0xff
            if k == ord('q'):
                break

        for i in range(len(status_move)):
            status_move[i] -= 1
        idle_time += 1

    # cleanup the camera and close any open windows
    camera.release()
    cv2.destroyAllWindows()
