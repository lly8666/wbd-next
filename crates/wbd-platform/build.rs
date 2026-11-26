use std::{env,path::PathBuf,process::Command};
fn main(){
    println!("cargo:rerun-if-changed=native/winxdp_tx.cpp");
    println!("cargo:rerun-if-env-changed=WBD_XDP_SDK_INCLUDE");
    if env::var_os("CARGO_FEATURE_WINXDP_TX_TRIAL").is_none()||
       env::var("CARGO_CFG_TARGET_OS").as_deref()!=Ok("windows"){return}
    assert_eq!(env::var("CARGO_CFG_TARGET_ENV").as_deref(),Ok("msvc"));
    let sdk=env::var("WBD_XDP_SDK_INCLUDE").expect("official XDP SDK include path");
    let out=PathBuf::from(env::var_os("OUT_DIR").unwrap());
    let object=out.join("wbd_xdp_tx.obj");
    let library=out.join("wbd_xdp_tx.lib");
    let ok=Command::new("cl.exe").args(["/nologo","/c","/O2","/MD","/std:c++17"])
        .arg(format!("/I{sdk}")).arg(format!("/Fo{}",object.display()))
        .arg("native/winxdp_tx.cpp").status().expect("MSVC developer environment");
    assert!(ok.success(),"XDP SDK shim build");
    let ok=Command::new("lib.exe").arg("/nologo")
        .arg(format!("/OUT:{}",library.display())).arg(object)
        .status().expect("MSVC lib");
    assert!(ok.success(),"XDP SDK shim archive");
    println!("cargo:rustc-link-search=native={}",out.display());
    for l in ["ntdll","onecore","iphlpapi","ws2_32"]{println!("cargo:rustc-link-lib={l}")}
    println!("cargo:rustc-link-lib=static=wbd_xdp_tx");
}
