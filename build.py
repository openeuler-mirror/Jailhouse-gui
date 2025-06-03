import os.path
from glob import glob
import datetime

"""
资源工具构建脚本模块

该模块包含用于构建UI界面、资源文件、生成版本信息以及应用部署的工具函数。
主要功能包括：
- 自动编译UI文件(.ui)为Python代码
- 编译资源文件(.qrc)为二进制资源模块
- 生成包含版本号和构建时间的版本信息文件
- 应用程序打包部署（通过PyInstaller）
"""

# 工具路径配置
uic = "pyside2-uic" # UI编译器路径
rcc = "pyside2-rcc" # 资源编译器路径


def build_uic():
    """
    编译UI文件(.ui)为Python代码
    
    遍历forms目录下的所有UI文件，检查是否需要重新编译：
    - 若目标文件不存在或UI文件更新时间晚于目标文件，则执行编译
    - 使用pyside2-uic工具生成对应的ui_*.py文件
    
    Returns:
        int: 成功编译的文件数量
    """
    ui_files = glob("forms/*.ui")   # 获取所有UI文件路径
    count = 0
    for file in ui_files:
        path = os.path.dirname(file)
        name = os.path.splitext(os.path.basename(file))[0]  # 提取文件名（不带扩展名）
        output = os.path.join(path, f"ui_{name}.py")    # 生成目标文件路径

        # 检查是否需要重新编译
        if not os.path.exists(output) or os.path.getmtime(file) > os.path.getmtime(output):
            cmd = f'{uic} -o {output} {file}'   # 构建编译命令
            print(cmd)
            os.system(cmd)  # 执行编译命令
            count = count + 1
    return count


def build_rcc():
    """
    编译资源文件(.qrc)为二进制资源模块
    
    递归查找assets目录下的所有.qrc文件，检查资源是否发生变化：
    - 若资源文件或其引用的文件更新，则重新编译
    - 使用pyside2-rcc工具生成对应的qr_*.py文件
    
    Returns:
        int: 1表示有资源更新并重新编译，0表示无需更新
    """
    qrc_files = glob("assets/*.qrc", recursive=True)     # 获取所有资源文件路径
    update = False  # 是否需要更新标志

    # 检查是否有资源文件需要更新
    for qrc in qrc_files:
        path = os.path.dirname(qrc)
        name = os.path.splitext(os.path.basename(qrc))[0]
        qrc_output = os.path.join(path, f"qr_{name}.py")
        # 若目标文件不存在，则需要更新
        if not os.path.exists(qrc_output):
            update = True
            break

        # 检查资源文件引用的所有文件是否有更新
        for file in glob("assets/**", recursive=True):
            if '__pycache__' in file:   # 跳过缓存目录
                continue
            if os.path.getmtime(file) > os.path.getmtime(qrc_output):
                update = True
                break
        if update:
                break

    if not update:
        return 0    # 无需更新

    # 执行资源文件编译
    for file in qrc_files:
        path = os.path.dirname(file)
        name = os.path.splitext(os.path.basename(file))[0]
        output = os.path.join(path, f"qr_{name}.py")

        cmd = f'{rcc} -o {output} {file}'
        os.system(cmd)

    return 1


def get_version():
    """
    获取当前版本号
    
    通过Git命令获取最新标签作为版本号，若获取失败则返回"unknown"
    
    Returns:
        str: 版本号（格式：vX.Y.Z 或 unknown）
    """
    version = os.popen("git describe --tags --dirty=-dev").read()
    if len(version) == 0:
        version = "unknown"
    return version.strip()


def gen_version():
    """
    生成版本信息文件(version.py)
    
    文件内容包含：
    - VERSION: 从Git获取的版本号
    - BUILD_TIME: 当前构建时间（datetime字符串）
    """
    version = get_version()

    now = datetime.datetime.now()
    # 写入版本信息文件（自动生成，禁止手动修改）
    with open("version.py", "wt") as f:
        f.write('# Generated, DO NOT MODIFY.\n\n')
        f.write(f"VERSION = '{version}'\n")
        f.write(f"BUILD_TIME = '{now}'\n")


def build_and_exit():
    """
    构建资源并退出（用于预构建检查）
    
    执行以下操作：
    1. 生成版本信息
    2. 编译UI和资源文件
    3. 若有文件更新，提示重新构建并退出
    """
    gen_version()
    count = sum((0,
                 build_uic(),
                 build_rcc(),
                 ))
    if count > 0:
        print("Build file changed, try again.")
        exit()

def build():
    """
    执行资源构建（UI/资源文件编译 + 版本生成）
    
    Returns:
        int: 总变更文件数
    """
    gen_version()
    count = sum((0,
                 build_uic(),
                 build_rcc(),
                 ))
    print("build:", count)
    return count


def deploy():
    """
    应用程序打包部署
    
    流程：
    1. 使用PyInstaller根据.spec文件打包应用
    2. 将生成的无版本号可执行文件重命名为带版本号的文件
    3. 清理旧文件并输出部署结果
    
    Returns:
        str: 部署后的可执行文件路径（失败时返回None）
    """
    version = get_version()

    exe = f'resource-tool-{version}.exe'    # 带版本号的目标文件名
    cmd = 'pyinstaller resource-tool.spec'
    # 执行PyInstaller打包
    if os.system(cmd) != 0:
        print("pyinstaller failed.")
        return None

    # 重命名可执行文件（从非版本号名称改为带版本号名称）
    name_from = os.path.join("dist", "resource-tool-nonversion.exe")
    name_to   = os.path.join("dist", exe)
    if os.path.exists(name_to):
        os.remove(name_to)  # 删除旧版本文件
    os.rename(name_from, name_to)   # 重命名文件

    print("deploy finished", exe)
    return exe


def main():
    """
    主入口函数
    
    支持命令行参数：
    - 无参数：执行预构建（编译UI/资源 + 生成版本号）
    - deploy: 执行完整部署（预构建 + 打包发布）
    """
    import sys
    if len(sys.argv) == 1:
        print("pre build.")
        build_uic()
        build_rcc()
        gen_version()
        print("pre build done.")
        return 0

    if sys.argv[1] == 'deploy':
        build_uic()
        build_rcc()
        gen_version()
        print("deploy.")
        exe = deploy()
        print(f"deploy done {exe}.")


if __name__ == '__main__':
    main()
