# Jailhouse-gui usage instructions

## introduce

Jailhouse gui is a graphical user interface (GUI) tool used to configure and manage Jailhouse. Jailhouse is a Linux based management program that divides multi-core processors into independent units for real-time critical applications.

## software architecture

Jailhouse gui is a graphical interface program developed and implemented in Python language. The entire software is divided into two parts: one is the core module that focuses on business and data processing, and the other is the GUI module that focuses on interaction and display. The functional module architecture of the entire software is shown in the following figure.
![1695286662657](image/README/1695286662657.png)


## Deploy jailhouse virtualization environment

### Compile Jailhouse-gui

Jailhouse gui supports running on both Windows and Linux platforms. Below, we will introduce the compilation methods for each platform one by one.

#### Compilation and packaging under Linux platform

1. Download the source code of Jailhouse gui

```
git clone  https://gitee.com/openeuler/Jailhouse-gui.git
```

2. Install the dependencies required for Jalhouse gui, which can be found in the requirements list. txt file.

If openEuler does not have the pip tool, it needs to be installed by oneself. If the user's openEuler has already installed pip, follow the steps below to continue.

```
cd Jailhouse-gui
pip install -r requirements_linux.txt -i  https://pypi.tuna.tsinghua.edu.cn/simple
sudo apt install libxcb-xinerama0
```

3. Package Jalhouse gui

```
python ./build.py deploy
```

4. Launch Jalhouse gui

```
cd Jailhouse-gui/dist
./resource-tool-nonversion
```
#### Compilation and packaging under Windows platform

1. Download the source code of Jailhouse gui.

```
git clone  https://gitee.com/openeuler/Jailhouse-gui.git
```

2. Install the dependencies required for Jalhouse gui, which can be found in the requirements _ in. txt file.

```
cd Jailhouse-gui
pip install -r requirements_win.txt -i  https://pypi.tuna.tsinghua.edu.cn/simple
```

3. Package Jailhouse gui.

```
python ./build.py deploy
```

4. Start Jalhouse gui.
Double click the resource tool executable file in the dist directory.

### Using Jaillhouse-gui
In order to facilitate users to quickly deploy jailhouse virtualization environments using the jailhouse gui tool, we provide complete configuration files, root cell and guest cell configuration files, and their related image files. Users can directly use the jailhouse gui tool.

The list of documents provided is as follows:

|Name | Introduction | Path|
| :--------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
|D2000_rtt.jhr | provides a complete set of configuration entries for root cells and guest cells, which can be opened directly using the Jailhouse gui tool. Typically, users do not need to modify this configuration file| Jailhouse-gui/examlpes |
|Rtthread_o64.bin | The guest cell runs RTOS, and rtthread_o64.bin is the guest cell image provided by us. It can be deployed directly with one click using Jailhouse gui. We need to connect the serial port 1 used by the guest cell in advance| Jailhouse-gui/examlpes |

Jailhouse gui needs to be used in conjunction with the rpc_server service on the target machine, and there should be a limit on the memory that the target machine's kernel can use. For example, this can be achieved by adding "mem=3GB" in the system startup parameters (the specific limit needs to be adjusted according to the actual size of the target machine's memory). Secondly, it is necessary to start the rpc_server service on the target machine.

#### Deploy rpc_server service (openEuler edge/server version)

1. Copy the rpc_server folder to the target machine.
2. The dependencies required for installing rpc_server.

```
yum install -y python3-devel python3-mako
cd rpc_server
pip3 install -r requirements_rpc.txt -i  https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install psutil==5.9.4 -i  https://pypi.tuna.tsinghua.edu.cn/simple
```
3. Point the soft link in rpc_server/jailhouse_bin to the correct jailhouse file.
4. Start rpc_server to allow it to run in the background.

```
python3 server_host.py &
```
