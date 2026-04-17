import serial
import subprocess
import time
import sys
import os

ARDUINO_PORT = 'COM6'
BAUD_RATE = 9600


def main() -> None:
    """Lắng nghe tín hiệu chuyển động từ Arduino và gọi camera.py để xác thực."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    camera_script = os.path.join(current_dir, "camera.py")

    print(f"[*] He thong dang ket noi Arduino tai {ARDUINO_PORT}...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        ser.reset_input_buffer()
        print("[+] HE THONG SAN SANG!")
    except Exception as exc:
        print(f"[-] LOI: Khong mo duoc cong Serial. Chi tiet: {exc}")
        return

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()

                if line == "MOTION":
                    print("\n[!] PHAT HIEN NGUOI -> Dang kich hoat Camera...")

                    # Chạy camera theo chuẩn subprocess để tách luồng rõ ràng.
                    proc = subprocess.run(
                        [sys.executable, camera_script],
                        capture_output=True,
                        text=True,
                    )

                    output = proc.stdout.strip()
                    if proc.stderr:
                        print(f"[!] Loi tu camera.py: {proc.stderr.strip()}")

                    print(f"[*] Ket qua xac thuc: {output}")

                    if "SUCCESS" in output:
                        print("[V] XAC THUC THANH CONG! Mo cua.")
                        ser.write(b"OPEN\n")
                    else:
                        print("[X] XAC THUC THAT BAI! Tu choi.")
                        ser.write(b"DENY\n")

                    time.sleep(3)
                    ser.reset_input_buffer()

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