# 🐾 GPU Pet Monitor

> 一只可爱的桌面宠物，实时监控你的 NVIDIA GPU 状态。

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 截图预览

桌面悬浮窗，宠物根据 GPU 状态自动变化表情和颜色：

| 状态 | 外观 | 说明 |
|------|------|------|
| IDLE | 🟦 蓝色 | GPU 空闲，宠物打盹 |
| NORMAL | 🟩 绿色 | 一切正常 |
| WORKING | 🟨 黄色 | 工作中 |
| WARNING | 🟧 橙色 | 温度/使用率偏高 |
| CRITICAL | 🟥 红色 | 危险！弹窗提醒 |

## 功能特性

- **实时监控** — GPU 使用率、显存、温度、功耗、风扇、频率
- **迷你历史曲线** — 最近 60 秒 GPU / 显存 / 温度趋势图
- **8 套内置皮肤** — 猫咪、机器人、狐狸、兔子、恶魔、史莱姆、企鹅、仓鼠
- **智能状态切换** — 宠物根据 GPU 负载自动变换颜色和动作
- **系统托盘** — 最小化到托盘，右键菜单快速操作
- **危险通知** — GPU 温度/使用率过高时弹出系统通知
- **完全可配置** — 采样间隔、阈值、显示项目均可自定义

## 快速开始

### 方式一：直接运行（Windows）

从 [Releases](../../releases) 下载 `GPU-Pet-Monitor.exe`，双击运行即可。

### 方式二：源码运行

```bash
# 安装依赖
pip install PyQt5 nvidia-ml-py

# 运行
python src/main.py
```

## 托盘菜单

| 菜单 | 功能 |
|------|------|
| 显示/隐藏悬浮窗 | 切换窗口可见性 |
| 设置 | 打开设置面板 |
| 皮肤 | 8 套皮肤快速切换 |
| 开机自启 | 开机自动启动 |
| 重启程序 | 重新启动 |
| 退出 | 完全退出 |

## 设置面板

6 个标签页：GPU 选择、外观（皮肤/缩放/透明度）、数据显示、阈值滑块、通知开关、关于。

## 皮肤制作

在 `skins/` 目录下创建新文件夹，添加 `skin.json`：

```json
{
  "id": "my_skin",
  "name": "我的皮肤",
  "description": "自定义宠物",
  "character_type": "cat",
  "animation_type": "procedural",
  "animations": {
    "idle": {}, "normal": {}, "working": {}, "warning": {}, "critical": {}
  }
}
```

`character_type` 可选值：`cat`, `robot`, `fox`, `bunny`, `demon`, `slime`, `penguin`, `hamster`

## 技术栈

- Python 3.10+
- PyQt5 — GUI 框架
- nvidia-ml-py — NVIDIA GPU 数据采集
- PyInstaller — 打包为独立 exe

## 许可

MIT License
