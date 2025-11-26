# Download and Run

This document describes how to download and run the logdog executable file.

## 1. Download the Executable File

Navigate to the [release](https://github.com/MaaGF1/logdog/releases) page to find the [latest](https://github.com/MaaGF1/logdog/releases) version . In the `Assets` section, select and download `logdog-platform-arch-version.zip`, where:

1. `platform` supports `linux` and `windows`;
2. `arch` supports `amd64 (x86-64, x64)`;
3. `version` is the version number.

## 2. Extract

1. Place `logdog-*.zip` into the MaaGF1 folder, in the form: `/MaaGF1-GUI-*/logdog-*.zip`
2. Choose "Extract All to **current folder**" (not to a subfolder named `logdog-*`). After extraction, the `.exe` file should be organized as follows:

```sh
# MaaGF1 directory / logdog directory / logdog.exe
/MaaGF1-GUI-v1.7.4-x86_64-/logdog-win-x86_64/logdog.exe
```

## 3. Launch the Program

Before launching the program, you should first start MaaGF1's main program, i.e., `MFAAvalonia`, and ensure the corresponding `/debug/maa.log` file is generated (refreshed). After that, you can start logdog.

Taking the Windows platform as an example, you can either double-click the executable directly or execute it using the following command:

```sh
./logdog.exe
```

After startup, you will see the following output:

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

In this output, the logs before `Dandelion` show the information for loading `watchdog.conf`; the logs after `Dandelion` show the program's own initialization information.

## 4. Custom Configuration

The `watchdog.conf` file in the release version is located in the `_internal` subfolder. Other configuration information and rule writing methods are consistent with the description in the `README`.

## 5. FAQ

1. Why does the program close immediately after opening?
    - Ensure the relative path follows the format described in [Extract](#2-extract).