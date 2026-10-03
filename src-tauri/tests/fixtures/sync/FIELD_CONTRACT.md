# A1-01 同步字段契约

Android HEAD：`06cae09d5cdddfc8662fa7868245f83288aca0d7`。Desktop HEAD：`ededbee3946e5ebadc7f6ada5676e69cdb35afa7`。

由 `python3 scripts/sync-field-contract.py` 从实际 Kotlin 和 Rust Proto 定义生成。字段名/tag/标量类型不一致会使脚本失败；缺失字段明确记录，不能等同为兼容通过。

审计覆盖当前 SyncData 根及所有关联序列化消息；不包含非线上 SyncResult/SyncConflict 和 serializer 内私有的历史错误编号 schema。

## 解释与兼容规则

- `Long` 为有符号 int64，`Int` 为 int32，普通整数编码为 varint；不改成 sint/uint。字符串、消息及重复消息 wire type 为 2。
- JSON 中 Long/Int 是整数，Boolean 是布尔，String/SyncAction 是文本，List 是数组，消息是对象。可空值在安卓 JSON 写入时省略；空字符串和 null 的归一化需按消费契约核对。
- ProtoBuf 标量缺省值可省略；重复列表缺省为空。Android encodeDefaults=false，JSON encodeDefaults=true/explicitNulls=false。lastModified 的构造默认值是当前时间，测试必须显式固定。
- SyncAction 的 Proto 数值依次为 0 CREATE_PLAYLIST、1 DELETE_PLAYLIST、2 RENAME_PLAYLIST、3 ADD_SONG、4 REMOVE_SONG、5 REORDER_SONGS、6 PLAY_SONG；JSON 用名称。
- LEGACY_SONG_ORDER_VERSION=0、LEGACY_SYNC_METADATA_VERSION=0；当前顺序/因果元数据版本=1。favorite.modifiedAt/sortOrder 默认引用 addedTime，Desktop 归一化补齐。
- Desktop 某些 ID 内部以 String 保存，但线上 JSON/Proto 仍为 int64。大于 2^53 的 ID 必须保持精度；进入 JS 的 DTO 另行设计。
- 存在 Proto tag 只证明声明对齐，不证明 JSON 转换、normalize、merge、存储和再次快照已接通；下表存在的字段也须通过真实双端样本验证。
- protobuf/serde 丢弃 unknown 字段后重编码不能保留数据；新字段必须做有类型 codec、合并及持久化。

## 必须完成的语义验收

1. 新四组区段及 recentPlays.resumePositionMs：读→归一化→合并→保存→重启→构建快照→写回，包含历史 IPC/前端重建链路。
2. 因果 token 去无效/重复、确定顺序；删除只移除已见 membership，重新添加的新 token 不被旧墓碑删除。
3. counter shard 同 device/epoch 用 max 而非重复累加；清空标记、基数、日分桶和汇总关系遵循安卓策略。
4. 跳过规则按 bvid/cid、modifiedAt、删除及同时间戳规则合并；时间区间归一化按安卓规则验证。
5. Cover URL sanitize 必须使用真实 serializer；本地 file/content cover 不上传。缺失、合法空、读失败、损坏分别处理。
6. 默认/null、字段别名、旧编号 Proto、三种传输格式及异常/大小上限分别验证；当前样本不等于上述所有项目已完成。

## 全字段对照

