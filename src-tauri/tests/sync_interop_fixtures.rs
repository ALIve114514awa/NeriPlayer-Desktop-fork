use neri_player_desktop::sync::serializer;
use serde_json::Value;
use std::{fs, path::PathBuf};

fn directory() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/sync/android")
}

#[test]
fn actual_android_formats_decode_consistently_and_keep_int64_ids() {
    for name in ["full", "defaults", "deleted", "readded", "cleared"] {
        let mut reference = None;
        for format in ["json", "raw.bin", "legacy.base64"] {
            let data = serializer::deserialize(&fs::read(directory().join(format!("{name}.{format}"))).unwrap()).unwrap();
            let canonical = serializer::serialize(&data, false).unwrap();
            if let Some(previous) = &reference {
                assert_eq!(&canonical, previous, "{name}.{format}");
            } else {
                reference = Some(canonical);
            }
            if name == "full" {
                assert_eq!(data.playlists[0].id, "9007199254740993");
                assert_eq!(data.playlists[0].songs[0].id, "9007199254740993");
                assert_eq!(data.favorite_playlists[0].id, "9007199254740997");
                assert!(data.playlists[0].songs[0].custom_cover_url.is_none());
                let json: Value = serde_json::from_slice(reference.as_ref().unwrap()).unwrap();
                assert_eq!(json["playlists"][0]["id"].as_i64(), Some(9_007_199_254_740_993));
            }
        }
    }
}

/// Run explicitly during A1-02; keep failures visible until the real model/codec is complete.
#[test]
#[ignore = "A1-02: product models currently discard root tags 14-17 and recent-play tag 5"]
fn android_non_default_fields_survive_desktop_codec() {
    let expected: Value = serde_json::from_slice(&fs::read(directory().join("full.json")).unwrap()).unwrap();
    for format in ["json", "raw.bin", "legacy.base64"] {
        let data = serializer::deserialize(&fs::read(directory().join(format!("full.{format}"))).unwrap()).unwrap();
        let actual: Value = serde_json::from_slice(&serializer::serialize(&data, false).unwrap()).unwrap();
        for field in ["playlistUsageStats", "localPlaylistPlaybackStats", "localPlaylistPlaybackBuckets", "biliVideoSkipRules"] {
            assert_eq!(actual.get(field), expected.get(field), "lost {field} through {format}");
        }
        assert_eq!(actual["recentPlays"][0]["resumePositionMs"], expected["recentPlays"][0]["resumePositionMs"], "lost resumePositionMs through {format}");
    }
}
