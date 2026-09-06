# 机器人软件工程师（综合）学习路径

> 基于本项目的完整软件链路，从零到掌握 ROS2 机器人系统开发。

## 阶段一：环境搭建与系统感知（1-2 天）

### 目标
跑通整个系统，建立"机器人系统长什么样"的整体认知。

### 学习内容

1. **环境准备**
   ```bash
   # 方案A：本机安装 ROS2 Jazzy（Ubuntu 24.04）
   source /opt/ros/jazzy/setup.bash
   rosdep install --from-paths src --ignore-src -r -y
   colcon build --symlink-install
   source install/setup.bash

   # 方案B：Docker 复现环境
   docker build -t robot-amr -f docker/Dockerfile .
   docker run -it --rm robot-amr bash
   ```

2. **跑通一键自动仿真**（重点！这是理解全系统的捷径）
   ```bash
   ros2 launch robot_bringup amr_demo.launch.py gui:=true use_rviz:=true
   ```

   - 观察 Gazebo 中机器人如何移动
   - 观察 RViz 中的 TF 树、路径、激光数据
   - 观察终端日志中自动演示如何下发任务

3. **使用诊断工具观察系统**（养成诊断习惯）
   ```bash
   ros2 node list                    # 看所有节点
   ros2 topic list                   # 看所有话题
   ros2 topic echo /mission_runner/state   # 看任务状态
   ros2 topic echo /chassis/state    # 看底盘状态
   ros2 topic echo /system_health    # 看系统健康
   ros2 service list                 # 看所有服务
   ros2 action list                  # 看所有动作
   ros2 run tf2_tools view_frames    # 生成 TF 树 PDF
   ```

### 核心理解
- **ROS2 三要素**：节点（Node）、话题（Topic）、服务/动作（Service/Action）
- **系统分层**：硬件 → 传感器 → 导航 → 任务调度 → 安全 → 集成
- **命令工具**：`ros2 node/topic/service/action/launch` 系列命令

---

## 阶段二：掌握 ROS2 核心通信模型（2-3 天）

### 目标
学会在 ROS2 中创建节点、定义接口、实现通信。

### 学习内容

1. **消息（msg）**：学习 `src/robot_interfaces/msg/` 下所有消息定义
   ```text
   ChassisState.msg          # 底盘状态
   RobotState.msg            # 机器人状态
   SafetyState.msg           # 安全状态
   LocalizationHealth.msg    # 定位健康度
   PayloadState.msg          # 载物状态
   TrackingError.msg         # 跟踪误差
   ```

2. **服务（srv）**：学习 `src/robot_interfaces_*/srv/` 下的服务定义
   - `SubmitOrder.srv`：统一订单入口
   - `ListStations.srv`：站点查询
   - `RequestCharging.srv`：充电请求

3. **动作（action）**：学习 `src/robot_interfaces/action/NavigateSequence.action`
   ```text
   # 目标：geometry_msgs/PoseStamped[] goals + bool loop
   # 结果：success/message/succeeded_goals/failed_goals
   # 反馈：current_goal_index/total_goals/state/message
   ```

4. **Launch 文件**：精读 `src/robot_bringup/launch/bringup.launch.py`
   - `DeclareLaunchArgument`：参数声明
   - `IncludeLaunchDescription`：launch 嵌套
   - `Node`：节点启动
   - `LaunchConfiguration`：运行时配置

### 实践练习
```bash
# 创建一个简单的发布-订阅节点
# 参考 robot_sensors/src/ 下的 fake_scan_node
ros2 run robot_sensors fake_scan_node
ros2 topic echo /scan
```

---

## 阶段三：沿数据流学习各模块（1 周）

### 目标
理解数据在系统中的流动方式，每个模块的角色。

### 数据流主线

```
Gazebo/真实硬件
    → robot_hardware: 底盘驱动 (CMD/ODOM/STATE 协议)
    → /odom, /chassis/state
    → robot_sensors: 传感器标准化
    → /scan, /imu/data
    → robot_navigation: Nav2 导航 + SLAM + EKF
    → /nav2_cmd_vel
    → robot_path_tracking: Pure Pursuit / Stanley
    → /tracking_cmd_vel
    → robot_teleop: twist_mux + cmd_vel_safety_gate
    → /cmd_vel (唯一发布者)
    → robot_tasks: mission_runner 任务调度
    → /navigate_sequence (action)
    → 完成搬运/充电/过门/电梯等任务
```

### 建议学习顺序（按依赖关系）

