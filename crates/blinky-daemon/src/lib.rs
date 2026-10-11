pub mod protocol;

// The daemon is a Linux desktop service. Keep its wire protocol available to
// the cross-platform Rust agent, but do not compile Linux compositor/input
// implementations into the Windows Tauri build.
#[cfg(target_os = "linux")]
pub mod apps;
#[cfg(target_os = "linux")]
pub mod atspi;
#[cfg(target_os = "linux")]
pub mod capture;
#[cfg(target_os = "linux")]
pub mod compositor;
#[cfg(target_os = "linux")]
pub mod coordinate;
#[cfg(target_os = "linux")]
pub mod input;
#[cfg(target_os = "linux")]
pub mod media;
#[cfg(target_os = "linux")]
pub mod server;
#[cfg(target_os = "linux")]
pub mod system;
