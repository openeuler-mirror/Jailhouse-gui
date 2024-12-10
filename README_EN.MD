# Jailhouse-gui usage instructions

## introduce

Jailhouse gui is a graphical user interface (GUI) tool used to configure and manage Jailhouse. Jailhouse is a Linux based management program that divides multi-core processors into independent units for real-time critical applications.

## software architecture

Jailhouse gui is a graphical interface program developed and implemented in Python language. The entire software is divided into two parts: one is the core module that focuses on business and data processing, and the other is the GUI module that focuses on interaction and display. The functional module architecture of the entire software is shown in the following figure.
![1695286662657](image/README/1695286662657.png)


## Deploy jailhouse virtualization environment

### Compile Jailhouse-gui

Jailhouse gui supports running on both Windows and Linux platforms. Below, we will introduce the compilation methods for each platform one by one.
