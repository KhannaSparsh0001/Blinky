use std::process::Command;

pub fn execute_power_off() {
    if let Err(e) = Command::new("systemctl").arg("poweroff").spawn() {
        eprintln!("Failed to execute Linux/Unix poweroff: {:?}", e);
    }
}

pub fn execute_restart() {
    if let Err(e) = Command::new("systemctl").arg("reboot").spawn() {
        eprintln!("Failed to execute Linux/Unix reboot: {:?}", e);
    }
}

pub fn execute_sleep() {
    if let Err(e) = Command::new("systemctl").arg("suspend").spawn() {
        eprintln!("Failed to execute Linux/Unix suspend: {:?}", e);
    }
}

pub fn execute_volume_up() {
    let _ = Command::new("amixer").args(&["sset", "Master", "5%+"]).spawn();
    let _ = Command::new("pactl").args(&["set-sink-volume", "@DEFAULT_SINK@", "+5%"]).spawn();
}

pub fn execute_volume_down() {
    let _ = Command::new("amixer").args(&["sset", "Master", "5%-"]).spawn();
    let _ = Command::new("pactl").args(&["set-sink-volume", "@DEFAULT_SINK@", "-5%"]).spawn();
}

pub fn execute_volume_mute() {
    let _ = Command::new("amixer").args(&["sset", "Master", "toggle"]).spawn();
    let _ = Command::new("pactl").args(&["set-sink-mute", "@DEFAULT_SINK@", "toggle"]).spawn();
}

pub fn execute_lock() {
    let _ = Command::new("xdg-screensaver").arg("lock").spawn();
    let _ = Command::new("gnome-screensaver-command").arg("-l").spawn();
    let _ = Command::new("loginctl").args(&["lock-session"]).spawn();
}

pub fn execute_screenshot() {
    let _ = Command::new("gnome-screenshot").arg("-i").spawn();
    let _ = Command::new("spectacle").spawn();
    let _ = Command::new("xfce4-screenshooter").spawn();
}

