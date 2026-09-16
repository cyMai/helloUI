# helloUI

从已有前端模板提炼设计规则，并在新增页面和模块时保持风格一致。**同一个页面只维护一份 HTML/路由**，用响应式样式适配手机与桌面。多个 HTML 文件用于首页、列表页、详情页等不同功能页面。

helloUI 将“看到了什么”和“决定以后怎么做”分开：脚本从静态 HTML/CSS 提取可追溯证据与候选规则；Codex 检查实际页面、判断例外和漂移，再把确认的规则写入项目根目录的一份 `DESIGN.md`。自动报告不会覆盖正式规范。

## 安装

```bash
npx skills add cyMai/helloUI -s hello-ui -g -y
```

安装后开启新会话，用 `$hello-ui` 调用。提取脚本需要 Python 3.9 或更新版本，无需额外 Python 包。

## 什么时候用

**第一次把模板放进长期项目时**，可以运行一次提炼，建立简短的 `DESIGN.md`：

```text
$hello-ui 读取这个前端模板，提炼有源码证据的候选设计规则，检查手机与桌面页面，再建立一份 DESIGN.md。无法确认的设计意图标为待确认。
```

**之后无需每次调用。**普通文案或小样式调整直接改。新增页面、增加较大模块、做同一页面的手机适配，或发现跨页风格不一致时再用：

```text
$hello-ui 基于现有模板新增详情页。让同一份页面适配手机和桌面，沿用共享导航、字体、颜色、间距和按钮；只在项目级规则变化时更新 DESIGN.md。
```

## 四层工作流

| 层 | 内容 | 地位 |
| --- | --- | --- |
| 页面源码 | HTML、CSS、组件及现有模板 | 实际实现 |
| 观察证据 | `.hello-ui/evidence.json` 中的源码位置、变量、选择器、断点、页面结构 | 自动提取的事实 |
| 候选规则 | `.hello-ui/proposals.md` 中的重复模式和需要核对的问题 | 待审核，不是规范 |
| 正式规则 | 项目根目录的 `DESIGN.md` | 已确认的当前规范 |

脚本只负责前两层到候选层。比如它能发现多个页面共用 `.button`、`--accent`，却不能仅凭重复次数断定“绿色就是品牌主色”。Codex 应对照用户要求和实际页面，决定该规则是否成立、适用范围是什么、是否存在页面特例。

## 手动提取候选规则

在已放入 HTML/CSS 的项目上运行：

```bash
python /path/to/helloUI/scripts/extract_design.py --project-root /path/to/project
```

Windows PowerShell 示例：

```powershell
python 'C:\path\to\helloUI\scripts\extract_design.py' --project-root 'D:\my-project'
```

默认在目标项目的 `.hello-ui/` 下生成：

- `evidence.json`：HTML 页面、viewport、引用的样式表、共享类名、CSS 变量、重复声明、媒体/容器查询，以及文件和行号。
- `proposals.md`：给人和 Agent 阅读的候选报告，指出可能的共享规则与风险，例如缺少 viewport、页面内局部样式或固定宽度。

这些是**可重新生成的工作材料**，建议将 `.hello-ui/` 加入目标项目的 `.gitignore`。脚本不改业务代码、不创建 `DESIGN.md`、不安装 Git 钩子，也不启动后台任务。已有 `DESIGN.md` 始终保留，由 Codex 根据审核结果做有范围的更新。

### 审核与写入 `DESIGN.md`

1. 阅读报告中的每条候选及对应源码位置。
2. 在至少一个手机宽度和一个桌面宽度查看同一页面；布局在中间宽度转换时补查该处。核对计算样式、内容顺序、导航、按钮、溢出和交互状态。
3. 区分共享规则、合理的页面例外与历史漂移。无法从证据确定的意图标 `[待确认]`。
4. 把确认后的规则精简写入 `DESIGN.md`，不把报告整段粘进去。字段建议见 [`references/design-contract.md`](references/design-contract.md)。

脚本当前分析静态 `.html`、`.htm`、`.css`、`.scss` 文本。它**不会运行浏览器或计算最终样式**，也不会识别所有动态生成页面、CSS-in-JS 与构建时样式；这些需要 Codex 再检查。截图与页面外观的结论必须来自实际渲染。

## 新功能开发时怎么用

### 同一页面适配两端

```text
$hello-ui 把当前详情页适配 390px 手机和 1280px 桌面。保留同一份 HTML；检查导航、内容顺序、主操作、长文本和横向溢出，并沿用 DESIGN.md 的共享风格。
```

优先用流式布局、媒体查询或现有响应式机制，不为同一页面另建 `mobile.html`。断点应由内容碰撞和任务需求解释。

### 新增多个页面或单页多模块

```text
$hello-ui 基于现有首页新增列表页和详情页。每页分别适配手机与桌面，并让共享导航、按钮、字体与间距保持一致。
```

```text
$hello-ui 在当前 HTML 页面新增功能、案例和 FAQ 模块，沿用现有卡片、标题层级和模块节奏，检查手机端顺序与交界处的留白。
```

细化核对项见 [`references/consistency-contract.md`](references/consistency-contract.md)、[`references/responsive-contract.md`](references/responsive-contract.md) 和 [`references/component-contract.md`](references/component-contract.md)。

## `DESIGN.md` 写什么

保持短而可执行，通常包括：项目范围及样式来源、共享视觉规则、页面壳层与组件、同一页面的响应式行为、少量例外与待确认项。它引用实际 CSS 变量和组件，不复制一整份 token 清单。重大选择如果以后可能反复讨论，可以按 [`references/decision-records.md`](references/decision-records.md) 留一份简短的决策记录；普通改动不需要。

旧版 helloUI 曾默认生成 `spec.md`、`domain.md`、`craft.md`、`design.md`、`components.md`、`template.md`。新版本**不会自动删除这些文件**。已有项目先保留；需要迁移时，让 Codex 读取其中仍有效的规则，合并到 `DESIGN.md`，确认后再决定如何处理旧文档。

## 目录结构

```text
helloUI/
├── SKILL.md                         Agent 工作规则
├── README.md                        本说明
├── scripts/
│   └── extract_design.py            提取源码证据与候选规则
├── tests/
│   └── test_extract_design.py       提取流程的基本测试
└── references/
    ├── design-contract.md           一份 DESIGN.md 的写法
    ├── responsive-contract.md       同一页面的响应式检查
    ├── consistency-contract.md      多页面与多模块一致性
    ├── component-contract.md        组件契约
    └── decision-records.md          可选的重大决策记录
```

开发此 skill 时可运行 `python -m unittest discover -s tests -v` 验证提取流程。

## 常见问题

**为什么报告只是候选？** 重复样式也可能是历史遗留。脚本能证明值在哪里出现，不能证明设计意图或判断视觉质量。

**每次修改都要重新提炼吗？** 不用。首次引入模板、共享规则变化或发现跨页漂移时提炼更有价值。日常小改动直接参考现有 `DESIGN.md`。

**会覆盖我手写的 `DESIGN.md` 吗？** 不会。脚本只写 `.hello-ui/` 下的可生成报告；正式规范由 Codex 审核后更新。

**一个项目需要多个设备版 HTML 吗？** 不需要。同一功能页面维护同一份 HTML/路由，让布局和交互响应可用宽度。不同功能页面才使用不同 HTML 文件。
