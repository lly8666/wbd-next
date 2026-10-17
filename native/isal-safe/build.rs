use std::{env,path::PathBuf};
fn main(){
 println!("cargo:rerun-if-env-changed=WBD_ISAL_PREFIX");
 if env::var_os("CARGO_FEATURE_NATIVE").is_none(){return;}
 assert_eq!(env::var("TARGET").unwrap(),"x86_64-unknown-linux-gnu",
            "native ISA-L unsupported platform");
 let prefix=PathBuf::from(env::var_os("WBD_ISAL_PREFIX")
                      .expect("pinned ISA-L prefix missing"));
 assert!(prefix.join("lib/libisal.a").is_file(),"missing pinned libisal.a");
 println!("cargo:rustc-link-search=native={}",prefix.join("lib").display());
 println!("cargo:rustc-link-lib=static=isal");
}
