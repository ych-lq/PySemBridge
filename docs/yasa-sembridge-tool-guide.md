# YASA-sembridge Tool Guide

本文档说明 PySemBridge 仓库内集成版 YASA 工具的目录、功能和完整操作流程。

## 目录位置

集成版 YASA 位于：

```text
integrations/yasa/YASA-Engine-sembridge/
```

该目录是可直接运行的 YASA 引擎副本，包含 PySemBridge 对接所需的源码改动、`package.json`、`package-lock.json`、规则资源、测试目录和 Python UAST 解析二进制 `uast4py-linux-amd64`。本仓库不提交 `node_modules/`、运行日志或原始 `.git/` 目录，依赖通过锁文件重新安装。

旧的 `integrations/yasa/yasa-sembridge-interface.patch` 已删除；现在以完整工具目录作为复现实验入口。

## 功能简介

YASA-sembridge 在原 YASA 扫描流程上增加了 PySemBridge facts 输入：

```bash
--semanticBridgeFacts <file>
```

该参数加载 PySemBridge 生成的 YASA facts JSON，并在 YASA 正常输出 SARIF 后追加一条语义桥增强结果。当前能力包括：

- 校验并加载 `yasa_injection.graph_facts` 和 `yasa_injection.flow_facts`。
- 保留 YASA 原始 source/sink 规则扫描结果。
- 根据 bridge facts、验证信息和 evidence 生成 `semanticBridgeEnhanced: true` 的完整链路 SARIF finding。
- 写出 `semantic_bridge_summary.json`，记录增强是否成功、预期 sink、gap 类型等摘要。

当前实现属于报告层增强：它补齐 SARIF 中的完整 source-to-real-sink 证据链，但尚未把 facts 深度注入 YASA 内部符号执行/污点传播逻辑。

## 安装依赖

在 PySemBridge 仓库根目录中：

```bash
cd integrations/yasa/YASA-Engine-sembridge
npm install
```

如需重新生成构建产物：

```bash
npm run build
```

日常实验可以直接使用 `npx tsx src/main.ts` 运行源码入口。

## 基本运行流程

1. 在 PySemBridge 中生成或准备 Semantic Bridge IR。

```bash
python3 -m pysembridge.cli compile-yasa \
  --bridge bridges/cve-2025-55156-pyload/bridge.json \
  --output experiments/results/cve-2025-55156-pyload.yasa-facts.json
```

2. 使用集成版 YASA 扫描目标 Python 项目。

```bash
cd integrations/yasa/YASA-Engine-sembridge

npx tsx src/main.ts \
  --sourcePath /path/to/python/project \
  --language python \
  --report /path/to/output/yasa-sembridge-report \
  --ruleConfigFile /path/to/precise-yasa-rule.json \
  --semanticBridgeFacts /path/to/cve.yasa-facts.json \
  --checkerIds taint_flow_python_input_inner \
  --entrypointMode ONLY_CUSTOM
```

3. 查看输出。

```text
/path/to/output/yasa-sembridge-report/report.sarif
/path/to/output/yasa-sembridge-report/semantic_bridge_summary.json
```

`report.sarif` 中新增的增强结果包含：

```json
{
  "semanticBridgeEnhanced": true,
  "semanticBridge": {
    "sourceBridge": "...",
    "gapTypes": ["..."]
  }
}
```

4. 使用 PySemBridge 验证 SARIF。

```bash
python3 -m pysembridge.cli verify-sarif \
  --sarif /path/to/output/yasa-sembridge-report/report.sarif \
  --expected-sink self.c.execute \
  --expected-trace-contains file_database.py
```

## 一键流水线

PySemBridge 也提供端到端 runner，可自动完成 gap 识别、bridge 合成、facts 编译、YASA 扫描和 SARIF 验证：

```bash
python3 -m pysembridge.cli run-yasa \
  --project /path/to/python/project \
  --project-name cve-name \
  --output-dir experiments/results/tool-pipeline/cve-name \
  --yasa-dir integrations/yasa/YASA-Engine-sembridge \
  --rule-config /path/to/precise-yasa-rule.json \
  --source url \
  --sink self.c.execute.arg0 \
  --expected-sink self.c.execute \
  --expected-trace-contains file_database.py
```

## 关键改动文件

YASA-sembridge 相比原 YASA 的核心改动集中在：

```text
src/config.ts
src/interface/starter.ts
src/engine/analyzer/common/semantic-bridge-facts-loader.ts
src/engine/analyzer/common/semantic-bridge-report-augmenter.ts
```

其中：

- `config.ts` 增加 `semanticBridgeFactsFile` 和 `semanticBridgeFacts` 配置项。
- `starter.ts` 增加 CLI 参数、facts 加载流程和 SARIF 增强调用。
- `semantic-bridge-facts-loader.ts` 负责读取、校验和统计 facts。
- `semantic-bridge-report-augmenter.ts` 负责生成增强 finding 和摘要 JSON。

## 输出解释

成功运行时，日志中会出现类似信息：

```text
[YASA][semantic-bridge] Loaded semantic bridge facts: ... facts=...
[YASA][semantic-bridge] Semantic bridge appended complete-chain finding to .../report.sarif
```

`semantic_bridge_summary.json` 的 `augmented` 为 `true` 表示报告增强已完成。若为 `false`，可根据 `reason` 字段定位原因，例如 SARIF 没有 results 或 facts 格式不符合预期。
