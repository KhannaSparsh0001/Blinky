use std::process::Command;

pub fn execute_power_off() {
    if let Err(e) = Command::new("shutdown").args(&["/s", "/t", "0"]).spawn() {
        eprintln!("Failed to execute Windows shutdown: {:?}", e);
    }
}

pub fn execute_restart() {
    if let Err(e) = Command::new("shutdown").args(&["/r", "/t", "0"]).spawn() {
        eprintln!("Failed to execute Windows restart: {:?}", e);
    }
}

pub fn execute_sleep() {
    if let Err(e) = Command::new("rundll32.exe")
        .args(&["powrprof.dll,SetSuspendState", "0", "1", "0"])
        .spawn()
    {
        eprintln!("Failed to execute Windows sleep: {:?}", e);
    }
}

pub fn execute_lock() {
    if let Err(e) = Command::new("rundll32.exe")
        .args(&["user32.dll,LockWorkStation"])
        .spawn()
    {
        eprintln!("Failed to execute Windows lock: {:?}", e);
    }
}

pub fn execute_screenshot() {
    if let Err(e) = Command::new("snippingtool")
        .arg("/clip")
        .spawn()
    {
        eprintln!("Failed to execute Windows screenshot: {:?}", e);
    }
}