| 顺序 | 模块 | 代码入口 | 学习重点 |
|------|------|----------|----------|
| 1 | `robot_hardware` | `src/robot_hardware/src/chassis_packet*` | 协议编解码、Serial/UDP 通信、状态机 |
| 2 | `robot_sensors` | `src/robot_sensors/src/*` | 传感器数据标准化、坐标系 |
| 3 | `robot_navigation` | `src/robot_navigation/config/` | Nav2 参数、costmap、SLAM 配置 |
| 4 | `robot_path_tracking` | `src/robot_path_tracking/src/*` | Pure Pursuit 算法、Stanley 算法 |
| 5 | `robot_teleop` | `src/robot_teleop/src/*` | cmd_vel 仲裁、安全门、急停 |
| 6 | `robot_tasks` | `src/robot_tasks/src/*` | 任务调度、队列、状态机（重点！） |
| 7 | `robot_utils` | `src/robot_utils/src/*` | 系统监控、诊断、故障监督 |

### 每个模块问自己三个问题
1. 这个模块的**输入**是什么？（订阅哪些话题、接收哪些请求）
2. 这个模块的**输出**是什么？（发布哪些话题、提供哪些服务）
3. 这个模块的**状态**如何管理？（内部状态机、生命周期）

---

## 阶段四：深入任务调度中枢 robot_tasks（1 周）

### 目标
这是项目最有分量的部分（46 个源文件），也是综合工程师面试的高频考点。

### 代码地图

```
mission_runner_node.cpp          # 核心入口（5659行），所有服务的注册
├── mission_profile.cpp          # 任务配置文件解析
├── mission_profile_builders.cpp # 从订单构建任务配置
├── mission_queue.cpp            # 任务队列管理
├── mission_estimator.cpp        # 成本/ETA/电量估算
├── mission_preflight.cpp        # 任务前校验（电量/地图/路线）
├── mission_recovery_policy.cpp  # 失败恢复策略
├── submit_order_router.cpp      # 统一订单路由
├── station_catalog.cpp          # 站点目录
├── station_transport_workflow.cpp  # 站点搬运工作流
├── station_sequence_workflow.cpp   # 站点序列工作流
├── facility_reservation.cpp     # 设施（门/电梯/充电）预约
├── facility_workflow.cpp        # 设施联动工作流
├── docking_workflow.cpp         # 对接充电工作流
├── fulfillment_workflow.cpp     # 订单履约工作流
├── fleet_runtime_state.cpp      # 车队状态管理
├── traffic_reservation.cpp      # 路线资源锁/防死锁
├── workflow_control.cpp         # 工作流暂停/恢复/取消
└── operator_snapshot.cpp        # 运营快照
```

### 核心设计模式

1. **Behavior Tree 模式**（强烈建议学习！）
   ```text
   mission_queue_behavior_tree     # 排队决策
   mission_recovery_behavior_tree  # 失败恢复决策
   mission_result_behavior_tree    # 结果处理决策
   mission_runtime_behavior_tree   # 运行时决策
   submit_order_behavior_tree      # 订单路由决策
   ```
   模式：输入结构体 → 行为树逻辑 → 决策结构体 → 节点执行副作用

2. **状态机模式**
   ```text
   READY → RUNNING → PAUSED → RUNNING → 完成 → (回桩/下个任务)
     ↓        ↓
   ERROR ← CANCELING
   ```

3. **门控（Gate）模式**
   每个订单提交都经过多层校验：
   - 重复检查（duplicate gate）
   - 前置校验（preflight gate）
   - 路由校验（route gate）

### 重点精读顺序

1. **`mission_runner_node.cpp` 构造函数**：看懂所有服务的注册方式
2. **`SubmitOrder()` 方法**：看懂统一订单如何路由到不同类型
3. **`DispatchMission()` 方法**：看懂任务如何发给 navigate_sequence action
4. **`HandleMissionFailure()` 方法**：看懂失败恢复策略
5. **`Tick()` 方法**：看懂周期运行的调度逻辑

---

## 阶段五：掌握测试与验收体系（2-3 天）

### 目标
学会如何测试和验收一个机器人系统。

### 学习内容

1. **单元测试（GoogleTest）**
   ```bash
   colcon test --packages-select robot_tasks --event-handlers console_direct+
   ```
   查看 `src/robot_tasks/test/` 下的测试用例

