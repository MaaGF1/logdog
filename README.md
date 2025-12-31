[![English](https://img.shields.io/badge/English-README-blue)](docs/README.en.md)   [![Run](https://img.shields.io/badge/下载并运行-8CA1AF?logo=readthedocs&logoColor=fff)](docs/01_begin.md)

# MaaFramework Watchdog

一个为 MaaFramework 设计的基于日志的监控系统。

Logdog 通过实时分析日志文件来监控 MaaFramework Pipeline 的执行流程。它利用可配置的图导向状态机来跟踪任务节点切换、检测超时，并在操作未在预期时间内完成时，通过外部通知发送警报。

## 一、功能特性

* 非侵入式监控: 通过 `debug/maa.log` 文件监控代理，无需注入进程内存。
* 图导向状态机: 支持单状态多分支逻辑，自动合并共享起点的规则，例如: `起点 -> 分支A` 或 `起点 -> 分支B`。
* 智能超时检测: 基于当前节点的所有潜在出边，动态计算最短超时阈值。
* 入口节点检测: 当新的任务周期开始(入口节点)时，自动重置当前活动的状态，防止逻辑错乱。
* 多平台通知: 
    * Telegram Bot
    * 企业微信
* 自定义警报: 筛选触发通知的事件类型，例如: 仅在超时发生时报警。
* 自定义Action:
    * 外部通知
    * 自动关机

## 二、使用源码

Python 版本要求3.8及以上。

1.  克隆仓库: 

```bash
git clone git@github.com:MaaGF1/logdog.git
# 或者
git clone https://github.com/MaaGF1/logdog.git
# 进入目录
cd logdog
```

2.  安装依赖: 

唯一的外部依赖是用于发送通知的 `requests` 库: 

```bash
pip install requests
```

3. 构建 C++ 核心:

本项目核心逻辑采用 C++ 实现，需使用 `scons` 进行构建。确保已安装 C++ 编译器和 SCons。

```bash
scons
```

## 三、配置说明

系统完全通过 `watchdog.conf` 文件进行控制。

### 3.1 通知设置

配置外部通知参数，以及设置通知过滤选项。

```ini
[Notification]
# Telegram 配置
Bot_Token=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
Chat_ID=123456789

# 企业微信配置
Webhook_Key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# 默认平台，可用选项: 
    # telegram
    # wechat
Default_ExtNotify=wechat

# 通知过滤，定义哪些事件会触发消息发送，可用选项: 
    # StateActivated (状态激活), 
    # StateCompleted (状态完成), 
    # Timeout (超时), 
    # StateInterrupted (状态中断), 
    # EntryDetected (检测到入口)
# 如果注释掉此行，将发送所有事件。
NotifyWhen={Timeout, StateInterrupted}
```

### 3.2 监控设置

将 Watchdog 指向你的 MaaFramework 日志文件。

```ini
[Monitoring]
# MaaFramework 生成的日志文件路径
Log_File_Path=../debug/maa.log

# 轮询间隔(秒)
Monitor_Interval=1.0
```

### 3.3 状态机规则

#### 状态规则 (`[States]`)
格式: `规则名称={开始节点, 超时毫秒数, 下一节点, [超时毫秒数, 下一节点...], 描述}`

系统会将所有规则解析为一个状态图。如果多条规则以同一个节点开始，它们将被视为该节点的不同分支。

* StartNode (开始节点): 当前所处的节点名称。
* TimeoutMS (超时毫秒数): 允许到达下一节点的时间。**注意：如果一个节点有多个分支，系统将取所有分支中最小的超时时间作为阈值。**
* NextNode (下一节点): 预期的目标节点。

```ini
[States]
# 简单线性规则: StartTask -> (30s) -> EndTask
Simple_Task={StartTask, 30000, EndTask, "基础任务监控"}

# 分支逻辑示例:
# 当处于 'DecisionNode' 时，如果在 10秒内检测到 'BranchA' 则走第一条路；
# 如果检测到 'BranchB' 则走第二条路。
# 如果 10秒内既没有 A 也没有 B，则触发超时。
Flow_Path_A={DecisionNode, 10000, BranchA, "流程分支A"}
Flow_Path_B={DecisionNode, 10000, BranchB, "流程分支B"}
```

#### 入口节点 (`[Entries]`)

标志着主要工作流开始的节点。当检测到此类节点时，状态机将强制重置，并从该节点重新开始跟踪。这用于处理意外重启或手动干预的情况。

```ini
[Entries]
# 格式: 名称={节点名, 描述}
Main_Entry={Task_Start_Node, "主任务入口点"}
```

#### 完成节点 (`[Completed]`)

明确标记流程已成功结束的节点。到达此节点后，状态机将停止计时并重置状态。

```ini
[Completed]
# 格式: 名称={节点名, 描述}
Task_Done={Task_Success_Node, "任务成功完成"}
```

## 四、使用方法

### 4.1 启动 Watchdog

运行主脚本。它将阻塞并无限期地监控日志文件。

```bash
# 确保已运行 scons 构建
python main.py
```

### 4.2 命令行参数

* `--config <path>`: 指定自定义配置文件路径。
* `--status`: 打印状态机的当前配置摘要并退出。

示例:

```bash
python main.py --config ./my_configs/watchdog.conf
```

## 五、How it works

1. **日志解析**: C++ 核心实时读取 `maa.log`，通过正则匹配 `[pipeline_data.name=NodeName] | enter` 等模式提取节点。
2. **状态转移**: 
    * 系统维护一个单一的“当前节点”指针。
    * 当检测到新节点时，系统检查该节点是否为当前节点的有效“下一跳”（基于配置的规则）。
    * 如果匹配成功，系统更新“当前节点”并重置计时器。
3. **超时机制**: 
    * 每当进入一个新节点，系统会计算所有可能的下一跳路径中**最短**的超时时间。
    * 如果在规定时间内没有转移到任何有效的下一节点，触发 `Timeout` 事件。
4. **通知**: Python 层接收 C++ 抛出的事件，根据 `NotifyWhen` 的设置向配置的平台发送警报。