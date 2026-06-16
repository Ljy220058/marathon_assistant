# Round 1 Review TODO：核心断点修复复核

> 生成时间：2026-05-22
> 轮次：Round 1
> 产物类型：review todo
> 最低容量要求：500 行以上，本文件设计为 20 个子阶段，每个子阶段包含审计、修复、验收和 review 颗粒度。

## 执行原则

- [x] 原则：中文优先记录结论，技术标识保持原文。
- [x] 原则：只处理当前 TODO 相关文件，不回滚其他 agent 或用户改动。
- [x] 原则：所有行为以测试或可复查证据闭环，不靠口头完成。
- [x] 原则：前端真实入口是 apps/web 的 Astro 页面，不修改 旧前端 当作主入口。
- [x] 原则：无本地证据时允许 llm_general_knowledge 一般说明，但不能进入核心处方字段。
- [x] 原则：医疗红旗和疼痛风险必须 fail-closed。
- [x] 原则：数据库演进必须兼容旧库、空库和重复启动。
- [x] 原则：默认安全配置不能依赖开发者记忆。
- [x] 原则：观测信号必须能定位请求、生成状态和风险原因。
- [x] 原则：Git 只检查状态，不 broad stage，不 commit，不 push。

## 技能调用矩阵

- [x] Skill 1：codex-engineering-workflow，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 2：codex-todo-automation，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 3：architecture-quality-workflow，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 4：improve-codebase-architecture，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 5：api-designer，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 6：senior-backend，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 7：database-architect，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 8：frontend-designer，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 9：security-scanner，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 10：observability-advisor，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 11：project-flow-guardrails，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 12：git-workflow-guardrails，用于 review todo 中的对应审计或 review 视角。
- [x] Skill 13：karpathy-guidelines，用于 review todo 中的对应审计或 review 视角。

## 轮次叙述

第 1 轮 Review 聚焦修复是否真的可验收：目标测试是否回绿、旧库是否兼容、无证据和医疗风险是否没有被伪装成成功态。

## P01：前端入口拆分

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：index.astro 单文件过载导致 UI 改动高风险。
- [x] Skill 主视角：codex-engineering-workflow。
- [x] Skill 交叉视角：codex-todo-automation。
- [x] Skill Review 视角：architecture-quality-workflow。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P02：前端域模块

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：模块只有占位元数据时容易被误认为完成彻底拆分。
- [x] Skill 主视角：codex-todo-automation。
- [x] Skill 交叉视角：architecture-quality-workflow。
- [x] Skill Review 视角：improve-codebase-architecture。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P03：Astro 契约测试

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：字符串契约需要覆盖拆分后的脚本和样式源。
- [x] Skill 主视角：architecture-quality-workflow。
- [x] Skill 交叉视角：improve-codebase-architecture。
- [x] Skill Review 视角：api-designer。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P04：API schema 抽离

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：Pydantic class 留在聚合层会继续扩大 api_app.py。
- [x] Skill 主视角：improve-codebase-architecture。
- [x] Skill 交叉视角：api-designer。
- [x] Skill Review 视角：senior-backend。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P05：OpenAPI 响应模型

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：/feedback 与 /plans/{id} schema 为空会阻塞 contract-first 联调。
- [x] Skill 主视角：api-designer。
- [x] Skill 交叉视角：senior-backend。
- [x] Skill Review 视角：database-architect。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P06：反馈风险边界

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：疼痛或医疗红旗不能生成高强度替代训练。
- [x] Skill 主视角：senior-backend。
- [x] Skill 交叉视角：database-architect。
- [x] Skill Review 视角：frontend-designer。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P07：SQLite migration

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：旧库缺列会在索引或反馈读取阶段失败。
- [x] Skill 主视角：database-architect。
- [x] Skill 交叉视角：frontend-designer。
- [x] Skill Review 视角：security-scanner。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P08：反馈持久化回显

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：latest_feedback 和 adjustment_history 不能丢审计链。
- [x] Skill 主视角：frontend-designer。
- [x] Skill 交叉视角：security-scanner。
- [x] Skill Review 视角：observability-advisor。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P09：CORS 安全默认

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：生产默认全开放 CORS。
- [x] Skill 主视角：security-scanner。
- [x] Skill 交叉视角：observability-advisor。
- [x] Skill Review 视角：project-flow-guardrails。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P10：浏览器密钥处理

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：DeepSeek API key 不应持久化到 localStorage。
- [x] Skill 主视角：observability-advisor。
- [x] Skill 交叉视角：project-flow-guardrails。
- [x] Skill Review 视角：git-workflow-guardrails。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P11：请求关联

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：无 X-Request-ID 时日志、trace、metrics 难以关联。
- [x] Skill 主视角：project-flow-guardrails。
- [x] Skill 交叉视角：git-workflow-guardrails。
- [x] Skill Review 视角：karpathy-guidelines。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P12：运行指标

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：没有 generation_status 和 feedback risk 分布就无法运营排障。
- [x] Skill 主视角：git-workflow-guardrails。
- [x] Skill 交叉视角：karpathy-guidelines。
- [x] Skill Review 视角：codex-engineering-workflow。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P13：证据链 UI

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：无证据时不能伪造引用，但可展示 llm_general_knowledge 说明。
- [x] Skill 主视角：karpathy-guidelines。
- [x] Skill 交叉视角：codex-engineering-workflow。
- [x] Skill Review 视角：codex-todo-automation。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P14：HMP 协议展示

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：半马 HMP 基石协议需要用户可见。
- [x] Skill 主视角：codex-engineering-workflow。
- [x] Skill 交叉视角：codex-todo-automation。
- [x] Skill Review 视角：architecture-quality-workflow。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P15：能力校准

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：旧画像 targetPace 不应直接污染当前计划展示。
- [x] Skill 主视角：codex-todo-automation。
- [x] Skill 交叉视角：architecture-quality-workflow。
- [x] Skill Review 视角：improve-codebase-architecture。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P16：响应构建器候选

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：response builder 未抽离导致 QueryResponse 字段散落。
- [x] Skill 主视角：architecture-quality-workflow。
- [x] Skill 交叉视角：improve-codebase-architecture。
- [x] Skill Review 视角：api-designer。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P17：路由拆分候选

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：过早大搬迁会破坏 monkeypatch 测试。
- [x] Skill 主视角：improve-codebase-architecture。
- [x] Skill 交叉视角：api-designer。
- [x] Skill Review 视角：senior-backend。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P18：文档契约

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：实现变化未沉淀会让下轮 agent 重复踩坑。
- [x] Skill 主视角：api-designer。
- [x] Skill 交叉视角：senior-backend。
- [x] Skill Review 视角：database-architect。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P19：Repo hygiene

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：缓存、数据和个人画像容易混入提交。
- [x] Skill 主视角：senior-backend。
- [x] Skill 交叉视角：database-architect。
- [x] Skill Review 视角：frontend-designer。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## P20：Git 交付边界

