import subprocess
import time
import sys
import os

try:
    # Ưu tiên đọc cấu hình tập trung từ config/setting.py.
    from config.setting import SERIAL_BAUD, SERIAL_PORT
except Exception:
    SERIAL_PORT = ""
    SERIAL_BAUD = 9600

from iot.serial_comm import SerialConfig, open_serial, send_command

# Anti-spam trigger:
# - Camera sẽ bật NGAY khi có MOTION (logic "đứng yên rồi chụp" nằm trong camera.py).
# - Ở đây chỉ cần cooldown + lockout để tránh quét liên tục do cảm biến nhiễu.
CAPTURE_COOLDOWN_SECONDS = 5.0
# Lockout sau mỗi lần quét xong (không phụ thuộc Arduino có spam MOTION hay không):
# - SUCCESS: khóa lâu hơn để tránh mở cửa/quét lặp khi bạn vẫn đứng đó.
# - FAIL: khóa ngắn để thử lại nhanh.
LOCKOUT_SECONDS_SUCCESS = 20.0
LOCKOUT_SECONDS_FAIL = 3.0
# Pause rất ngắn sau khi gửi lệnh, chỉ để Serial ổn định trước khi reset buffer.
# Thời gian "mở cửa rồi đóng" nên xử lý ở Arduino (servo/relay), không nên sleep ở PC.
POST_COMMAND_PAUSE_SECONDS = 0.2


def main() -> None:
    """Lắng nghe tín hiệu chuyển động từ Arduino và gọi camera.py để xác thực."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    camera_script = os.path.join(current_dir, "camera.py")

    print("[*] He thong dang ket noi Arduino qua Serial...")
    try:
        ser = open_serial(SerialConfig(port=SERIAL_PORT, baud=SERIAL_BAUD, timeout_s=1.0))
        print(f"[+] Da ket noi Arduino tai {ser.port} (baud={SERIAL_BAUD})")
        print("[+] HE THONG SAN SANG!")
    except Exception as exc:
        print(f"[-] LOI: Khong mo duoc cong Serial. Chi tiet: {exc}")
        return

    last_capture_at = 0.0
    next_allowed_at = 0.0
    capturing = False

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()

                if line == "MOTION":
                    now = time.time()
                    if capturing:
                        continue
                    # Cooldown: chống spam chụp do cảm biến nhiễu / gửi MOTION liên tục.
                    if (now - last_capture_at) < CAPTURE_COOLDOWN_SECONDS:
                        continue
                    if now < next_allowed_at:
                        continue

                    # Bật camera ngay khi có người lại gần.
                    last_capture_at = now
                    capturing = True
                    print("\n[!] PHAT HIEN NGUOI -> Bat camera ngay...", flush=True)

                    proc = subprocess.run(
                        [sys.executable, camera_script],
                        capture_output=True,
                        text=True,
                    )

                    output = proc.stdout.strip()
                    if proc.stderr:
                        print(f"[!] Loi tu camera.py: {proc.stderr.strip()}")

                    print(f"[*] Ket qua xac thuc: {output}")

                    if "SUCCESS_FACE" in output:
                        print("[V] XAC THUC THANH CONG! Mo cua.")
                        send_command(ser, "OPEN")
                        next_allowed_at = time.time() + LOCKOUT_SECONDS_SUCCESS
                    else:
                        print("[X] XAC THUC THAT BAI! Tu choi.")
                        send_command(ser, "FAIL")
                        next_allowed_at = time.time() + LOCKOUT_SECONDS_FAIL

                    time.sleep(POST_COMMAND_PAUSE_SECONDS)
                    ser.reset_input_buffer()
                    capturing = False

            time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[*] Dung listener theo yeu cau nguoi dung.")
            break
        except Exception as exc:
            print(f"[-] Loi trong vong lap listener: {exc}")
            time.sleep(0.5)

    try:
        ser.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()