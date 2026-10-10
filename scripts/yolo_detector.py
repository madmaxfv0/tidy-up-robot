#!/usr/bin/env python3
# coding=utf-8
import rospy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import os
import cv2
import rospkg
from yolov4 import Detector


class YOLODetectorNode:
    def __init__(self):
        self.detector = Detector(gpu_id=0,
            config_path='/opt/darknet/cfg/yolov4.cfg',
            weights_path='/opt/darknet/yolov4.weights',
            lib_darknet_path='/opt/darknet/libdarknet.so',
            meta_path=os.path.join(rospkg.RosPack().get_path('second_coursework'),
                                   'cfg', 'coco.data'))
        self.bridge = CvBridge()
        self.cv_image = None
        self.new_image = False
        self.frame_count = 0
        self.skip = 10
        rospy.Subscriber('/camera/image', Image, self.img_callback)
        self.det_pub = rospy.Publisher('/yolo_detections', String, queue_size=5)

    def img_callback(self, msg):
        self.frame_count += 1
        if self.frame_count % self.skip == 0:
            self.cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
            self.new_image = True

    def main_loop(self):
        rate = rospy.Rate(5)
        while not rospy.is_shutdown():
            if self.new_image and self.cv_image is not None:
                self.new_image = False
                cv_copy = self.cv_image.copy()
                img_arr = cv2.resize(cv_copy,
                    (self.detector.network_width(), self.detector.network_height()))
                detections = self.detector.perform_detect(
                    image_path_or_buf=img_arr, show_image=True)
                for detection in detections:
                    if detection.class_confidence > 0.5:
                        rospy.loginfo("Detected: %s (%.1f%%)",
                            detection.class_name, detection.class_confidence * 100)
                        self.det_pub.publish(detection.class_name)
            rate.sleep()


if __name__ == '__main__':
    rospy.init_node('yolo_detector')
    node = YOLODetectorNode()
    node.main_loop()
