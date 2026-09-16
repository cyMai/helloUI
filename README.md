# helloUI

面向长期迭代项目的设计说明书 skill。它把功能、领域、设计工艺、视觉系统、组件和页面结构分成六份持续维护的 Markdown 文档，并要求明确写出网页桌面端、手机端和中间宽度的自适应行为。

helloUI 不生成一套固定视觉风格。它从项目现状与已确认的设计决策出发，帮助 Codex 在多次迭代中保持规则一致。附带的同步脚本只收集源码路径线索，不会凭代码猜测业务意图或自动改写手写设计规则。

## 适用场景

- 新项目需要建立可供 AI 和团队持续使用的设计规范。
- 已有网页或 App 项目需要补齐设计说明，并在后续改版中持续更新。
- 同一产品需要协调手机、平板或中间宽度、桌面端的布局与交互。
- 需要审查实现与设计规则是否漂移，并保留重要设计决策的理由。

一次性海报、孤立页面草图或纯图片生成通常不需要这套六文档工作流。

## 安装

在支持 Agent Skills 的环境中运行：

```bash
npx skills add cyMai/helloUI -s hello-ui -g -y
```

安装后开启新会话，输入：

```text
$hello-ui 为当前项目建立长期设计说明书，检查手机和桌面端的自适应行为。
```

也可以把本仓库放到 Codex 的全局 skills 目录，并以 `hello-ui` 作为目录名。需要 Python 3.9 或更新版本来运行可选同步脚本；仅阅读和编辑设计文档不依赖 Python。

## 会生成什么

在目标项目根目录维护六份文档：

| 文件 | 记录的内容 | 自适应重点 |
| --- | --- | --- |
| `spec.md` | 用户、功能、信息架构、状态流转、验收条件 | 跨端任务链是否改变、入口如何保留 |
| `domain.md` | 业务对象、术语、风险和责任边界 | 不同端的业务语义保持一致 |
| `craft.md` | 排版、密度、反馈和动效 | 触控、指针、动态字体与减少动效 |
| `design.md` | 语义 token、主题、字体和布局尺度 | 容器、流式规则及有依据的断点 |
| `components.md` | 组件用途、变体、状态和无障碍 | 窄屏、中间宽度、宽屏的组件转换 |
| `template.md` | 页面类型、导航、区域和栏位 | 导航、内容优先级及操作区变化 |

文档首先应记录当前有效的规则。代码只能证明已有实现，不能证明某项设计是被批准的。无法证实的判断标为 `[待确认]`。六份文档的细化字段见 [`references/spec-contract.md`](references/spec-contract.md)。

## 推荐使用流程

### 1. 初始化现有项目

在 Codex 中打开目标项目，然后输入：

```text
$hello-ui 读取当前项目的路由、组件、样式和已有设计文档，建立六份设计说明。只把能证实的项目事实写为事实；列出需要我确认的选择。
```

若要手动建立文档，在任意目录运行：

```bash
python /path/to/helloUI/scripts/sync_docs.py --project-root /path/to/project --mode immediate
```

Windows PowerShell 示例：

```powershell
python 'C:\path\to\helloUI\scripts\sync_docs.py' --project-root 'D:\my-project' --mode immediate
```

脚本会创建缺失的六份文档，并列出找到的源码路径。随后由设计者或 Codex 填写当前规则。生成的 `## 当前规则` 中的 `[待确认]` 是待处理项，不是可直接用于开发的规范。

### 2. 日常迭代

修改需求或界面时，把本次决定写入对应文档。例如：

```text
$hello-ui 把商品详情页改成手机单栏、桌面双栏。更新受影响的设计说明和组件契约，验证窄屏与桌面状态，并记录这次布局决定。
```

推荐顺序是：读当前规则 → 确认受影响的页面与组件 → 实现和验证 → 更新归属文档 → 记录值得长期保留的决策。相同规则只在一份文档中维护，其他文档用链接引用。

### 3. 同步源码线索

用户明确要求同步，或本次变更已完成时：

```bash
python /path/to/helloUI/scripts/sync_docs.py --project-root /path/to/project --mode immediate
```

进入已有项目，只想记录源码变化并等待工作稳定时：

```bash
python /path/to/helloUI/scripts/sync_docs.py --project-root /path/to/project --mode passive
```

被动模式默认要求 30 分钟静默。可以用 `--quiet-minutes 10` 调整。它**不会启动后台任务**；下次运行脚本且静默时间已满足时，才会同步相关文档。运行状态保存在目标项目的 `.design-spec/source-state.json`，建议将 `.design-spec/` 加入该项目的 `.gitignore`。

同步只替换以下标记之间的源码路径线索：

```markdown
<!-- living-design:source:start -->
## 源码线索（自动更新，不代表设计决策）
...
<!-- living-design:source:end -->
```

标记外的手写规则不会被覆盖。如果同名文档已有内容却没有完整标记，脚本会保留该文件并提示人工合并。脚本不会自动安装 Git 钩子、修改项目配置或提交代码。

### 4. 检查文档完整性

```bash
python /path/to/helloUI/scripts/sync_docs.py --project-root /path/to/project --check
```

检查确认六份文件存在且包含受管标记。它不能证明设计规则正确，还需要查看实际页面和组件。

## 手机与桌面端如何写

不要只写“移动端单栏、桌面端双栏”。一条可执行的规则需要说明触发条件和任务如何完成。例如：

> 当详情主栏与辅助信息同时显示会压缩正文行长时，辅助信息移至正文之后；主要购买操作在手机端保持可见，但不遮挡系统安全区与虚拟键盘。桌面端辅助信息位于右侧，并维持主内容的可读行长。

对受影响界面，检查导航入口、内容顺序、操作位置、表格或长文本溢出、触控目标、键盘焦点、横屏、缩放、动态字体和减少动效。具体矩阵见 [`references/responsive-contract.md`](references/responsive-contract.md)。断点数值应来自项目实现或明确决定，并解释为什么在该条件下转换。

## 目录结构

```text
helloUI/
├── SKILL.md                         Agent 入口
├── README.md                        本说明
├── scripts/
│   └── sync_docs.py                 源码线索同步与文档检查
└── references/
    ├── spec-contract.md             六份文档的写法
    ├── responsive-contract.md       跨端自适应检查表
    ├── component-contract.md        组件契约
    └── decision-records.md          设计决策记录
```

## 常见问题

**同步后为什么只有路径，没有完整设计规范？** 源码路径是线索。业务目标、设计意图和批准状态需要结合用户要求、现有规范和实际界面判断，不能由扫描脚本臆造。

**已有 `design.md` 会被覆盖吗？** 不会。缺少完整受管标记时，脚本保留原文件并提示。先人工合并，再重新运行。

**被动模式为什么没有立即更新？** 它等待静默期，并只在下次调用时检查。需要立即收敛时使用 `--mode immediate`。

**如何处理规则冲突？** 优先遵循当前用户要求和已确认的设计决策。核对代码与旧规范，更新当前规则，并用决策记录解释变化；不要把两个冲突版本都留作现行规则。

**是否会自动修改业务代码？** 同步脚本只写六份设计文档和 `.design-spec/source-state.json`。Codex 在具体设计实现任务中是否修改业务代码，由该任务的用户要求决定。
