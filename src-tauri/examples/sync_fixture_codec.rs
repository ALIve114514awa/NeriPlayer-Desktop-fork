//! Offline interop utility. It calls the product codec; it never writes a remote backup.
use base64::{engine::general_purpose::STANDARD, Engine};
use neri_player_desktop::sync::serializer;
use std::{error::Error, fs, path::PathBuf};

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() != 2 {
        return Err("usage: sync_fixture_codec INPUT_DIRECTORY OUTPUT_DIRECTORY".into());
    }
    let input = PathBuf::from(&args[0]);
    let output = PathBuf::from(&args[1]);
    if input.canonicalize()? == output.canonicalize().unwrap_or_else(|_| output.clone()) {
        return Err("input and output must be separate directories".into());
    }
    fs::create_dir_all(&output)?;
    for name in ["full", "defaults", "deleted", "readded", "cleared"] {
        let mut reference = None;
        for format in ["json", "raw.bin", "legacy.base64"] {
            let decoded = serializer::deserialize(&fs::read(input.join(format!("{name}.{format}")))?)?;
            let canonical = serializer::serialize(&decoded, false)?;
            if let Some(previous) = &reference {
                if canonical != *previous {
                    return Err(format!("format-dependent product decode: {name}.{format}").into());
                }
            } else {
                reference = Some(canonical);
            }
            let bytes = match format {
                "json" => serializer::serialize(&decoded, false)?,
                "raw.bin" => serializer::serialize(&decoded, true)?,
                _ => STANDARD.encode(serializer::serialize(&decoded, true)?).into_bytes(),
            };
            fs::write(output.join(format!("{name}.{format}")), bytes)?;
        }
        println!("{name}: actual Desktop codec decoded and re-encoded all 3 formats");
    }
    println!("Encoding succeeded. Lossless cross-platform compatibility requires Android validation.");
    Ok(())
}
