# A1-01 双端同步证据

本目录提供完整字段契约、真实安卓 codec 样本和产品 codec 验证入口。它是后续 A1-02/03 的输入；**当前 Desktop 仍丢失数据，不能据此宣称同步互通完成**。

- [字段契约](FIELD_CONTRACT.md)：17 个消息、167 个字段；机器版本是 `field-contract.json`。
- `android/manifest.json`：生成端 HEAD、当前模型/codec/测试源码 SHA256、工具与依赖哈希、每个样本哈希及执行限制。
- `android/`：5 个场景，每个包含 JSON、raw GZIP(ProtoBuf)、legacy Base64(GZIP) 三种真实 codec 产物。

## 样本场景

| Stem | 覆盖 |
| --- | --- |
| full | 根 1—17、嵌套数据、全部 SyncAction、resumePositionMs、超过 2^53 的 ID/Long 计数、本地封面过滤、重复 device/epoch 分片、两个 Bili 区间 |
| defaults | 可空/缺省标量与空列表；lastModified 明确固定，避免构造默认时钟影响比对 |
| deleted | 删除当前 membership token、删除跳过规则的快照 |
| readded | 保留旧删除记录，使用新 membership token 重新添加，并恢复跳过规则 |
| cleared | 更晚的统计清空标记及空统计区段 |

这些场景是 codec/后续合并的输入。重复合并的幂等性、墓碑与新 token、清空语义、磁盘重启和完整 IPC 消费在 A1-03 验收；本目录没有假定它们已通过。legacy Base64 使用当前 schema 的原始压缩字节包装，不是历史错误字段编号 schema；后者另由现有 serializer 单元测试覆盖。

## 重生成与来源

首选在 Android 根目录执行实际 `:sync` JVM 测试，并通过环境变量导出：

```bash
NERIPLAYER_SYNC_FIXTURE_OUTPUT_DIR=/workspace/NeriPlayer-Desktop-fork/src-tauri/tests/fixtures/sync/android \
  ./gradlew :sync:testDebugUnitTest \
  --tests moe.ouom.neriplayer.data.sync.codec.SyncInteropFixtureTest
```

当前云环境该任务的离线依赖解析被 `androidx.profileinstaller:profileinstaller:1.3.0` 未缓存阻塞。本轮实际采用以下备用入口，直接编译当前模型/codec/sanitize/fixture 源码并调用真实 serializer：

```bash
source /workspace/.onboarding/activate.sh
cd /workspace/NeriPlayer-fork
python3 tools_pub/quality/sync_interop_fixtures.py export \
  /workspace/NeriPlayer-Desktop-fork/src-tauri/tests/fixtures/sync/android
```

该脚本只读取已缓存 JVM 依赖，不联网；版本取当前 catalog。当前配置需要 Kotlin 2.4.10、serialization 1.11.0、compiler-only reflect 2.3.21、coroutines 1.11.0、Android API 37.0、core/core-ktx 1.19.0，以及已有 `:model` classes.jar 提供辅助类型。可用 `--gradle-cache`、`--android-sdk`、`--java`、`--reflect-version` 指定位置。缺少依赖时明确失败，不用替代 serializer 或手写 protobuf。

备用入口使用 Android API stub；样本仅使用能由真实 sanitize 前缀分支确认的 file/content 和公开 example.com URL。它证明当前 codec 字节/模型行为，不验证通用 Android URI 解析、完整模块/APK、设备或真实账号。Gradle 模块验证仍需补做。

export 会重建带源码/依赖/样本哈希的 manifest。Gradle 直接导出只刷新样本，不自动更新 manifest；此时应重新记录来源并更新哈希，不能保留旧 manifest 冒充新来源。

## Desktop 产品验证

在 Desktop 根目录生成字段契约，随后进入 src-tauri：

```bash
python3 scripts/sync-field-contract.py
cd src-tauri
cargo test --offline --locked --test sync_interop_fixtures
cargo test --offline --locked sync::serializer --lib
```

常规 fixture 测试检查 15 种输入的产品解码一致性、int64 精度和封面过滤。这些通过也不代表新字段已保留。严格字段保留测试当前显式 ignore；在 A1-02 修复后移除 ignore，再作为常规回归：

```bash
cargo test --offline --locked --test sync_interop_fixtures \
  android_non_default_fields_survive_desktop_codec -- --ignored
```

完整 codec 往返必须让 Android 实际代码读取 Desktop 产物：

```bash
# Desktop/src-tauri；输出必须与输入分开
cargo run --offline --locked --example sync_fixture_codec -- \
  tests/fixtures/sync/android /workspace/scratch/sync-interop-desktop-roundtrip

# Android 根目录；此命令在当前基线预期返回非零，明确列出损失
python3 tools_pub/quality/sync_interop_fixtures.py validate \
  /workspace/scratch/sync-interop-desktop-roundtrip
```

验证器逐项比对 Android 模型语义，并报告四组根字段、resumePositionMs 和额外模型差异；从不把已知丢失视为通过。GZIP 压缩字节不要求跨语言完全相同。输出目录在 scratch，不接触真实同步备份。

## 接续

查看仓库外 `/workspace/desktop-feature-reproduction-progress.md` 的最新执行记录。下一步先做 A1-02 全模型/codec，再做 A1-03 合并、历史链路、磁盘重启与再次上传。远端迁移前优先落实 A2-03 的完整 mutation/提交语义。