### SyncData

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `version` | `String` | 2 (length-delimited) | `"2.0"` | `version: String` |
| 2 | `deviceId` | `String` | 2 (length-delimited) | `""` | `device_id: String` |
| 3 | `deviceName` | `String` | 2 (length-delimited) | `""` | `device_name: String` |
| 4 | `lastModified` | `Long` | 0 (varint) | `System.currentTimeMillis()` | `last_modified: i64` |
| 5 | `playlists` | `List<SyncPlaylist>` | 2 (length-delimited) | `emptyList()` | `playlists: Vec<ProtoSyncPlaylist>` |
| 6 | `favoritePlaylists` | `List<SyncFavoritePlaylist>` | 2 (length-delimited) | `emptyList()` | `favorite_playlists: Vec<ProtoSyncFavoritePlaylist>` |
| 7 | `recentPlays` | `List<SyncRecentPlay>` | 2 (length-delimited) | `emptyList()` | `recent_plays: Vec<ProtoSyncRecentPlay>` |
| 8 | `syncLog` | `List<SyncLogEntry>` | 2 (length-delimited) | `emptyList()` | `sync_log: Vec<ProtoSyncLogEntry>` |
| 9 | `recentPlayDeletions` | `List<SyncRecentPlayDeletion>` | 2 (length-delimited) | `emptyList()` | `recent_play_deletions: Vec<ProtoSyncRecentPlayDeletion>` |
| 10 | `playbackStats` | `List<SyncTrackStat>` | 2 (length-delimited) | `emptyList()` | `playback_stats: Vec<ProtoSyncTrackStat>` |
| 11 | `playbackStatsClearedAt` | `Long` | 0 (varint) | `0L` | `playback_stats_cleared_at: i64` |
| 12 | `playbackStatBuckets` | `List<SyncPlaybackStatBucket>` | 2 (length-delimited) | `emptyList()` | `playback_stat_buckets: Vec<ProtoSyncPlaybackStatBucket>` |
| 13 | `playlistSongDeletions` | `List<SyncPlaylistSongDeletion>` | 2 (length-delimited) | `emptyList()` | `playlist_song_deletions: Vec<ProtoSyncPlaylistSongDeletion>` |
| 14 | `playlistUsageStats` | `List<SyncPlaylistUsageStat>` | 2 (length-delimited) | `emptyList()` | **MISSING** |
| 15 | `localPlaylistPlaybackStats` | `List<SyncLocalPlaylistPlaybackStat>` | 2 (length-delimited) | `emptyList()` | **MISSING** |
| 16 | `localPlaylistPlaybackBuckets` | `List<SyncLocalPlaylistPlaybackBucket>` | 2 (length-delimited) | `emptyList()` | **MISSING** |
| 17 | `biliVideoSkipRules` | `List<SyncBiliVideoSkipRule>` | 2 (length-delimited) | `emptyList()` | **MISSING** |

### SyncPlaylist

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `id` | `Long` | 0 (varint) | `0L` | `id: i64` |
| 2 | `name` | `String` | 2 (length-delimited) | `""` | `name: String` |
| 3 | `songs` | `List<SyncSong>` | 2 (length-delimited) | `emptyList()` | `songs: Vec<ProtoSyncSong>` |
| 4 | `createdAt` | `Long` | 0 (varint) | `0L` | `created_at: i64` |
| 5 | `modifiedAt` | `Long` | 0 (varint) | `0L` | `modified_at: i64` |
| 6 | `isDeleted` | `Boolean` | 0 (varint) | `false` | `is_deleted: bool` |
| 7 | `songOrderVersion` | `Int` | 0 (varint) | `LEGACY_SONG_ORDER_VERSION` | `song_order_version: i32` |

### SyncSong

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `id` | `Long` | 0 (varint) | `0L` | `id: i64` |
| 2 | `name` | `String` | 2 (length-delimited) | `""` | `name: String` |
| 3 | `artist` | `String` | 2 (length-delimited) | `""` | `artist: String` |
| 4 | `album` | `String` | 2 (length-delimited) | `""` | `album: String` |
| 5 | `albumId` | `Long` | 0 (varint) | `0L` | `album_id: i64` |
| 6 | `durationMs` | `Long` | 0 (varint) | `0L` | `duration_ms: i64` |
| 7 | `coverUrl` | `String?` | 2 (length-delimited) | `null` | `cover_url: Option<String>` |
| 8 | `mediaUri` | `String?` | 2 (length-delimited) | `null` | `media_uri: Option<String>` |
| 9 | `addedAt` | `Long` | 0 (varint) | `0L` | `added_at: i64` |
| 10 | `matchedLyric` | `String?` | 2 (length-delimited) | `null` | `matched_lyric: Option<String>` |
| 11 | `matchedTranslatedLyric` | `String?` | 2 (length-delimited) | `null` | `matched_translated_lyric: Option<String>` |
| 12 | `matchedLyricSource` | `String?` | 2 (length-delimited) | `null` | `matched_lyric_source: Option<String>` |
| 13 | `matchedSongId` | `String?` | 2 (length-delimited) | `null` | `matched_song_id: Option<String>` |
| 14 | `userLyricOffsetMs` | `Long` | 0 (varint) | `0L` | `user_lyric_offset_ms: i64` |
| 15 | `customCoverUrl` | `String?` | 2 (length-delimited) | `null` | `custom_cover_url: Option<String>` |
| 16 | `customName` | `String?` | 2 (length-delimited) | `null` | `custom_name: Option<String>` |
| 17 | `customArtist` | `String?` | 2 (length-delimited) | `null` | `custom_artist: Option<String>` |
| 18 | `originalName` | `String?` | 2 (length-delimited) | `null` | `original_name: Option<String>` |
| 19 | `originalArtist` | `String?` | 2 (length-delimited) | `null` | `original_artist: Option<String>` |
| 20 | `originalCoverUrl` | `String?` | 2 (length-delimited) | `null` | `original_cover_url: Option<String>` |
| 21 | `originalLyric` | `String?` | 2 (length-delimited) | `null` | `original_lyric: Option<String>` |
| 22 | `originalTranslatedLyric` | `String?` | 2 (length-delimited) | `null` | `original_translated_lyric: Option<String>` |
| 23 | `channelId` | `String?` | 2 (length-delimited) | `null` | `channel_id: Option<String>` |
| 24 | `audioId` | `String?` | 2 (length-delimited) | `null` | `audio_id: Option<String>` |
| 25 | `subAudioId` | `String?` | 2 (length-delimited) | `null` | `sub_audio_id: Option<String>` |
| 26 | `playlistContextId` | `String?` | 2 (length-delimited) | `null` | `playlist_context_id: Option<String>` |
| 27 | `syncMembershipTokens` | `List<SyncCausalToken>` | 2 (length-delimited) | `emptyList()` | `sync_membership_tokens: Vec<ProtoSyncCausalToken>` |
| 28 | `syncMetadataVersion` | `Int` | 0 (varint) | `LEGACY_SYNC_METADATA_VERSION` | `sync_metadata_version: i32` |
| 29 | `legacyAddedAt` | `Long?` | 0 (varint) | `null` | `legacy_added_at: Option<i64>` |