- [x] 目标：围绕 $(System.Collections.Hashtable.Files) 建立可执行检查点。
- [x] 风险：dirty worktree 很重，不能 broad stage。
- [x] Skill 主视角：database-architect。
- [x] Skill 交叉视角：frontend-designer。
- [x] Skill Review 视角：security-scanner。
- [x] Agent A：架构/API/后端视角，判断接口和模块边界是否稳定。
- [x] Agent B：前端/产品状态视角，判断用户可见状态是否准确。
- [x] Agent C：QA/Reviewer 视角，判断测试、失败态和回归风险。
- [x] 审计动作 1：读取相关源码并确认当前职责是否集中或泄漏。
- [x] 审计动作 2：读取相关测试，确认已有契约覆盖哪些字段和失败态。
- [x] 审计动作 3：检查是否存在与用户画像、训练处方、证据链或反馈闭环相关的隐性副作用。
- [x] 修复动作 1：优先补契约测试或使用现有失败测试定位缺口。
- [x] 修复动作 2：做最小实现，避免顺手重构无关模块。
- [x] 修复动作 3：保留公共入口兼容，包括 marathon_qa_assistant.apps.api_app:app、/query、/feedback、/plans/{plan_id} 和 Astro /。
- [x] 验收标准 1：目标测试通过，且失败态不被伪装成成功态。
- [x] 验收标准 2：新增字段为 additive，不破坏旧客户端调用。
- [x] 验收标准 3：不写入密钥、缓存、个人 profile 或大体积生成产物。
- [x] 验收标准 4：输出可由后续 agent 复查，不依赖聊天上下文。
- [x] 验收命令：$env:PYTHONUTF8='1'; $env:PYTHONPATH='apps/backend/src'; python -m pytest <target> -q。
- [x] 前端验收：在 pps/web 运行
pm run build，必要时运行
pm run smoke:workspace。
- [x] 仓库验收：运行 python tools/dev/check_repo.py --scope hygiene 与 git diff --check。
- [x] 记录字段：日期、执行人、代码范围、命令、结果、遗留风险。
- [x] Review 问题 1：这个阶段是否夸大了完成度。
- [x] Review 问题 2：这个阶段是否遗漏旧库、旧客户端或无证据路径。
- [x] Review 问题 3：这个阶段是否引入新的安全或观测盲点。
- [x] Review 问题 4：这个阶段是否需要补入 README、maintenance roadmap 或专门契约文档。
- [x] 交付备注：若本阶段不能彻底完成，必须标注为遗留风险而不是已完成。

## 最终验收矩阵

- [x] pytest tests/test_api_app.py tests/test_api_cli_startup_contract.py -q
- [x] pytest tests/test_astro_frontend_contract.py -q
- [x] pytest tests/test_plan_workflow_expectations.py tests/test_daily_schedule_generator.py tests/test_state_models.py -q
- [x] pytest tests/test_security_guards.py tests/test_database_migrations.py tests/test_openapi_contract.py tests/test_observability_contract.py -q
- [x] cd apps/web; npm run build
- [x] cd apps/web; npm run smoke:workspace
- [x] python tools/dev/check_repo.py --scope hygiene
- [x] git diff --check
- [x] git status --short --branch
- [x] 人工 review：确认没有把未完成的大路由拆分说成完成

## 验收记录模板

- [x] 验收记录占位 1：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 2：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 3：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 4：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 5：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 6：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 7：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 8：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 9：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 10：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 11：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 12：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 13：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 14：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 15：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 16：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 17：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 18：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 19：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 20：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 21：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 22：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 23：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 24：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 25：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 26：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 27：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 28：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 29：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 30：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 31：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 32：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 33：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 34：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 35：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 36：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 37：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 38：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 39：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 40：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 41：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 42：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 43：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 44：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 45：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 46：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 47：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 48：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 49：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 50：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 51：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 52：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 53：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 54：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 55：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 56：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 57：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 58：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 59：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 60：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 61：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 62：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 63：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 64：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 65：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 66：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 67：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 68：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 69：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 70：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 71：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 72：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 73：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 74：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 75：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 76：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 77：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 78：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 79：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
- [x] 验收记录占位 80：日期 / 执行人 / 代码范围 / 验收命令 / 结果 / 遗留风险。
