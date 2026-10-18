# EchoSkin

**ReverbScope 社区皮肤。** 可逆的视觉主题，只换外观，不碰任何测量功能。

[English](README.md) | **简体中文**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

![Midnight Studio 主题预览](themes/midnight-studio/preview.png)

## 这是什么

EchoSkin 是 [ReverbScope](https://github.com/jingyemingyue/ReverbScope) 的社区主题库。每个皮肤是一个文件夹，包含 `skin.json` 清单、Qt 样式表（`theme.qss`）和一张预览图。皮肤只改变外观——测量、分析和音频 I/O 完全不受影响。

**原则：**
- **可逆**——一键恢复默认外观，不留残留
- **无侵入**——皮肤永远不碰测量代码和音频路径
- **版本化**——每个皮肤声明支持的 ReverbScope 版本

## 画廊

| 皮肤 | 作者 | 预览 |
| --- | --- | --- |
| [Midnight Studio](themes/midnight-studio/) | EchoSkin 团队 | ![Midnight Studio](themes/midnight-studio/preview.png) |

*想上架你的皮肤？看[贡献](#贡献)。*

## 安装

1. 从 `themes/` 下载皮肤文件夹（或 `.zip`）。
2. 在 ReverbScope 里打开 **设置 → 外观 → 导入皮肤…**，选择文件夹。
3. 皮肤立即生效。恢复默认选 **恢复默认外观** 即可。

> 皮肤功能需要 ReverbScope 0.5.0b3 或更新版本。外观设置页还在开发中——去 [ReverbScope releases](https://github.com/jingyemingyue/ReverbScope/releases) 确认皮肤加载器是否可用。

## 制作皮肤

一个皮肤文件夹含三个文件：

```
my-skin/
├── skin.json     # 清单：名字、作者、版本、支持的 ReverbScope 版本
├── theme.qss     # Qt 样式表
└── preview.png   # 1280×800 预览截图（必需）
```

完整格式见 [docs/SKIN_SPEC.md](docs/SKIN_SPEC.md)，制作流程见 [docs/MAKING_SKINS.md](docs/MAKING_SKINS.md)（英文版，中文版待补充）。

## 贡献

- **提交皮肤**——开 PR 把你的文件夹加到 `themes/` 下。`preview.png` 必须是真机截图，不接受效果图。
- **报 bug**——用 issue 模板，写明 ReverbScope 版本和皮肤名。

## 安全

- 皮肤只是样式表和图片，不能执行代码。
- EchoSkin 不修改你的 ReverbScope 安装；删掉皮肤文件夹即完全还原。
- 只从你信任的来源安装皮肤。

## 许可证

MIT——见 [LICENSE](LICENSE)。ReverbScope 本体是另一个项目（Apache-2.0）；EchoSkin 是社区项目，与其开发无关。
