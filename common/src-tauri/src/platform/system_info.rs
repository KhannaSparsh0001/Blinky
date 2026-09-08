use serde_json::{json, Value};
#[cfg(target_os = "linux")]
use std::fs;
#[cfg(target_os = "linux")]
use std::path::Path;

/// Collects host identity, uptime, memory, battery, and network telemetry.
pub fn get_system_telemetry() -> Value {
    #[cfg(target_os = "linux")]
    {
        // 1. Hostname (RFC 1123 host)
        let hostname = fs::read_to_string("/etc/hostname")
            .map(|s| s.trim().to_string())
            .unwrap_or_else(|_| std::env::var("HOSTNAME").unwrap_or_else(|_| "Blinky-Host".to_string()));

        // 2. OS Name — freedesktop.org standard (/etc/os-release, fallback /usr/lib/os-release)
        let os_name = fs::read_to_string("/etc/os-release")
            .or_else(|_| fs::read_to_string("/usr/lib/os-release"))
            .ok()
            .and_then(|content| {
                for line in content.lines() {
                    if line.starts_with("PRETTY_NAME=") {
                        let val = line.trim_start_matches("PRETTY_NAME=").trim_matches('"');
                        return Some(val.to_string());
                    }
                }
                None
            })
            .unwrap_or_else(|| "Linux".to_string());

        // 3. Desktop / Compositor (Hyprland, Sway, KDE Plasma, GNOME, XFCE, etc.)
        let desktop = std::env::var("XDG_CURRENT_DESKTOP")
            .or_else(|_| std::env::var("DESKTOP_SESSION"))
            .or_else(|_| std::env::var("XDG_SESSION_DESKTOP"))
            .unwrap_or_else(|_| "Desktop".to_string());
        let session_type = std::env::var("XDG_SESSION_TYPE").unwrap_or_default();
        let compositor = if !session_type.is_empty() {
            format!("{} ({})", desktop, session_type)
        } else {
            desktop
        };

        // 4. System Uptime from /proc/uptime (standard on all Linux kernels)
        let uptime_seconds = fs::read_to_string("/proc/uptime")
            .ok()
            .and_then(|content| {
                content
                    .split_whitespace()
                    .next()
                    .and_then(|s| s.parse::<f64>().ok())
                    .map(|f| f as u64)
            })
            .unwrap_or(0);

        // 5. Memory statistics from /proc/meminfo
        let (total_mb, used_mb, mem_percent) = fs::read_to_string("/proc/meminfo")
            .ok()
            .and_then(|content| {
                let mut total_kb = 0u64;
                let mut avail_kb = 0u64;
                for line in content.lines() {
                    if line.starts_with("MemTotal:") {
                        total_kb = parse_meminfo_kb(line);
                    } else if line.starts_with("MemAvailable:") {
                        avail_kb = parse_meminfo_kb(line);
                    }
                }
                if total_kb > 0 {
                    let used_kb = total_kb.saturating_sub(avail_kb);
                    let percent = ((used_kb as f64 / total_kb as f64) * 100.0) as u32;
                    Some((total_kb / 1024, used_kb / 1024, percent))
                } else {
                    None
                }
            })
            .unwrap_or((0, 0, 0));

        let battery = read_linux_battery();
        let network = read_linux_network();

        json!({
            "type": "system_info",
            "hostname": hostname,
            "os": os_name,
            "platform": "linux",
            "compositor": compositor,
            "uptime_seconds": uptime_seconds,
            "memory": {
                "total_mb": total_mb,
                "used_mb": used_mb,
                "percent": mem_percent
            },
            "battery": battery,
            "network": network,
            "version": "0.1.0"
        })
    }

    #[cfg(target_os = "windows")]
    {
        let hostname = std::env::var("COMPUTERNAME").unwrap_or_else(|_| "Windows-PC".to_string());
        let (os_name, total_mb, used_mb, mem_percent, uptime_seconds, battery, network) = read_windows_telemetry();

        json!({
            "type": "system_info",
            "hostname": hostname,
            "os": os_name,
            "platform": "windows",
            "compositor": "Windows Desktop (DWM)",
            "uptime_seconds": uptime_seconds,
            "memory": {
                "total_mb": total_mb,
                "used_mb": used_mb,
                "percent": mem_percent
            },
            "battery": battery,
            "network": network,
            "version": "0.1.0"
        })
    }
}

/// Parses a `/proc/meminfo` value expressed in kilobytes.
#[cfg(target_os = "linux")]
fn parse_meminfo_kb(line: &str) -> u64 {
    line.split_whitespace()
        .nth(1)
        .and_then(|s| s.parse::<u64>().ok())
        .unwrap_or(0)
}

/// Reads battery capacity and charging state from Linux sysfs.
#[cfg(target_os = "linux")]
fn read_linux_battery() -> Value {
    let power_path = Path::new("/sys/class/power_supply");
    if let Ok(entries) = fs::read_dir(power_path) {
        for entry in entries.flatten() {
            let p = entry.path();
            let p_type = fs::read_to_string(p.join("type")).unwrap_or_default();
            if p_type.trim().eq_ignore_ascii_case("battery") || entry.file_name().to_string_lossy().starts_with("BAT") {
                let capacity = fs::read_to_string(p.join("capacity"))
                    .ok()
                    .and_then(|c| c.trim().parse::<u32>().ok());
                let status = fs::read_to_string(p.join("status"))
                    .map(|s| s.trim().to_string())
                    .unwrap_or_else(|_| "Unknown".to_string());
                let is_charging = status.eq_ignore_ascii_case("charging");
                return json!({
                    "has_battery": true,
                    "percent": capacity,
                    "is_charging": is_charging,
                    "status": status
                });
            }
        }
    }

    json!({
        "has_battery": false,
        "percent": null,
        "is_charging": false,
        "status": "AC Mains Nominal"
    })
}

/// Selects an active physical network interface and reports its MAC address.
#[cfg(target_os = "linux")]
fn read_linux_network() -> Value {
    let net_path = Path::new("/sys/class/net");
    let mut best_mac = String::new();
    let mut best_iface = String::new();

    if let Ok(entries) = fs::read_dir(net_path) {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();
            if name == "lo" || name.starts_with("docker") || name.starts_with("veth") || name.starts_with("br-") || name.starts_with("tailscale") {
                continue;
            }

            let p = entry.path();
            let mac = fs::read_to_string(p.join("address")).unwrap_or_default().trim().to_string();
            let oper = fs::read_to_string(p.join("operstate")).unwrap_or_default().trim().to_string();

            if !mac.is_empty() && mac != "00:00:00:00:00:00" {
                if oper == "up" || best_mac.is_empty() {
                    best_mac = mac;
                    best_iface = name;
                    if oper == "up" {
                        break;
                    }
                }
            }
        }
    }

    json!({
        "mac_address": best_mac,
        "interface": best_iface
    })
}

/// Returns the currently supported Windows telemetry fields and defaults.
#[cfg(target_os = "windows")]
fn read_windows_telemetry() -> (String, u64, u64, u32, u64, Value, Value) {
    // Standard Windows fallback defaults
    let os_name = "Windows".to_string();
    let total_mb = 0u64;
    let used_mb = 0u64;
    let mem_percent = 0u32;
    let uptime_seconds = 0u64;

    let battery = json!({
        "has_battery": false,
        "percent": null,
        "is_charging": false,
        "status": "AC Mains Nominal"
    });

    let network = json!({
        "mac_address": "",
        "interface": ""
    });

    (os_name, total_mb, used_mb, mem_percent, uptime_seconds, battery, network)
}
