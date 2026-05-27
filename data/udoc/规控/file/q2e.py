import rospy
import numpy as np
import tf
from tf.transformations import *
from geometry_msgs.msg import PoseStamped

x_sum=0
y_sum=0
yaw_sum=0
count=0

def callback(data):
    x = data.pose.position.x
    y = data.pose.position.y
    z = data.pose.position.z
    t = data.header.stamp
    (roll,pitch,yaw) = euler_from_quaternion([data.pose.orientation.x,data.pose.orientation.y,data.pose.orientation.z,data.pose.orientation.w])
    yaw = yaw * 180 / 3.1415926
    if yaw < 0:
        yaw += 360
    roll = roll * 180 / 3.1415926
    pitch = pitch * 180 / 3.1415926
    #rospy.loginfo("Position - distance: %f, offset: %f, yaw: %f",x,y,yaw)
    global x_sum
    global y_sum
    global yaw_sum
    global count
    x_sum +=x
    y_sum +=y
    yaw_sum +=yaw
    count +=1
    if count / 20:
        rospy.loginfo("side docking param | distance_check: %f, offset_check: %f, angleRobotdiff_check: %f", -1000 * x_sum/count, -1000 * y_sum/count, yaw_sum/count)
        x_sum=0
        y_sum=0
        yaw_sum=0
        count=0    
rospy.init_node("side_dock_calibrating",anonymous=True)
rospy.Subscriber("/pose_in_tag",PoseStamped ,callback)
sleep(6)
#rospy.spin()