### SyncRecentPlay

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `songId` | `Long` | 0 (varint) | `0L` | `song_id: i64` |
| 2 | `song` | `SyncSong` | 2 (length-delimited) | `SyncSong()` | `song: Option<ProtoSyncSong>` |
| 3 | `playedAt` | `Long` | 0 (varint) | `0L` | `played_at: i64` |
| 4 | `deviceId` | `String` | 2 (length-delimited) | `""` | `device_id: String` |
| 5 | `resumePositionMs` | `Long` | 0 (varint) | `0L` | **MISSING** |

### SyncRecentPlayDeletion

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `songId` | `Long` | 0 (varint) | `0L` | `song_id: i64` |
| 2 | `album` | `String` | 2 (length-delimited) | `""` | `album: String` |
| 3 | `mediaUri` | `String?` | 2 (length-delimited) | `null` | `media_uri: Option<String>` |
| 4 | `deletedAt` | `Long` | 0 (varint) | `0L` | `deleted_at: i64` |
| 5 | `deviceId` | `String` | 2 (length-delimited) | `""` | `device_id: String` |

### SyncPlaylistSongDeletion

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `playlistId` | `Long` | 0 (varint) | `0L` | `playlist_id: i64` |
| 2 | `songId` | `Long` | 0 (varint) | `0L` | `song_id: i64` |
| 3 | `album` | `String` | 2 (length-delimited) | `""` | `album: String` |
| 4 | `mediaUri` | `String?` | 2 (length-delimited) | `null` | `media_uri: Option<String>` |
| 5 | `deletedAt` | `Long` | 0 (varint) | `0L` | `deleted_at: i64` |
| 6 | `deviceId` | `String` | 2 (length-delimited) | `""` | `device_id: String` |
| 7 | `removedMembershipTokens` | `List<SyncCausalToken>` | 2 (length-delimited) | `emptyList()` | `removed_membership_tokens: Vec<ProtoSyncCausalToken>` |

### SyncFavoritePlaylist

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `id` | `Long` | 0 (varint) | `0L` | `id: i64` |
| 2 | `name` | `String` | 2 (length-delimited) | `""` | `name: String` |
| 3 | `coverUrl` | `String?` | 2 (length-delimited) | `null` | `cover_url: Option<String>` |
| 4 | `trackCount` | `Int` | 0 (varint) | `0` | `track_count: i32` |
| 5 | `source` | `String` | 2 (length-delimited) | `""` | `source: String` |
| 6 | `songs` | `List<SyncSong>` | 2 (length-delimited) | `emptyList()` | `songs: Vec<ProtoSyncSong>` |
| 7 | `addedTime` | `Long` | 0 (varint) | `0L` | `added_time: i64` |
| 8 | `modifiedAt` | `Long` | 0 (varint) | `addedTime` | `modified_at: i64` |
| 9 | `isDeleted` | `Boolean` | 0 (varint) | `false` | `is_deleted: bool` |
| 10 | `sortOrder` | `Long` | 0 (varint) | `addedTime` | `sort_order: i64` |
| 11 | `browseId` | `String?` | 2 (length-delimited) | `null` | `browse_id: Option<String>` |
| 12 | `playlistId` | `String?` | 2 (length-delimited) | `null` | `playlist_id: Option<String>` |
| 13 | `subtitle` | `String?` | 2 (length-delimited) | `null` | `subtitle: Option<String>` |

