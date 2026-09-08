import { useState, useEffect, useRef, useCallback } from 'react';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface SystemMemory {
  total_mb: number;
  used_mb: number;
  percent: number;
}

export interface SystemBattery {
  has_battery: boolean;
  percent: number | null;
  is_charging: boolean;
  status: string;
}

export interface SystemNetwork {
  mac_address: string;
  interface: string;
}

export interface SystemInfo {
  type: 'system_info';
  hostname: string;
  os: string;
  platform: 'linux' | 'windows';
  compositor: string;
  uptime_seconds: number;
  memory: SystemMemory;
  battery: SystemBattery;
  network: SystemNetwork;
  version: string;
}

export interface PowerEvent {
  type: 'power_event';
  action: 'hibernate' | 'power_off' | 'restart' | 'sleep' | 'lock';
  status: 'triggered';
  message: string;
  timestamp: number;
}

export type PowerCommand =
  | 'power_off'
  | 'restart'
  | 'sleep'
  | 'hibernate'
  | 'lock'
  | 'volume_up'
  | 'volume_down'
  | 'volume_mute'
  | 'get_sarvam_key'
  | 'get_system_info'
  | 'screenshot';

/** Manages the mobile app's authenticated WebSocket connection to a Blinky host. */
export function usePCWebSocket() {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [latestResponse, setLatestResponse] = useState<any>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [latestPowerEvent, setLatestPowerEvent] = useState<PowerEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
    setErrorMsg(null);
    setLatestResponse(null);
  }, []);

  /** Sends a host command when the WebSocket connection is ready. */
  const sendCommand = useCallback((command: PowerCommand | string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(command);
      return true;
    }
    return false;
  }, []);

  /** Requests a fresh telemetry snapshot from the connected host. */
  const fetchSystemInfo = useCallback(() => {
    return sendCommand('get_system_info');
  }, [sendCommand]);

  /** Opens a WebSocket connection and authenticates it when a token is provided. */
  const connect = useCallback((ipAddress: string, token?: string) => {
    disconnect();
    
    // Clean IP Address and default to port 9001 if no port is specified
    let formattedIp = ipAddress
      .trim()
      .replace(/^https?:\/\//i, '')
      .replace(/^wss?:\/\//i, '')
      .replace(/\/+$/, '');

    if (!formattedIp) {
      setStatus('error');
      setErrorMsg('IP Address cannot be empty');
      return;
    }

    if (!formattedIp.includes(':')) {
      formattedIp = `${formattedIp}:9001`;
    }

    const wsUrl = `ws://${formattedIp}`;
    setStatus('connecting');
    setErrorMsg(null);

    let connectTimeout: any = null;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      connectTimeout = setTimeout(() => {
        if (wsRef.current === ws && ws.readyState !== WebSocket.OPEN) {
          try { ws.close(); } catch (e) {}
          wsRef.current = null;
          setStatus('error');
          setErrorMsg(`Connection timed out (${formattedIp}). Ensure Blinky desktop app is running and port 9001 is open.`);
        }
      }, 5000);

      ws.onopen = () => {
        if (connectTimeout) clearTimeout(connectTimeout);
        if (wsRef.current === ws) {
          // Authenticate the remote connection before any commands are sent.
          // The desktop gateway denies all commands from non-loopback peers
          // unless the BLINKY_REMOTE_TOKEN is presented.
          if (token && token.trim()) {
            ws.send(`auth:${token.trim()}`);
          }
          setStatus('connected');
          setErrorMsg(null);

          // Request initial telemetry upon connection
          setTimeout(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send('get_system_info');
            }
          }, 300);
        }
      };

      ws.onmessage = (e) => {
        if (wsRef.current === ws) {
          try {
            const parsed = JSON.parse(e.data);
            if (parsed.type === 'system_info') {
              setSystemInfo(parsed as SystemInfo);
            } else if (parsed.type === 'power_event') {
              setLatestPowerEvent(parsed as PowerEvent);
            } else {
              setLatestResponse(parsed);
            }
          } catch (err) {
            console.log('Received raw websocket message:', e.data);
          }
        }
      };

      ws.onclose = (e) => {
        if (connectTimeout) clearTimeout(connectTimeout);
        if (wsRef.current === ws) {
          setStatus('disconnected');
          wsRef.current = null;
        }
      };

      ws.onerror = (e) => {
        if (connectTimeout) clearTimeout(connectTimeout);
        if (wsRef.current === ws) {
          setStatus('error');
          setErrorMsg(`Failed to connect to ${formattedIp}. Check Wi-Fi & PC firewall.`);
          wsRef.current = null;
        }
      };
    } catch (err: any) {
      if (connectTimeout) clearTimeout(connectTimeout);
      setStatus('error');
      setErrorMsg(err?.message || 'WebSocket creation failed');
      wsRef.current = null;
    }
  }, [disconnect]);

  const sendQuery = useCallback((query: string, requestId: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify({ requestId, query });
      wsRef.current.send(payload);
      return true;
    }
    return false;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    status,
    errorMsg,
    latestResponse,
    systemInfo,
    latestPowerEvent,
    connect,
    disconnect,
    sendCommand,
    sendQuery,
    fetchSystemInfo,
  };
}
