# 下载并运行

本篇文档用于描述如何下载 logdog 的可执行文件并允许。

## 一、下载可执行文件

在[release](https://github.com/MaaGF1/logdog/releases)页面找到最新正式版([latest](https://github.com/MaaGF1/logdog/releases))页面，在`Assets`一栏中选择`logdog-platform-arch-verion.zip`并下载，其中：

1. `platform`支持`linux`和`windows`；
2. `arch`支持`amd64(x86-64、x64)`；
3. `version`为版本号。

## 二、解压缩

1. 将`logdog-*.zip`放入 MaaGF1 的文件夹中，形如：`/MaaGF1-GUI-*/logdog-*.zip`
2. 选择“全部解压到**当前文件夹**”(而不是解压到`logdog-*`的子文件中)，解压后的`.exe`应该按照如下形式存放：

```sh
# MaaGF1目录 / logdog目录 / logdog.exe
/MaaGF1-GUI-v1.7.4-x86_64-/logdog-win-x86_64/logdog.exe
```

## 三、启动程序

在启动程序之前，应当首先启动 MaaGF1 的主程序，即`MFAAvalonia`，并确保生成(刷新)对应的`/debug/maa.log`文件。之后可以启动 logdog。

以 Windows 平台为例，可以直接双击可执行程序，也可以使用如下的风格执行：

```sh
./logdog.exe
```

在启动后，会有如下的打印：

```log
Initializing MaaFramework Watchdog...
Config file: C:\Users\14021\Downloads\MaaGF1-GUI-v1.7.4-x86_64-\logdog-win-x86_64\_internal\watchdog.conf
Loaded 6 state machine rules
Loaded 3 entry nodes
Loaded 3 completion nodes
Notification filter enabled: Timeout
Warning: No notification platforms configured
Watchdog service initialized successfully
Starting MaaFramework Watchdog Service...
Press Ctrl+C to stop
Use --status for basic status, --detailed-status for full details

              .=====================.
             /|                     |\
            | |  Dandelion Service  | |
            | |                     | |
            |  \___________________/  |
             \_______________________/
                     \      /
                      \    /
                 .-----`--'-----.
                / .------------. \
               / /    .----.    \ \
              | |    /  ()  \    | |
              | |   |   __   |   | |
               \ \   \      /   / /
                \ '------------' /
                 \              /
                 /`.__________.'\
                /   /        \   \
               ^   ^          ^   ^

Starting watchdog service...
Monitoring log file: ../debug/maa.log
Starting Watchdog monitor loop...
Watchdog log monitor started
Watchdog service started successfully
Monitoring started at: 2025-11-26 09:05:58
Status: {'running': True, 'total_state_rules': 6, 'total_entry_nodes': 3, 'total_completion_nodes': 3, 'active_state_rules': 0, 'active_state_rule_names': [], 'log_source': '../debug/maa.log', 'notification_available': False}
```

其中，在`Dandelion`之前的日志，为加载`watchdog.conf`的信息；在`Dandelion`之后的日志，为程序本身的初始化信息。

## 四、自定义Conf

发行版的`watchdog.conf`文件在`_internal`这个子文件夹中，其余配置信息、规则编写方式与`README`中的说明一致。

## 五、FAQ

1. 为什么程序打开就闪退？
    - 确保其相对路径是[解压缩](#二解压缩)中的形式。