### SyncLogEntry

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `timestamp` | `Long` | 0 (varint) | `0L` | `timestamp: i64` |
| 2 | `deviceId` | `String` | 2 (length-delimited) | `""` | `device_id: String` |
| 3 | `action` | `SyncAction` | 0 (varint) | `SyncAction.CREATE_PLAYLIST` | `action: i32` |
| 4 | `playlistId` | `Long?` | 0 (varint) | `null` | `playlist_id: Option<i64>` |
| 5 | `songId` | `Long?` | 0 (varint) | `null` | `song_id: Option<i64>` |
| 6 | `details` | `String?` | 2 (length-delimited) | `null` | `details: Option<String>` |

### SyncPlaybackCounterShard

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `deviceId` | `String` | 2 (length-delimited) | `""` | `device_id: String` |
| 2 | `epochStartedAt` | `Long` | 0 (varint) | `0L` | `epoch_started_at: i64` |
| 3 | `totalListenMs` | `Long` | 0 (varint) | `0L` | `total_listen_ms: i64` |
| 4 | `playCount` | `Int` | 0 (varint) | `0` | `play_count: i32` |
| 5 | `firstPlayedAt` | `Long` | 0 (varint) | `0L` | `first_played_at: i64` |
| 6 | `lastPlayedAt` | `Long` | 0 (varint) | `0L` | `last_played_at: i64` |

### SyncTrackStat

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `identityKey` | `String` | 2 (length-delimited) | `""` | `identity_key: String` |
| 2 | `name` | `String` | 2 (length-delimited) | `""` | `name: String` |
| 3 | `artist` | `String` | 2 (length-delimited) | `""` | `artist: String` |
| 4 | `album` | `String` | 2 (length-delimited) | `""` | `album: String` |
| 5 | `totalListenMs` | `Long` | 0 (varint) | `0L` | `total_listen_ms: i64` |
| 6 | `playCount` | `Int` | 0 (varint) | `0` | `play_count: i32` |
| 7 | `lastPlayedAt` | `Long` | 0 (varint) | `0L` | `last_played_at: i64` |
| 8 | `firstPlayedAt` | `Long` | 0 (varint) | `0L` | `first_played_at: i64` |
| 9 | `coverUrl` | `String?` | 2 (length-delimited) | `null` | `cover_url: Option<String>` |
| 10 | `durationMs` | `Long` | 0 (varint) | `0L` | `duration_ms: i64` |
| 11 | `mediaUri` | `String?` | 2 (length-delimited) | `null` | `media_uri: Option<String>` |
| 12 | `id` | `Long` | 0 (varint) | `0L` | `id: i64` |
| 13 | `albumId` | `Long` | 0 (varint) | `0L` | `album_id: i64` |
| 14 | `counterBaseListenMs` | `Long` | 0 (varint) | `0L` | `counter_base_listen_ms: i64` |
| 15 | `counterBasePlayCount` | `Int` | 0 (varint) | `0` | `counter_base_play_count: i32` |
| 16 | `counterShards` | `List<SyncPlaybackCounterShard>` | 2 (length-delimited) | `emptyList()` | `counter_shards: Vec<ProtoSyncPlaybackCounterShard>` |

### SyncPlaybackStatBucket

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `dayStartAt` | `Long` | 0 (varint) | `0L` | `day_start_at: i64` |
| 2 | `identityKey` | `String` | 2 (length-delimited) | `""` | `identity_key: String` |
| 3 | `name` | `String` | 2 (length-delimited) | `""` | `name: String` |
| 4 | `artist` | `String` | 2 (length-delimited) | `""` | `artist: String` |
| 5 | `album` | `String` | 2 (length-delimited) | `""` | `album: String` |
| 6 | `totalListenMs` | `Long` | 0 (varint) | `0L` | `total_listen_ms: i64` |
| 7 | `playCount` | `Int` | 0 (varint) | `0` | `play_count: i32` |
| 8 | `lastPlayedAt` | `Long` | 0 (varint) | `0L` | `last_played_at: i64` |
| 9 | `firstPlayedAt` | `Long` | 0 (varint) | `0L` | `first_played_at: i64` |
| 10 | `coverUrl` | `String?` | 2 (length-delimited) | `null` | `cover_url: Option<String>` |
| 11 | `durationMs` | `Long` | 0 (varint) | `0L` | `duration_ms: i64` |
| 12 | `mediaUri` | `String?` | 2 (length-delimited) | `null` | `media_uri: Option<String>` |
| 13 | `id` | `Long` | 0 (varint) | `0L` | `id: i64` |
| 14 | `albumId` | `Long` | 0 (varint) | `0L` | `album_id: i64` |
| 15 | `counterBaseListenMs` | `Long` | 0 (varint) | `0L` | `counter_base_listen_ms: i64` |
| 16 | `counterBasePlayCount` | `Int` | 0 (varint) | `0` | `counter_base_play_count: i32` |
| 17 | `counterShards` | `List<SyncPlaybackCounterShard>` | 2 (length-delimited) | `emptyList()` | `counter_shards: Vec<ProtoSyncPlaybackCounterShard>` |

