# A1-01 基线结果

执行日期：2026-10-03（Asia/Shanghai）。输入见 `android/manifest.json`，命令见 [README](README.md)。本次没有改产品模型/codec。

## 已通过

- 字段审计：17 个消息、167 个字段；已有 Proto tag 的名称与标量编码类型对齐。
- 安卓真实 codec：5 个场景 × JSON/raw/legacy Base64，共 15 次本端语义往返通过；样本及源码/依赖哈希已保存。
- `cargo test --offline --locked --test sync_interop_fixtures`：1 passed，1 显式 ignored。通过项覆盖 15 种真实输入、格式解码一致性、int64 精度及本地封面 sanitize。
- `cargo test --offline --locked sync::serializer --lib`：现有 11 个测试通过，314 个无关测试被筛选。
- `sync_fixture_codec` 实际解码/重编码 15 种输入成功；这只证明写出成功。

## 明确未通过的目标验收

`android_non_default_fields_survive_desktop_codec -- --ignored` 已实际运行并失败：`playlistUsageStats` 在 JSON 往返中缺失。这是产品现存差异，不能记为通过。

安卓真实 serializer 重新读取 Desktop 产物后，**1/15 通过，14/15 失败**：

| 场景 | JSON | raw / legacy Base64 |
| --- | --- | --- |
| full、deleted、readded | 根 14—17 和 resumePositionMs 丢失 | 同左，另丢 CREATE_PLAYLIST 日志 |
| cleared | playlistUsageStats、biliVideoSkipRules 和 resumePositionMs 丢失 | 同左，另丢 CREATE_PLAYLIST 日志 |
| defaults | 通过 | 空 deviceId/deviceName 被替换为桌面默认身份 |

后两种差异来自已有压缩写入兼容策略，不是本轮引入：

- `serializer.rs::log_entry_is_proto_safe` 过滤 action 数值 0，因而七种操作只输出六种。当前安卓模型已经为 CREATE_PLAYLIST 提供默认值；后续需确定旧客户端兼容范围，再决定如何保留或明确允许该日志变化。
- `sync_data_to_proto` 使用 fallback deviceId/deviceName；JSON 写路径没有同样转换。后续须明确空身份规范化契约，不能仅删除样本或减弱断言让结果变绿。

验证器恢复已知四根字段和 resumePositionMs 后再次比较，单独报告这些额外差异。完整对象比较仍严格失败。

## 环境限制与未验证范围

- 原生 Gradle `:sync:testDebugUnitTest` 离线解析失败：缺少 `androidx.profileinstaller:profileinstaller:1.3.0`。本轮用了 README 描述的真实源码最小 JVM 备用入口，没有替换 serializer。
- Rust 1.95.0 的 rustfmt 未安装；未为本轮安装工具或联网。
- 未完成：Android Gradle 模块验证、A1-02/03 产品保留改造、merge 语义、历史 IPC、持久化/重启/再上传、真实服务和平台联调。
- 未做提交、推送或真实 GitHub/WebDAV 写入。

下一轮从 A1-02 开始，并以本文与实际测试失败作为输入。默认 fixture 测试中的 ignore 必须在相应修复完成后移除；完整 A1 要等待 A1-03 的磁盘和历史回流验证。
