#!/usr/bin/env python3
"""Audit all protobuf-numbered Android SyncData types against the actual Rust schema."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def constructor(text, start):
    depth, quote, escape = 1, None, False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:index]
    raise ValueError("Unclosed Kotlin constructor")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    desktop = Path(__file__).resolve().parents[1]
    parser.add_argument("--android", type=Path, default=desktop.parent / "NeriPlayer-fork")
    args = parser.parse_args()
    java = args.android / "modules/model/src/main/java/moe/ouom/neriplayer/data"
    sources = [java / "model/sync/SyncDataModels.kt", java / "model/sync/SyncBiliVideoSkipModels.kt", java / "sync/model/SyncCausalToken.kt"]
    rust_path = desktop / "src-tauri/src/sync/proto_models.rs"
    rust = rust_path.read_text()
    rust_types = {}
    for match in re.finditer(r"pub struct (Proto\w+)\s*\{([^}]+)\}", rust, re.S):
        fields = {}
        for field in re.finditer(r'#\[prost\(([^\]]+)\)\]\s*pub (\w+):\s*([^,]+),', match[2]):
            tag = int(re.search(r'tag = "(\d+)"', field[1])[1])
            fields[tag] = {"rustName": field[2], "rustType": field[3].strip(), "prost": field[1]}
        rust_types[match[1]] = fields
    types = []
    for source in sources:
        text = source.read_text()
        for match in re.finditer(r"data class (Sync\w+)\s*\(", text):
            body = constructor(text, match.end())
            fields = []
            for field in re.finditer(r"@ProtoNumber\((\d+)\)\s+val (\w+):\s*([\w<>?]+)\s*=\s*([^\n]+)", body):
                tag, name, kind, default = int(field[1]), field[2], field[3], field[4].rstrip().removesuffix(",")
                if kind.startswith("List<") or kind.rstrip("?") not in ("Long", "Int", "Boolean", "SyncAction"):
                    wire = "2 (length-delimited)"
                else:
                    wire = "0 (varint)"
                actual = rust_types.get("Proto" + match[1], {}).get(tag)
                if actual:
                    camel = re.sub(r"_([a-z])", lambda m: m[1].upper(), actual["rustName"])
                    if camel != name:
                        raise ValueError(f"tag/name mismatch: {match[1]} {tag}: {name} vs {camel}")
                    scalar = kind.rstrip("?")
                    expected_prost = {"Long": "int64", "Int": "int32", "Boolean": "bool", "String": "string", "SyncAction": "int32"}.get(scalar, "message")
                    if not actual["prost"].startswith(expected_prost + ","):
                        raise ValueError(f"wire/type mismatch: {match[1]}.{name}: {actual}")
                fields.append({"tag": tag, "name": name, "kotlinType": kind, "default": default, "nullable": kind.endswith("?"), "wire": wire, "desktop": actual})
            if fields:
                assert len({f['tag'] for f in fields}) == len(fields), match[1]
                types.append({"name": match[1], "source": str(source.relative_to(args.android)), "fields": fields})
    assert len(next(t for t in types if t['name'] == 'SyncData')['fields']) == 17
    output = desktop / "src-tauri/tests/fixtures/sync"
    output.mkdir(parents=True, exist_ok=True)
    sha = lambda root: subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    contract = {"schemaVersion": 1, "androidHead": sha(args.android), "desktopHead": sha(desktop), "types": types}
    (output / "field-contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n")
    lines = ["# A1-01 同步字段契约", "", f"Android HEAD：`{contract['androidHead']}`。Desktop HEAD：`{contract['desktopHead']}`。", "",
             "由 `python3 scripts/sync-field-contract.py` 从实际 Kotlin 和 Rust Proto 定义生成。字段名/tag/标量类型不一致会使脚本失败；缺失字段明确记录，不能等同为兼容通过。", "",
             "审计覆盖当前 SyncData 根及所有关联序列化消息；不包含非线上 SyncResult/SyncConflict 和 serializer 内私有的历史错误编号 schema。", "",
             "## 解释与兼容规则", "",
             "- `Long` 为有符号 int64，`Int` 为 int32，普通整数编码为 varint；不改成 sint/uint。字符串、消息及重复消息 wire type 为 2。",
             "- JSON 中 Long/Int 是整数，Boolean 是布尔，String/SyncAction 是文本，List 是数组，消息是对象。可空值在安卓 JSON 写入时省略；空字符串和 null 的归一化需按消费契约核对。",
             "- ProtoBuf 标量缺省值可省略；重复列表缺省为空。Android encodeDefaults=false，JSON encodeDefaults=true/explicitNulls=false。lastModified 的构造默认值是当前时间，测试必须显式固定。",
             "- SyncAction 的 Proto 数值依次为 0 CREATE_PLAYLIST、1 DELETE_PLAYLIST、2 RENAME_PLAYLIST、3 ADD_SONG、4 REMOVE_SONG、5 REORDER_SONGS、6 PLAY_SONG；JSON 用名称。",
             "- LEGACY_SONG_ORDER_VERSION=0、LEGACY_SYNC_METADATA_VERSION=0；当前顺序/因果元数据版本=1。favorite.modifiedAt/sortOrder 默认引用 addedTime，Desktop 归一化补齐。",
             "- Desktop 某些 ID 内部以 String 保存，但线上 JSON/Proto 仍为 int64。大于 2^53 的 ID 必须保持精度；进入 JS 的 DTO 另行设计。",
             "- 存在 Proto tag 只证明声明对齐，不证明 JSON 转换、normalize、merge、存储和再次快照已接通；下表存在的字段也须通过真实双端样本验证。",
             "- protobuf/serde 丢弃 unknown 字段后重编码不能保留数据；新字段必须做有类型 codec、合并及持久化。", "",
             "## 必须完成的语义验收", "",
             "1. 新四组区段及 recentPlays.resumePositionMs：读→归一化→合并→保存→重启→构建快照→写回，包含历史 IPC/前端重建链路。",
             "2. 因果 token 去无效/重复、确定顺序；删除只移除已见 membership，重新添加的新 token 不被旧墓碑删除。",
             "3. counter shard 同 device/epoch 用 max 而非重复累加；清空标记、基数、日分桶和汇总关系遵循安卓策略。",
             "4. 跳过规则按 bvid/cid、modifiedAt、删除及同时间戳规则合并；时间区间归一化按安卓规则验证。",
             "5. Cover URL sanitize 必须使用真实 serializer；本地 file/content cover 不上传。缺失、合法空、读失败、损坏分别处理。",
             "6. 默认/null、字段别名、旧编号 Proto、三种传输格式及异常/大小上限分别验证；当前样本不等于上述所有项目已完成。", "",
             "## 全字段对照", ""]
    count = 0
    for entry in types:
        rel = os.path.relpath(args.android / entry['source'], output)
        lines += [f"### {entry['name']}", "", f"来源：[{Path(entry['source']).name}]({rel})。", "",
                  "| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |", "| --- | --- | --- | --- | --- | --- |"]
        for field in entry['fields']:
            actual = field['desktop']
            status = "**MISSING**" if actual is None else f"`{actual['rustName']}: {actual['rustType']}`"
            lines.append(f"| {field['tag']} | `{field['name']}` | `{field['kotlinType']}` | {field['wire']} | `{field['default']}` | {status} |")
            count += 1
        lines += [""]
    lines += [f"共 {len(types)} 个消息，{count} 个字段。根缺失 tag 14—17；既有消息缺失 SyncRecentPlay tag 5；四个新增根区段关联的新消息尚未定义。", ""]
    (output / "FIELD_CONTRACT.md").write_text("\n".join(lines))
    print(f"Audited {len(types)} messages / {count} fields; wrote FIELD_CONTRACT.md and field-contract.json")


if __name__ == "__main__":
    main()
