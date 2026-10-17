//! Frozen M1-012 directional owner API. Production/default worker builds
//! retain the old bounded std sync_channel compatibility implementation.
//! M0-provided =0.3.2 rtrb only selected by explicit shared feature
//! `m1_rtrb`, whose root definition/locked CI belongs to M0.
//! No unsafe SPSC or chunk API is implemented by M1.
#![forbid(unsafe_code)]
pub(crate) use super::{TxKind,wake};

#[cfg(feature="m1_rtrb")]
#[path="directional_rtrb.rs"]
mod selected;
#[cfg(not(feature="m1_rtrb"))]
#[path="directional_compat.rs"]
mod selected;

pub use selected::*;

#[cfg(test)]
mod pinned_rtrb_overlay_proof {
    /// Exact M0-owned shared manifest graph (H114), not a worker root edit.
    const M0_SHARED: &str = "789aa27d039fa64183d4b06d2f0acd4868bfc544";
    #[test]
    fn r1_direction_m0_pinned_rtrb_overlay_source_exact_native_ci() {
        if std::env::var("GITHUB_ACTIONS").as_deref()!=Ok("true"){
            return; // local/offline only compatibility; no rtrb qualification
        }
        if std::env::var_os("M1_RTRB_OVERLAY_CHILD").is_some(){
            return;
        }
        let script=r#"set -euo pipefail
SOURCE="$(git rev-parse HEAD)"
test "$SOURCE" = "$GITHUB_SHA"
MAIN="$M1_PINNED_MAIN"
dir="$(mktemp -d /tmp/m1-rtrb-pinned-XXXXXXXX)"
trap 'rm -rf "$dir"' EXIT
git archive HEAD | tar -xf - -C "$dir"
git fetch -q --no-tags --depth=1 origin "$MAIN"
for p in Cargo.toml Cargo.lock crates/wbd-engine/Cargo.toml crates/wbd-codec/Cargo.toml; do
    git show "$MAIN:$p" > "$dir/$p"
done
while IFS= read -r p; do
    mkdir -p "$dir/$(dirname "$p")"
    git show "$MAIN:$p" > "$dir/$p"
done < <(git ls-tree -r --name-only "$MAIN" -- native/isal-safe)
python3 - "$dir/crates/wbd-engine/Cargo.toml" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1])
s=p.read_text()
assert "rtrb = { workspace = true }" in s
assert "m1_rtrb" not in s
assert "[features]" in s
s=s.replace("[features]\n","[features]\nm1_rtrb = []\n",1)
p.write_text(s)
PY
grep -q 'name = "rtrb"' "$dir/Cargo.lock"
grep -q 'version = "0.3.2"' "$dir/Cargo.lock"
cd "$dir"
export M1_RTRB_OVERLAY_CHILD=1
export CARGO_TARGET_DIR="$dir/target"
timeout 75s cargo +1.85.1 test --locked -p wbd-engine --lib --features m1_rtrb r1_rtrb_direction_ -- --test-threads=1 --nocapture
printf 'M1_RTRB_PINNED_NATIVE_PASS source=%s main=%s version=0.3.2 mode=safe_pop_push_only\n' "$SOURCE" "$MAIN"
"#;
        let output=std::process::Command::new("bash")
            .arg("-c").arg(script)
            .env("M1_PINNED_MAIN",M0_SHARED)
            .output()
            .expect("Actions native bash + cargo host required");
        let stdout=String::from_utf8_lossy(&output.stdout);
        let stderr=String::from_utf8_lossy(&output.stderr);
        assert!(output.status.success(),
            "M1_rtrb_overlay_failed exit={:?}\nSTDOUT:\n{}\nSTDERR:\n{}",
            output.status,stdout,stderr);
        assert!(stdout.contains("M1_RTRB_PINNED_NATIVE_PASS"),
            "missing true-rtrb success receipt: {}",stdout);
        assert!(stdout.contains("5 passed; 0 failed"),
            "five actually compiled and executed rtrb integration cases not seen: {}",stdout);
        println!("{}",stdout);
        println!("M1_RTRB_OVERLAY_ATTESTED main={} exact-worker-source={}",
            M0_SHARED,std::env::var("GITHUB_SHA").unwrap_or_default());
    }
}