2. **验收脚本体系**
   ```bash
   scripts/check_robot.sh                    # 查看可用 suite
   scripts/check_robot.sh mission queue      # 任务队列验收
   scripts/check_robot.sh facility charging  # 设施/充电验收
   ```
   学习脚本如何验证系统行为：
   ```bash
   # 例如 check_fault_supervisor.sh 的验证模式：
   # 1. 启动系统
   # 2. 触发故障条件
   # 3. 验证安全响应
   # 4. 恢复并验证
   ```

3. **集成测试（launch_testing）**
   - 查看 `src/robot_bringup/test/test_mock_bringup.launch.py`

---

## 阶段六：动手实战项目（持续进行）

### 项目 1：添加一个新服务
在 `mission_runner_node` 中添加一个 `/v2/hello` 服务：
1. 在 `robot_interfaces_mission/srv/` 定义新服务接口
2. 在 `CMakeLists.txt` 注册
3. 在 `mission_runner_node.cpp` 中创建服务
4. 通过 `ros2 service call` 测试

### 项目 2：实现一个新的工作流
仿照 `station_transport_workflow.cpp`，实现一个"快递取送"工作流：
1. 定义订单类型和路由
2. 实现工作流逻辑
3. 编写验收脚本

### 项目 3：修改调度策略
修改 `mission_queue.cpp` 中的排序逻辑，实现自定义优先级策略：
1. 理解现有排序算法
2. 添加新策略（如按距离+电量加权）
3. 编写单元测试验证

### 项目 4：理解并扩展安全机制
在 `robot_teleop` 中添加新的安全规则：
1. 学习 `cmd_vel_safety_gate` 的实现
2. 添加新的安全条件（如区域限速）
3. 编写验收脚本

---

## 知识体系对照表

| 面试/考核点 | 对应模块 | 深入学习建议 |
|------------|---------|-------------|
| ROS2 通信 | `robot_interfaces*` + 各节点 | 动手写一个 pub/sub 和 service 节点 |
| C++17 现代语法 | 所有 `src/` | 重点：智能指针、std::optional、lambda、模板 |
| 状态机设计 | `robot_tasks/src/*_workflow` | 画出每个 workflow 的状态转换图 |
| 多线程与并发 | `mission_runner_node.cpp` | 理解 mutex、线程安全、async_send_request |
| 设计模式 | `robot_tasks/src/*_behavior_tree` | 行为树、策略模式、观察者模式 |
| 系统集成 | `robot_bringup/launch/` | 理解 launch 嵌套、参数传递 |
| 调试技巧 | 各模块 | rqt_graph、rqt_console、gdb、ros2 doctor |
| 测试体系 | `scripts/` + `test/` | 了解三种测试层级（单元/集成/验收） |

---

## 常见面试题（基于本项目）

1. **ROS2 的 Topic/Service/Action 有什么区别？什么时候用哪个？**
   - 回答：Topic 用于持续数据传输（如 /scan、/odom）；Service 用于一次性请求响应（如 /v2/submit_order）；Action 用于长时间任务（如 /navigate_sequence），支持反馈和取消。

2. **本项目的 /cmd_vel 为什么只能由 safety gate 发布？**
   - 回答：安全设计原则。所有速度指令经过 twist_mux 仲裁后，由 safety gate 统一把关（急停/限速/接管），保证任何上层模块都不能绕过安全控制。

3. **如何设计一个任务调度系统？**
   - 回答：队列 + 优先级 + 状态机 + 恢复策略 + 资源管理。参考 `robot_tasks` 的实现。

4. **机器人系统如何保证安全？**
   - 回答：多层次防御：硬件急停 → safety gate（/cmd_vel 把关）→ system_monitor（健康监控）→ fault_supervisor（故障闭环）→ 任务层（暂停/回桩/恢复）。

5. **什么是行为树？为什么用它来管理任务流程？**
   - 回答：比传统状态机更灵活、可组合、可复用。本项目的任务决策逻辑都用行为树实现，将复杂决策拆分为可测试的小步骤。

---

## 学习资源推荐

1. **ROS2 官方文档**：https://docs.ros.org/en/jazzy/
2. **Nav2 文档**：https://docs.nav2.org/
3. **C++ 现代教程**：https://learncpp.com/
4. **行为树教程**：https://www.behaviortree.dev/
5. **本项目 README**：按"按岗位分模块学习"表格逐项对照学习

---

## 最终目标

完成以上学习后，你应该能够：
1. 独立动手对这个系统进行功能扩展
2. 理解每个模块的输入/输出/状态管理
3. 能够定位和修复系统中的问题
4. 能够讲解系统的架构设计原理
5. 面试时能结合项目实例回答各类 ROS2 问题