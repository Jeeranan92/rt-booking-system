# 🏥 ระบบยืม-คืนอุปกรณ์ ภาควิชารังสีเทคนิค
## คู่มือติดตั้งและเผยแพร่ใน Network มหาวิทยาลัย

---

## ขั้นตอนที่ 1 — สร้าง Google Sheets (ทำครั้งเดียว)

### 1.1 สร้าง Google Cloud Project
1. ไปที่ https://console.cloud.google.com
2. กด **"New Project"** → ตั้งชื่อ เช่น `RT-Borrow-System`
3. เปิดใช้งาน API:
   - ค้นหา **"Google Sheets API"** → Enable
   - ค้นหา **"Google Drive API"** → Enable

### 1.2 สร้าง Service Account
1. ไปที่ **IAM & Admin → Service Accounts**
2. กด **"Create Service Account"**
3. ตั้งชื่อ เช่น `rt-borrow-bot`
4. กด **"Create and Continue"** → **"Done"**
5. คลิก Service Account ที่สร้าง → แท็บ **"Keys"**
6. กด **"Add Key" → "Create new key" → JSON**
7. ดาวน์โหลดไฟล์ → **เปลี่ยนชื่อเป็น `credentials.json`**
8. วางไฟล์ในโฟลเดอร์เดียวกับ `app.py`

### 1.3 สร้าง Google Sheet
1. ไปที่ https://sheets.google.com → สร้าง Sheet ใหม่
2. ตั้งชื่อ เช่น `RT Borrow System`
3. กด **Share** → วาง email ของ Service Account (ดูจากไฟล์ credentials.json ที่ field `client_email`)
4. ให้สิทธิ์ **Editor** → Send
5. Copy **Sheet ID** จาก URL:
   ```
   https://docs.google.com/spreadsheets/d/[SHEET_ID_HERE]/edit
   ```

### 1.4 ใส่ Sheet ID ในโค้ด
เปิด `app.py` แก้บรรทัดนี้:
```python
SHEET_ID = "YOUR_GOOGLE_SHEET_ID_HERE"
```
เปลี่ยนเป็น Sheet ID ที่ copy มา เช่น:
```python
SHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
```

---

## ขั้นตอนที่ 2 — ติดตั้งในเครื่อง Server/PC

```bash
# ติดตั้ง Python packages
pip install -r requirements.txt

# รัน app (เข้าถึงได้จากทุกเครื่องใน Network)
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

**เครื่องอื่นใน Network เข้าผ่าน:**
```
http://[IP-เครื่อง-Server]:8501
```

หา IP เครื่อง Server:
- Windows: `ipconfig` → ดู IPv4 Address
- เช่น `http://192.168.1.100:8501`

---

## ขั้นตอนที่ 3 — รันอัตโนมัติตอน Windows เปิด (ไม่ต้องรันทุกครั้ง)

สร้างไฟล์ `start_app.bat`:
```bat
@echo off
cd /d "C:\Users\adminnistrator\Downloads\reservation"
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

วางใน **Startup folder**: กด `Win+R` → พิมพ์ `shell:startup` → วางไฟล์ .bat ที่นั่น

---

## โครงสร้างไฟล์ที่ต้องมี

```
reservation/
├── app.py                 ← โค้ดหลัก
├── requirements.txt       ← dependencies
├── credentials.json       ← Google Service Account key (อย่า share ไฟล์นี้!)
├── RT CMU Logo.png        ← โลโก้ (ถ้ามี)
├── bookings.json          ← backup ข้อมูล (สร้างอัตโนมัติ)
└── booking_images/        ← รูปภาพ (สร้างอัตโนมัติ)
```

---

## ⚠️ หมายเหตุสำคัญ

- **`credentials.json`** คือกุญแจ Google Account อย่า upload ขึ้น GitHub หรือแชร์ให้ใคร
- ข้อมูลบันทึกทั้งใน **Google Sheets** (หลัก) และ **bookings.json** (สำรอง)
- รูปภาพยังเก็บในเครื่อง Server ที่ `booking_images/`
- ถ้าต้องการ backup รูปภาพ ให้ copy folder `booking_images/` ไว้ด้วย

---

## แก้ปัญหาที่พบบ่อย

| ปัญหา | วิธีแก้ |
|-------|---------|
| เข้าจากเครื่องอื่นไม่ได้ | ตรวจสอบ Firewall → Allow port 8501 |
| Sheets ไม่อัปเดต | ตรวจสอบว่า Share Sheet ให้ Service Account แล้ว |
| credentials.json ไม่เจอ | ตรวจสอบ path และชื่อไฟล์ |
