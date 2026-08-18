"""
รันสคริปต์นี้บนเครื่องคอมพิวเตอร์ของคุณเอง (ไม่ใช่บน Streamlit Cloud) เพียงครั้งเดียว
เพื่อขอ refresh token สำหรับบัญชี Gmail ที่เป็นเจ้าของโฟลเดอร์ Google Drive

ก่อนรัน:
  1) pip install google-auth-oauthlib
  2) วางไฟล์ client_secret.json (ที่ดาวน์โหลดจาก Google Cloud Console) ไว้โฟลเดอร์เดียวกับสคริปต์นี้
  3) รันคำสั่ง: python get_refresh_token.py
  4) เบราว์เซอร์จะเปิดขึ้นมา ให้ล็อกอินด้วย Gmail ที่เป็นเจ้าของโฟลเดอร์ Drive นั้น
     (ถ้าเจอหน้าเตือน "Google hasn't verified this app" ให้กด Advanced > Go to app (unsafe)
     เพราะเป็นแอปที่คุณสร้างเอง ปลอดภัยสำหรับตัวคุณ)
  5) หลังอนุญาตสิทธิ์แล้ว ค่าที่ต้องการจะพิมพ์ออกมาในเทอร์มินัล
     ให้คัดลอกค่าทั้ง 3 ตัวไปใส่ใน Streamlit secrets (ดูตัวอย่างท้ายไฟล์)
"""

from google_auth_oauthlib.flow import InstalledAppFlow

# ต้องเป็น scope เดียวกับที่แอปใช้อัปโหลดไฟล์
SCOPES = ["https://www.googleapis.com/auth/drive"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("คัดลอกค่าด้านล่างนี้ไปใส่ใน Streamlit secrets.toml")
    print("=" * 60)
    print(f"""
[gdrive_oauth]
client_id = "{creds.client_id}"
client_secret = "{creds.client_secret}"
refresh_token = "{creds.refresh_token}"
""")
    print("=" * 60)
    print("⚠️  เก็บค่าเหล่านี้เป็นความลับ ห้าม commit ลง git หรือแชร์ให้ผู้อื่น")

if __name__ == "__main__":
    main()