### SyncPlaylistUsageStat

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `playlistKey` | `String` | 2 (length-delimited) | `""` | **MISSING** |
| 2 | `source` | `String` | 2 (length-delimited) | `""` | **MISSING** |
| 3 | `id` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 4 | `subtype` | `String?` | 2 (length-delimited) | `null` | **MISSING** |
| 5 | `name` | `String` | 2 (length-delimited) | `""` | **MISSING** |
| 6 | `coverUrl` | `String?` | 2 (length-delimited) | `null` | **MISSING** |
| 7 | `trackCount` | `Int` | 0 (varint) | `0` | **MISSING** |
| 8 | `lastOpenedAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 9 | `firstOpenedAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 10 | `openCount` | `Int` | 0 (varint) | `0` | **MISSING** |
| 11 | `counterBaseOpenCount` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 12 | `counterShards` | `List<SyncPlaybackCounterShard>` | 2 (length-delimited) | `emptyList()` | **MISSING** |
| 13 | `fid` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 14 | `mid` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 15 | `browseId` | `String?` | 2 (length-delimited) | `null` | **MISSING** |
| 16 | `playlistId` | `String?` | 2 (length-delimited) | `null` | **MISSING** |
| 17 | `subtitle` | `String?` | 2 (length-delimited) | `null` | **MISSING** |

### SyncLocalPlaylistPlaybackStat

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `playlistId` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 2 | `totalPlayCount` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 3 | `lastPlayedAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 4 | `firstPlayedAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 5 | `counterBasePlayCount` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 6 | `counterShards` | `List<SyncPlaybackCounterShard>` | 2 (length-delimited) | `emptyList()` | **MISSING** |

### SyncLocalPlaylistPlaybackBucket

来源：[SyncDataModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncDataModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `dayStartAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 2 | `playlistId` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 3 | `playCount` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 4 | `lastPlayedAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 5 | `firstPlayedAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 6 | `counterBasePlayCount` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 7 | `counterShards` | `List<SyncPlaybackCounterShard>` | 2 (length-delimited) | `emptyList()` | **MISSING** |

### SyncBiliVideoSkipInterval

来源：[SyncBiliVideoSkipModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncBiliVideoSkipModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `startMs` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 2 | `endMs` | `Long` | 0 (varint) | `0L` | **MISSING** |

### SyncBiliVideoSkipRule

来源：[SyncBiliVideoSkipModels.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/model/sync/SyncBiliVideoSkipModels.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `bvid` | `String` | 2 (length-delimited) | `""` | **MISSING** |
| 2 | `cid` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 3 | `intervals` | `List<SyncBiliVideoSkipInterval>` | 2 (length-delimited) | `emptyList()` | **MISSING** |
| 4 | `modifiedAt` | `Long` | 0 (varint) | `0L` | **MISSING** |
| 5 | `isDeleted` | `Boolean` | 0 (varint) | `false` | **MISSING** |

### SyncCausalToken

来源：[SyncCausalToken.kt](../../../../../NeriPlayer-fork/modules/model/src/main/java/moe/ouom/neriplayer/data/sync/model/SyncCausalToken.kt)。

| Tag | JSON 字段 | Kotlin 类型 | Wire | 默认值 | Desktop Proto |
| --- | --- | --- | --- | --- | --- |
| 1 | `deviceId` | `String` | 2 (length-delimited) | `""` | `device_id: String` |
| 2 | `counter` | `Long` | 0 (varint) | `0L` | `counter: i64` |

共 17 个消息，167 个字段。根缺失 tag 14—17；既有消息缺失 SyncRecentPlay tag 5；四个新增根区段关联的新消息尚未定义。
