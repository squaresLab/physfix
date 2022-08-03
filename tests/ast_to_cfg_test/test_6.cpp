//  ///////////////////////////////////////////////////////////
//
// turtlebot_example_node.cpp
// This file contains example code for use with ME 597 lab 1
// It outlines the basic setup of a ros node and the various 
// inputs and outputs.
// 
// Author: James Servos. 2012 
//
// //////////////////////////////////////////////////////////

#include <ros/ros.h>
#include <geometry_msgs/PoseWithCovarianceStamped.h>
#include <geometry_msgs/Twist.h>
#include <tf/transform_datatypes.h>

void goal_d(double x_t,double y_t, double t)
{
	int err_y = err_x + ang_z;

    if (vel_x < 0) {
        vel_x = ang_z + err_x;

        if (ang_z < 0) {
            vel_x = 10;
        } else {
            vel_x = -10
        }

    } else if (vel_x > 0) {
        vel_x = vel_x + err_y;
    } else {
        ang_z = 10;

        if (err_x < 0) {
            vel_x = 50;
        } else {
            vel_x = -50
        }
    }
}
