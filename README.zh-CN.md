# Agent-Skill-for-evidence-gated-AI-video-production.

[English](README.md) | **简体中文**

用于增强 DeepSeek 接入 Codex 环境后的视频生成能力。

## Video Production Director

一个以质量优先为核心的 Agent Skill，用于规划、生成、剪辑、审查和交付 AI 视频、程序化视频、混合视频及已有素材视频。

当前 Skill 版本：**0.5.0**。

大多数提示词集合只优化一次模型调用。本 Skill 会在多次调用之间维护完整的制作记忆：创意方向、资产连续性、镜头契约、模型能力、候选证据、剪辑决策、技术质检、权利状态和最终交付。

## 核心改进

- **先选控制方式，再选模型**：优先使用确定性资产和已有素材，其次是图生视频与关键帧控制，最后才用文生视频进行探索。
- **先锁脚本和主时钟**：在锁定镜头时长之前，确定视觉动作、旁白、音乐或对白哪一个是时间基准。
- **把参考图当作规格**：每份参考都必须声明控制范围和禁止控制的范围。
- **先锁资产，再做昂贵生成**：人物、产品、地点、道具和状态变体在进入正式生成前必须锁定。
- **每个镜头都有明确职责**：包含一个主要动作、一个镜头动机、可见的起止状态和预先登记的验收标准。
- **验收全链路追踪**：必现项、禁止项和签名时刻都要链接到镜头验收、QA 判定和哈希证据。
- **通用运动契约**：按需检查接触、滚动速度、关节、布料根部、流体、碰撞、银幕方向和口型同步。
- **证据来源分级**：最终画面不能被当成唯一的前置身份参考或运动控制证据。
- **候选全程可追溯**：记录每个候选的提示词、模型、版本、参考资产、参数、成本、输出哈希和评审结论。
- **分层审查**：技术、视觉、编辑和权利状态分别验收，不用一个模糊的“看起来不错”代替。
- **真实预演门禁**：发布前必须有经过完整播放审核的 animatic 和机器可读时间线。
- **门禁带文件哈希**：已批准内容一旦修改，对应门禁会自动失效，必须重新审查。
- **按实际文件发布**：发布前要求原生分辨率镜头证据、完整视频技术检查和最终交付清单。
- **结构化审阅交接**：输出与最终媒体哈希绑定的 `qa/review-handoff.json`，包含稳定锚点、生成上下文、有意效果和已知对照。
- **审阅反馈闭环**：接收结构化变更请求并返回回归结果，让生成 Skill 与审阅 Skill 相互改进，而不是自我批准。
- **变更后独立复核**：生成侧的修复响应只是 provisional，必须由新的独立审阅确认新媒体哈希与完整回归结果。

## 工作流

```text
需求接收
  -> 创意方向
  -> 脚本与主时钟
  -> 连续性与资产锁定
  -> 分镜与已审核动态分镜（animatic）
  -> 基于能力选择生成方式
  -> 候选片评审
  -> 剪辑、声音、图形与调色
  -> 哈希绑定的审阅交接
  -> 技术 + 视觉 + 编辑 + 权利审查
  -> 限定作用域的审阅反馈与回归
  -> 变更后新字节独立复核
  -> 交付清单
```

入口 Skill 会按需加载六份核心参考：

- `intake-and-quality.md`
- `requirements-and-traceability.md`
- `directing-and-continuity.md`
- `motion-contracts.md`
- `generation-and-repair.md`
- `qa-and-delivery.md`

`artifacts.md` 说明脚本读取和维护的项目状态。

## 安装

将仓库复制到 Codex Skills 目录：

```bash
git clone <repository-url> \
  "${CODEX_HOME:-$HOME/.codex}/skills/video-production-director"
```

也可以使用兼容的 Skills 安装器：

```bash
npx skills add <owner>/<repository>
```

安装后请新开一个 Codex 对话，让 Skill 被重新发现。

### 从 0.1.0 至 0.4.0 升级

为旧项目补齐新字段与产物，不覆盖已有内容，并使下游旧批准失效：

```bash
python scripts/upgrade_project.py projects/my-video
```

