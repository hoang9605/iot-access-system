from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import serial

try:
    # pyserial có sẵn module list_ports (Windows/Linux/macOS).
    from serial.tools import list_ports
except Exception:  # pragma: no cover
    list_ports = None


@dataclass(frozen=True)
class SerialConfig:
    """
    Cấu hình kết nối Serial đến Arduino.

    - port: ví dụ "COM6". Nếu None/"" thì sẽ auto-detect.
    - baud: phải khớp với Serial.begin(...) phía Arduino.
    """

    port: Optional[str]
    baud: int = 9600
    timeout_s: float = 1.0


def auto_detect_arduino_port() -> Optional[str]:
    """
    Tự động dò COM port cho Arduino.

    Quy tắc ưu tiên:
    - Nếu mô tả có chữ "arduino" (không phân biệt hoa thường) thì chọn đầu tiên.
    - Nếu không, trả về port đầu tiên tìm thấy (để vẫn chạy được với clone board).
    """

    if list_ports is None:
        return None

    ports = list(list_ports.comports())
    if not ports:
        return None

    for p in ports:
        desc = (p.description or "").lower()
        manu = (p.manufacturer or "").lower()
        if "arduino" in desc or "arduino" in manu:
            return p.device

    return ports[0].device


def open_serial(config: SerialConfig) -> serial.Serial:
    """
    Mở Serial theo config (có auto-detect nếu chưa set port).
    """

    port = (config.port or "").strip()
    if not port:
        port = auto_detect_arduino_port() or ""

    if not port:
        raise RuntimeError(
            "Khong tim thay COM port. Hay set SERIAL_PORT trong .env (vi du SERIAL_PORT=COM6)."
        )

    ser = serial.Serial(port, config.baud, timeout=config.timeout_s)
    # Arduino thường reset khi mở Serial; chờ 1 chút để ổn định.
    time.sleep(2)
    try:
        ser.reset_input_buffer()
    except Exception:
        pass
    return ser


def send_command(ser: serial.Serial, command: str) -> None:
    """
    Gửi 1 lệnh dạng dòng (line-based) xuống Arduino.
    Quy ước: "OPEN" hoặc "FAIL".
    """

    line = (command or "").strip()
    if not line:
        return
    ser.write((line + "\n").encode("utf-8"))