## 快速开始

创建项目：

```bash
python scripts/init_project.py projects/my-video \
  --title "My Video" --mode hero
```

填写 brief 和创意方向后，检查规划状态：

```bash
python scripts/preflight.py --project projects/my-video
python scripts/validate_project.py projects/my-video --mode plan
```

完成一个阶段后记录审批：

```bash
python scripts/approve_gate.py projects/my-video \
  --gate direction --owner "director"
```

渲染完成后检查实际成片：

```bash
python scripts/inspect_media.py projects/my-video/renders/final.mp4 \
  --project projects/my-video \
  --output projects/my-video/qa/technical-report.json \
  --frames-dir projects/my-video/qa/frames \
  --sample-fps 2
```

生成交付清单：

```bash
python scripts/build_manifest.py projects/my-video \
  --file master=renders/final.mp4 \
  --authority "Client or platform specification" \
  --rights-verified
```

执行最终发布门禁：

```bash
python scripts/validate_project.py projects/my-video --mode final
```

## 环境要求

- Python 3.10 或更高版本。
- 自动媒体检查需要 `ffmpeg` 和 `ffprobe`。
- 只有所选制作路线需要时，才需要对应的模型 API、渲染器或 MCP server。
- 图像或视频理解工具是可选能力。它们只能辅助筛选缺陷，不能代替最终责任人进行审美、故事、品牌和事实判断。

项目状态和校验脚本只依赖 Python 标准库。如果 FFmpeg 不在 `PATH` 中，请通过 `FFMPEG_BIN` 和 `FFPROBE_BIN` 指向两个可执行文件。`preflight.py` 会报告媒体检查链路是否就绪。

## 项目状态

```text
project/
├── project.json
├── brief.md
├── creative-bible.md
├── script.md
├── master-clock.json
├── assets.json
├── shots.json
├── timeline.md
├── timeline.json
├── generation-log.jsonl
├── qa-report.json
├── delivery-manifest.json
├── inputs/
├── assets/
├── prompts/
├── generations/
├── selects/
├── animatic/
├── qa/
├── rights/
├── renders/
└── delivery/
```

## 脚本

| 脚本 | 用途 |
| --- | --- |
| `init_project.py` | 创建带状态的视频项目骨架 |
| `upgrade_project.py` | 为旧项目补齐 0.5.0 审阅契约产物，并使旧批准失效 |
| `preflight.py` | 检查 Python、媒体工具、项目状态和模型配置 |
| `validate_project.py` | 校验规划结构或强制执行最终发布门禁 |
| `approve_gate.py` | 对阶段产物计算哈希并记录明确审批 |
| `record_candidate.py` | 记录生成候选的模型、提示词、成本和文件哈希 |
| `inspect_media.py` | 探测、完整解码、抽帧、测量响度并记录技术观察 |
| `make_contact_sheet.py` | 生成概览联系表，但不把联系表当作验收证据 |
| `build_manifest.py` | 计算最终文件哈希并生成交付清单 |

## 质量模型

默认评审维度包括故事或信息、视觉方向、运动与连续性、剪辑与声音，以及技术交付质量。评分用于候选比较，不能被用来平均掉阻断问题。

权利、同意、可访问性、安全和法律问题不能由 Agent 自行豁免。一个成功的 API 请求或一个能解码的文件，都不等于可以发布。

如果项目策略要求独立审核，制作代理的自审不能通过最终发布。自动检查结果在满足独立审核策略前只能视为预览。

## 模型配置

将 `assets/model-profile.example.json` 复制到适配层，并根据当前官方文档填写。必须记录核对日期。

模型目录、价格、限制、输入模态、内容审核、数据保留和商业条款都会频繁变化，不应写死在稳定的创作规则中。

## 设计来源

本项目为原创实现。其架构参考了公开的 Agent 视频工作流，包括 OpenMontage、Generative Media Skills、Film Studio Skills、DirectorSKILL、Scenario Skills、AI Video Generation Skills、Drama Skills、Super Video Maker、Claude Remotion Skill 和 VEFX-Bench。

具体来源和许可证边界见 [CREDITS.md](CREDITS.md)。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
