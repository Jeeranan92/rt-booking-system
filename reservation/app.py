import streamlit as st
import json
import os
from datetime import datetime, date, timedelta, time as dt_time, timezone as dt_timezone
import calendar
import uuid
import pandas as pd
import io
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

# ─── Google Sheets setup ──────────────────────────────────────────────────────
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

SHEET_ID = "1yWLwkCDuagzpBajvphTtSD9i_MiunH20aUO_slOPD9g"
DRIVE_FOLDER_ID = "1_6qt0qapzAZFqscbEudSiB0s2zuiDe39"

COLUMNS = ["id","name","phone_id","user_status","purpose","item","item_type",
           "quantity","start_date","end_date","slot","borrow_time","return_time","status",
           "borrow_image","return_image","notes"]

@st.cache_resource(show_spinner=False)
def get_sheet():
    if not GSHEETS_AVAILABLE:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.sheet1
        if ws.row_count == 0 or ws.cell(1,1).value != "id":
            ws.insert_row(COLUMNS, 1)
        return ws
    except Exception as e:
        st.warning(f"Google Sheets: {e}")
        return None
@st.cache_resource(show_spinner=False)
def get_drive_service():
    if not GDRIVE_AVAILABLE:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.warning(f"Google Drive: {e}")
        return None
        
def _use_gsheets():
    return GSHEETS_AVAILABLE and get_sheet() is not None

def _load_icon():
    from PIL import Image as _Img
    _candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "RT CMU Logo.ico"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "RT CMU Logo.png"),
    ]
    for _p in _candidates:
        if os.path.exists(_p):
            try:
                return _Img.open(_p)
            except Exception:
                pass
    return "🏥"

st.set_page_config(
    page_title="ระบบการจองห้องปฏิบัติการ และการยืม-คืนเครื่องมือ และอุปกรณ์ ภาควิชารังสีเทคนิค",
    page_icon=_load_icon(),
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_date_range(b):
    start = b.get("start_date") or b.get("date")
    end   = b.get("end_date")   or b.get("date")
    return start, end

def to_date(d):
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    return d

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&family=Prompt:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
.main-header {
    background: linear-gradient(135deg, #0d2137 0%, #1565c0 55%, #0288d1 100%);
    padding: 1.8rem 2.5rem; border-radius: 18px; color: white;
    margin-bottom: 1.5rem; box-shadow: 0 8px 32px rgba(13,110,253,0.22);
    display: flex; align-items: center; gap: 1.5rem;
}
.main-header h1 { font-family:'Prompt'; font-size:1.7rem; font-weight:800; margin:0; }
.main-header p  { margin:0; opacity:.85; font-size:.9rem; }
.stat-card {
    background:white; border-radius:14px; padding:1.2rem 1.5rem;
    box-shadow:0 2px 14px rgba(0,0,0,.08); border-left:5px solid #1565c0; margin-bottom:1rem;
}
.stat-card.orange { border-left-color:#ef6c00; }
.stat-card.green  { border-left-color:#2e7d32; }
.stat-card.red    { border-left-color:#c62828; }
.stat-card h3 { margin:0; font-size:2rem; font-weight:800; color:#0d2137; }
.stat-card p  { margin:0; color:#607d8b; font-size:.82rem; margin-top:2px; }
.sec-title {
    font-family:'Prompt'; font-size:1.05rem; font-weight:700; color:#0d2137;
    padding:.4rem 0; border-bottom:2.5px solid #e3eaf5; margin-bottom:1rem;
}
.slot-pill { display:inline-block; padding:3px 10px; border-radius:20px; font-size:.72rem; font-weight:700; letter-spacing:.3px; }
.pill-booked   { background:#fde8e8; color:#c62828; border:1px solid #ffcdd2; }
.pill-returned { background:#e3f2fd; color:#1565c0; border:1px solid #bbdefb; }
.hour-box { text-align:center; border-radius:8px; padding:6px 2px; font-size:.7rem; font-weight:700; line-height:1.4; }
.hour-free  { background:#e8f5e9; color:#2e7d32; border:1.5px solid #a5d6a7; }
.hour-taken { background:#fde8e8; color:#c62828; border:1.5px solid #ef9a9a; }
.cal-wrap { overflow-x:auto; margin-top:.5rem; }
.cal-table { width:100%; border-collapse:separate; border-spacing:4px; table-layout:fixed; }
.cal-th { text-align:center; padding:8px 4px; font-weight:700; font-size:.85rem; color:#546e7a; background:#f0f4f8; border-radius:6px; }
.cal-th.cal-sun { color:#c62828; }
.cal-td { border-radius:10px; padding:6px 4px; min-height:70px; background:#f8fafc; vertical-align:top; text-align:center; border:1.5px solid transparent; }
.cal-today { background:#e3f2fd !important; border-color:#1565c0 !important; }
.cal-has   { background:#fff8e1 !important; }
.cal-empty { background:transparent !important; }
.cal-daynum { font-weight:700; font-size:.9rem; color:#263238; }
.cal-daynum-sun { color:#c62828; }
.cal-dot { width:7px; height:7px; border-radius:50%; display:inline-block; margin:1px; }
.sum-table { width:100%; border-collapse:collapse; font-size:.83rem; }
.sum-table th { background:#0d2137; color:white; padding:9px 12px; text-align:center; white-space:nowrap; }
.sum-table td { padding:7px 10px; border-bottom:1px solid #eceff1; }
.sum-table tr:nth-child(even) td { background:#f5f7fa; }
.sum-table tr:hover td { background:#e3f0ff; }
/* ปฏิทินแบบปุ่มคลิกได้ */
.cal-cell-marker + div .stButton > button {
    background: #f8fafc !important;
    border: 1.5px solid #e3eaf5 !important;
    border-radius: 10px !important;
    min-height: 64px;
    white-space: pre-line;
    line-height: 1.5;
    color: #263238 !important;
    font-weight: 700;
    font-size: .95rem;
    padding: 6px 2px !important;
}
.cal-cell-marker.cal-has + div .stButton > button {
    background: #fff8e1 !important;
    border-color: #ffe082 !important;
}
.cal-cell-marker.cal-today + div .stButton > button {
    background: #e3f2fd !important;
    border-color: #1565c0 !important;
    color: #0d2137 !important;
}
.cal-cell-marker + div .stButton > button:hover {
    border-color: #1565c0 !important;
    color: #1565c0 !important;
}
.cal-count-line {
    font-size: .68rem;
    font-weight: 600;
    color: #ef6c00;
}
/* ปฏิทินจองอาจารย์สอบ Oral */
.oe-free + div .stButton > button { background:#e8f5e9 !important; border-color:#a5d6a7 !important; }
.oe-part + div .stButton > button { background:#fff8e1 !important; border-color:#ffe082 !important; }
.oe-full + div .stButton > button { background:#fde8e8 !important; border-color:#ef9a9a !important; color:#c62828 !important; }
.oe-off + div .stButton > button  { background:#eceff1 !important; border-color:#cfd8dc !important; color:#90a4ae !important; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
DATA_FILE  = "bookings.json"
IMAGES_DIR = "booking_images"
ADMIN_PIN  = "2101"   # รหัสแอดมิน: ใช้ลบ/ยกเลิก/คืนด่วนทุกประเภทการจอง
os.makedirs(IMAGES_DIR, exist_ok=True)

EQUIPMENT_LIST = [
    "IC and Solid state box set : Radcal","OSL reader: microStar","MCA : NaI(Te)",
    "SCA พร้อม หัววัด NaI(Te)","Computer : HP","Computer : ASUS","Computer : Lenovo",
    "Computer : Acer","Parallel plate","Digital caliper",
    "เครื่องวัดรังสี Digital (neutron) LUDLUM","Survey meter/Geiger muller แบบเข็ม LUDLUM",
    "Survey meter แบบเข็ม สทน.","Survey meter/Geiger muller แบบdigital : LUDLUM",
    "Digital barometer - วัดอุณหภูมิ ความดัน","Build up cap(high energy)","IC แบบ cylindrical",
    "Pocket dose meter","ชุดหัววัด Cd-Te","แผ่น DR","แผ่น CR ใหญ่","แผ่น CR เล็ก","HVL",
    "ขาตั้งกล้อง","แผ่น filter : Pb AL Cu","View box","Roll up","Backdrop","อื่นๆ",
]

ROOMS_LIST = [
    "ห้องปฏิบัติการ CT Scan","ห้องปฏิบัติการ X-Ray : Shimadzu",
    "ห้องปฏิบัติการ X-Ray : DRGem","ห้องปฏิบัติการ X-Ray : นวัตกรรม",
    "ห้องปฏิบัติการ Fluoroscopy : Philips","ห้องปฏิบัติการ US (อัลตราซาวด์)",
    "ห้องปฏิบัติการคอมพิวเตอร์","ห้องบรรยาย2 อาคาร3 ชั้น1","ห้องตรวจมวลกระดูก BMD : HOLOGIC",
]
# ─── วิทยาเขต ──────────────────────────────────────────────────────────────────
CAMPUSES = ["ภาควิชารังสีเทคนิค", "ศูนย์การศึกษาฯ หริภุญไชย"]

HARIPHUNCHAI_ROOMS = [
    "X-Ray : Shimadzu (ศบบ)",
    "XRF (ศบบ)",
    "HPGe (ศบบ)",
]

ALL_ROOMS = ROOMS_LIST + HARIPHUNCHAI_ROOMS

STATUS_OPTIONS = [
    "อาจารย์ประจำภาควิชารังสีเทคนิค","บุคลากรประจำภาควิชารังสีเทคนิค",
    "นักศึกษารังสีเทคนิค ชั้นปีที่ 1","นักศึกษารังสีเทคนิค ชั้นปีที่ 2",
    "นักศึกษารังสีเทคนิค ชั้นปีที่ 3","นักศึกษารังสีเทคนิค ชั้นปีที่ 4",
    "บุคลากรภายนอก สังกัดคณะเทคนิคการแพทย์","บุคลากรภายนอก สังกัดอื่นๆ",
]

ALL_STARTS = ["08:30","09:00","09:30","10:00","10:30","11:00","11:30",
              "12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00"]

ALL_ENDS   = ["09:00","09:30","10:00","10:30","11:00","11:30","12:00",
              "12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00","16:30"]
TIME_SLOTS = [f"{s}–{e}" for s, e in zip(ALL_STARTS, ALL_ENDS)]
TIME_SLOTS = list(dict.fromkeys(TIME_SLOTS))

MONTH_TH = ["","มกราคม","กุมภาพันธ์","มีนาคม","เมษายน",
            "พฤษภาคม","มิถุนายน","กรกฎาคม","สิงหาคม",
            "กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]

# ─── Data helpers ─────────────────────────────────────────────────────────────
def load_bookings():
    if _use_gsheets():
        try:
            ws = get_sheet()
            if ws:
                rows = ws.get_all_records()
                for r in rows:
                    r["quantity"] = int(r.get("quantity", 1) or 1)
                    if r.get("return_time") == "": r["return_time"] = None
                    if r.get("borrow_image") == "": r["borrow_image"] = None
                    if r.get("return_image") == "": r["return_image"] = None
                    if not r.get("start_date") and r.get("date"):
                        r["start_date"] = r["date"]
                    if not r.get("end_date") and r.get("date"):
                        r["end_date"] = r["date"]
                return rows
        except Exception as e:
            st.warning(f"โหลดจาก Sheets ไม่ได้: {e}")
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_bookings(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_one_booking(b):
    if _use_gsheets():
        try:
            ws = get_sheet()
            if ws:
                row = [str(b.get(col, "") or "") for col in COLUMNS]
                ws.append_row(row, value_input_option="RAW")
                return
        except Exception as e:
            st.warning(f"เพิ่มแถวใน Sheets ไม่ได้: {e}")
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            all_bks = json.load(f)
    else:
        all_bks = []
    all_bks.append(b)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_bks, f, ensure_ascii=False, indent=2)

def update_booking_status(bid, status, return_time, return_image, notes):
    if _use_gsheets():
        try:
            ws = get_sheet()
            if ws:
                all_ids = ws.col_values(1)
                if bid in all_ids:
                    row = all_ids.index(bid) + 1
                    updates = [
                        {"range": f"R{row}C{COLUMNS.index('status')+1}",       "values": [[status]]},
                        {"range": f"R{row}C{COLUMNS.index('return_time')+1}",  "values": [[return_time or ""]]},
                        {"range": f"R{row}C{COLUMNS.index('return_image')+1}", "values": [[return_image or ""]]},
                        {"range": f"R{row}C{COLUMNS.index('notes')+1}",        "values": [[notes or ""]]},
                    ]
                    ws.batch_update(updates, value_input_option="RAW")
                    return
        except Exception as e:
            st.warning(f"อัปเดต Sheets ไม่ได้: {e}")
    all_bks = load_bookings()
    for bk in all_bks:
        if bk["id"] == bid:
            bk["status"]       = status
            bk["return_time"]  = return_time
            bk["return_image"] = return_image
            bk["notes"]        = notes
    save_bookings(all_bks)

def quick_set_status(bid, status, note, flash_key, flash_msg):
    """บันทึกทันทีจากตารางด่วน (แอดมิน) โดยไม่ต้องแนบรูป"""
    update_booking_status(bid, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", note)
    st.session_state.bookings = load_bookings()
    st.session_state[flash_key] = flash_msg

def parse_time(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m

def slots_overlap(s1, s2):
    try:
        s1 = s1.replace("-", "–")
        s2 = s2.replace("-", "–")

        a_start, a_end = s1.split("–")
        b_start, b_end = s2.split("–")

        return (
            parse_time(a_start) < parse_time(b_end)
            and parse_time(b_start) < parse_time(a_end)
        )
    except:
        return False
        
def count_slot_bookings(bookings, item, date_str, slot):

    d = to_date(date_str)
    count = 0

    for b in bookings:

        if b.get("item") != item:
            continue

        if b.get("status") != "ยืมอยู่":
            continue

        b_start = to_date(b.get("start_date", b.get("date")))
        b_end   = to_date(b.get("end_date", b.get("date")))

        if b_start <= d <= b_end and slots_overlap(slot, b.get("slot","")):
            count += int(b.get("quantity", 1) or 1)

    return count
    
def room_capacity(room):

    if room == "ห้องปฏิบัติการคอมพิวเตอร์":
        return 35
    elif room == "ห้องปฏิบัติการ US (อัลตราซาวด์)":
        return 40
    else:
        return 1

# ─── จองห้องแบบประจำทุกสัปดาห์ ──────────────────────────────────────
SINGLE_MODE = "📅 จองครั้งเดียว"
REC_MODE    = "🔁 จองประจำทุกสัปดาห์"
REC_WEEKDAYS = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์"]
WEEKDAY_TH   = REC_WEEKDAYS + ["เสาร์","อาทิตย์"]
REC_SESSIONS = {"เช้า": ("08:30", "12:00"), "บ่าย": ("13:00", "16:30")}
REC_PATTERN_OPTIONS = [f"{wd} • {ss}" for wd in REC_WEEKDAYS for ss in REC_SESSIONS]

def toggle_rec_week(mkey):
    weeks = list(st.session_state.get("rec_weeks", []))
    if mkey in weeks:
        weeks.remove(mkey)
    else:
        weeks.append(mkey)
    st.session_state["rec_weeks"] = weeks

def clear_rec_weeks():
    st.session_state["rec_weeks"] = []

def rec_plan(bookings, rooms, mondays, patterns, qty, today):
    """วันที่จะจองประจำ พร้อมสถานะ: ว่าง / ไม่ว่าง / ผ่านแล้ว (ว่างเมื่อทุกห้องในรายการว่าง)"""
    items = []
    for monday in mondays:
        for p in patterns:
            wd_name, ss = p.split(" • ")
            d = monday + timedelta(days=REC_WEEKDAYS.index(wd_name))
            s, e = REC_SESSIONS[ss]
            slot = f"{s}–{e}"
            busy = [r for r in rooms
                    if count_slot_bookings(bookings, r, d.isoformat(), slot) + qty > room_capacity(r)]
            if d < today:
                status = "ผ่านแล้ว"
            elif busy:
                status = "ไม่ว่าง"
            else:
                status = "ว่าง"
            items.append({"date": d, "slot": slot, "status": status, "rooms": list(rooms)})
    return sorted(items, key=lambda x: (x["date"], x["slot"]))

OTHER_EQUIP = "อื่นๆ"
XRAY_ROOMS = ["ห้องปฏิบัติการ X-Ray : Shimadzu", "ห้องปฏิบัติการ X-Ray : DRGem", "ห้องปฏิบัติการ X-Ray : นวัตกรรม"]

def is_other_item(item):
    return str(item or "").startswith(OTHER_EQUIP + ": ")

def equipment_item_name(sel, other_text):
    return f"{OTHER_EQUIP}: {other_text.strip()}" if sel == OTHER_EQUIP else sel

def is_equipment_item(item):
    return item in EQUIPMENT_LIST or is_other_item(item)

def current_equipment_list():
    """คืนรายการอุปกรณ์สำหรับการยืม-คืน (ใช้กับภาควิชารังสีเทคนิคเท่านั้น)"""
    return EQUIPMENT_LIST

def current_rooms_list():
    """คืนรายการห้อง/เครื่องมือสำหรับการจองห้องตามวิทยาเขตที่เลือกอยู่"""
    if st.session_state.get("campus") == CAMPUSES[1]:
        return HARIPHUNCHAI_ROOMS
    return ROOMS_LIST

def is_slot_taken(bookings, item, date_str, slot):
    """
    คืนค่า booking ถ้ามีการจองซ้อน
    คืน None ถ้ายังว่าง
    ใช้สำหรับอุปกรณ์ (ที่ยืมได้ครั้งละ 1 รายการ)
    """
    d = to_date(date_str)

    for b in bookings:

        if b.get("item") != item:
            continue

        if b.get("status") in ["ยกเลิกแล้ว", "คืนแล้ว"]:
            continue

        b_start = to_date(b.get("start_date", b.get("date")))
        b_end   = to_date(b.get("end_date", b.get("date")))

        if b_start <= d <= b_end and slots_overlap(slot, b.get("slot", "")):
            return b

    return None
    
def is_range_conflict(bookings, item, start_date, end_date, slot):

    # ถ้าไม่ใช่ห้อง ใช้วิธีเดิม
    if item not in ALL_ROOMS:
        for b in bookings:
            if b.get("item") != item:
                continue
            if b.get("status") in ["ยกเลิกแล้ว", "คืนแล้ว"]:
                continue

            b_start = to_date(b.get("start_date", b.get("date")))
            b_end   = to_date(b.get("end_date", b.get("date")))

            overlap = not (end_date < b_start or start_date > b_end)

            if overlap and slots_overlap(slot, b.get("slot","")):
                return b

        return None


    # -----------------------
    # กรณีเป็นห้อง
    # -----------------------

    capacity = room_capacity(item)

    count = 0

    for b in bookings:

        if b.get("item") != item:
            continue

        if b.get("status") in ["ยกเลิกแล้ว","คืนแล้ว"]:
            continue

        b_start = to_date(b.get("start_date", b.get("date")))
        b_end   = to_date(b.get("end_date", b.get("date")))

        overlap = not (end_date < b_start or start_date > b_end)

        if overlap and slots_overlap(slot, b.get("slot","")):
            count += int(b.get("quantity", 1) or 1)

    if count >= capacity:
        return True

    return None

def add_watermark(file, text="RT CMU"):
    img = Image.open(file).convert("RGBA")
    width, height = img.size
    txt_layer = Image.new("RGBA", img.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt_layer)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    watermark_text = f"{text} | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    text_w, text_h = draw.textbbox((0,0), watermark_text, font=font)[2:]
    position = (width - text_w - 20, height - text_h - 20)
    draw.text(position, watermark_text, fill=(255,255,255,180), font=font)
    combined = Image.alpha_composite(img, txt_layer)
    output = io.BytesIO()
    combined.convert("RGB").save(output, format="JPEG")
    output.seek(0)
    return output

def upload_to_drive(file, filename, folder="rtcmu_booking"):
    try:
        service = get_drive_service()
        if not service:
            st.warning("⚠️ เชื่อมต่อ Google Drive ไม่ได้ (ตรวจสอบ st.secrets['gcp'])")
            return ""

        file_stream = add_watermark(file)
        media = MediaIoBaseUpload(file_stream, mimetype="image/jpeg", resumable=False)
        file_metadata = {
            "name": filename,
            "parents": [DRIVE_FOLDER_ID],
        }
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True,          # <-- เพิ่ม: จำเป็นถ้าโฟลเดอร์อยู่ใน Shared Drive
        ).execute()
        file_id = uploaded.get("id")

        service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
            supportsAllDrives=True,          # <-- เพิ่ม
        ).execute()

        return f"https://lh3.googleusercontent.com/d/{file_id}"

    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        st.warning(f"⚠️ อัปโหลดรูป '{getattr(file, 'name', filename)}' ไม่สำเร็จ: {e}")
        with st.expander("รายละเอียด error (สำหรับดีบัก)"):
            st.code(err_detail)
        return ""

def save_images_multi(bid, files, prefix):
    urls = []
    for i, f in enumerate(files):
        filename = f"{prefix}_{bid}_{i+1}_{f.name}"
        fold = "rtcmu_booking/after" if "return" in prefix else "rtcmu_booking/before"
        url = upload_to_drive(f, filename, folder=fold)
        if url:
            urls.append(url)
    return urls

def paths_to_str(paths):
    if isinstance(paths, list):
        return "|".join(paths)
    return paths or ""

def str_to_paths(s):
    if not s:
        return []
    if isinstance(s, list):
        return s
    return [p for p in s.split("|") if p]

# ─── Booking confirmation popup ────────────────────────────────────────────────
@st.dialog("🎉 ยืนยันการจองสำเร็จ")
def show_booking_confirmation():
    b = st.session_state.get("confirm_booking")
    if not b:
        return
    icon = "📋" if b.get("item_type") == "อุปกรณ์" else "🏫"
    start = b.get("start_date") or b.get("date")
    end   = b.get("end_date") or b.get("date")
    date_show = start if start == end else f"{start} → {end}"

    st.markdown(f"""
    <div style='text-align:center;padding:.3rem 0 1rem'>
        <div style='font-size:3rem'>{icon}</div>
        <div style='font-family:Prompt;font-weight:800;font-size:1.25rem;color:#2e7d32'>
            {'ยืมอุปกรณ์' if b.get('item_type')=='อุปกรณ์' else 'จองห้องปฏิบัติการ'}สำเร็จ!
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
| รายละเอียด | ข้อมูล |
|---|---|
| **รหัสการจอง** | `{b.get('id','-')}` |
| **ชื่อ-สกุล** | {b.get('name','-')} |
| **รายการ** | {b.get('item','-')} |
| **จำนวน** | {b.get('quantity',1)} |
| **วันที่** | {date_show} |
| **ช่วงเวลา** | {b.get('slot','-')} |
""")

    st.info("📌 กรุณาบันทึกรหัสการจองนี้ไว้เพื่อใช้อ้างอิงในการคืน/ยกเลิก")

    if st.button("✅ ตกลง", type="primary", use_container_width=True, key="close_confirm_dialog"):
        st.session_state.pop("confirm_booking", None)
        st.rerun()

@st.dialog("📅 รายการจองในวันที่")
def show_day_bookings():
    ds = st.session_state.get("cal_selected_date")
    if not ds:
        return
    d_obj = datetime.strptime(ds, "%Y-%m-%d").date()
    st.markdown(f"### {d_obj.strftime('%d/%m/%Y')}")

    day_bks = [b for b in st.session_state.bookings if b.get("status") != "ยกเลิกแล้ว" and
               (b.get("start_date") or b.get("date","")) <= ds <= (b.get("end_date") or b.get("date",""))]

    if not day_bks:
        st.info("ไม่มีการจองในวันนี้")
    else:
        for b in sorted(day_bks, key=lambda x: x.get("slot","")):
            is_room = b.get("item_type") == "ห้องปฏิบัติการ"
            icon = "🏫" if is_room else "📋"
            item_label = "ห้อง" if is_room else "อุปกรณ์"
            item_name = b.get("item", "-")
            status_txt = "🟢 ยืมอยู่" if b.get("status") == "ยืมอยู่" else "🔵 คืนแล้ว"

            with st.container(border=True):
                st.markdown(f"**{icon} {item_label}:** {item_name}")
                st.markdown(f"**⏰ ช่วงเวลา:** {b.get('slot','-')}  |  **สถานะ:** {status_txt}")
                st.markdown(f"**👤 ผู้จอง:** {b.get('name','-')}  ({b.get('user_status','-')})")
                st.markdown(f"**🎯 วัตถุประสงค์:** {b.get('purpose','-') or '-'}")
                st.caption(f"รหัสการจอง: `{b.get('id','-')}`")

    if st.button("ปิด", use_container_width=True, key="close_day_dialog"):
        st.session_state.pop("cal_selected_date", None)
        st.rerun()
# ─── จองอาจารย์สอบ Oral ───────────────────────────────────────────────────────
ORAL_ADVISORS   = ["ผศ.ดร.ชญานิษฐ์", "รศ.ดร.ศิริประภา", "อ.ดร.วรวัฒน์"]
ORAL_DAY_START  = "08:40"
ORAL_DAY_END    = "16:20"
ORAL_SLOT_MIN   = 20
ORAL_SHEET_NAME = "oral_exam 515113"           # worksheet แยก ในไฟล์ Google Sheets เดิม
ORAL_FILE       = "oral_bookings.json"  # สำรองเมื่อไม่ได้เชื่อม Google Sheets
ORAL_COLUMNS    = ["id", "advisor", "date", "slot", "kind", "name", "phone_id",
                   "user_status", "purpose", "status", "created_at"]
ORAL_BOOK       = "จอง"
ORAL_BLOCK      = "ไม่ว่าง"
ORAL_ACTIVE     = "ใช้งาน"
ORAL_CANCELLED  = "ยกเลิก"

def _build_oral_slots():
    out, t, end = [], parse_time(ORAL_DAY_START), parse_time(ORAL_DAY_END)
    while t + ORAL_SLOT_MIN <= end:
        n = t + ORAL_SLOT_MIN
        out.append(f"{t//60:02d}:{t%60:02d}–{n//60:02d}:{n%60:02d}")
        t = n
    return out

ORAL_SLOTS = _build_oral_slots()

@st.cache_resource(show_spinner=False)
def get_oral_sheet():
    """คืน worksheet 'oral_exam (515113)' ในไฟล์ Sheets เดิม (สร้างให้อัตโนมัติถ้ายังไม่มี)"""
    if not GSHEETS_AVAILABLE:
        return None
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        sh = gspread.authorize(creds).open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet(ORAL_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=ORAL_SHEET_NAME, rows=1000, cols=len(ORAL_COLUMNS))
            ws.insert_row(ORAL_COLUMNS, 1)
        return ws
    except Exception as e:
        st.warning(f"Google Sheets (oral): {e}")
        return None

def _oral_json_load():
    if os.path.exists(ORAL_FILE):
        with open(ORAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _oral_json_save(data):
    with open(ORAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_oral():
    ws = get_oral_sheet()
    if ws is not None:
        try:
            return ws.get_all_records()
        except Exception as e:
            st.warning(f"โหลดตารางอาจารย์จาก Sheets ไม่ได้: {e}")
    return _oral_json_load()

def add_oral_rows(rows):
    """บันทึกแถวใหม่ คืน True เมื่อสำเร็จ"""
    ws = get_oral_sheet()
    if ws is not None:
        try:
            ws.append_rows([[str(r.get(c, "") or "") for c in ORAL_COLUMNS] for r in rows],
                           value_input_option="RAW")
            return True
        except Exception as e:
            st.error(f"บันทึกลง Sheets ไม่สำเร็จ: {e}")
            return False
    data = _oral_json_load()
    data.extend(rows)
    _oral_json_save(data)
    return True

def cancel_oral_rows(ids):
    """เปลี่ยนสถานะแถวเป็น 'ยกเลิก' (ไม่ลบแถวออก เพื่อเก็บประวัติ)"""
    if not ids:
        return True
    ws = get_oral_sheet()
    if ws is not None:
        try:
            all_ids = ws.col_values(1)
            col = ORAL_COLUMNS.index("status") + 1
            for rid in ids:
                if rid in all_ids:
                    ws.update_cell(all_ids.index(rid) + 1, col, ORAL_CANCELLED)
            return True
        except Exception as e:
            st.error(f"ยกเลิกใน Sheets ไม่สำเร็จ: {e}")
            return False
    data = _oral_json_load()
    for r in data:
        if r.get("id") in ids:
            r["status"] = ORAL_CANCELLED
    _oral_json_save(data)
    return True

def oral_day_state(rows, advisor, ds):
    """คืน (booked, blocked): booked = {ช่วงเวลา: แถวที่จอง}, blocked = set ของช่วงที่ตั้งไม่ว่าง"""
    booked, blocked = {}, set()
    for r in rows:
        if r.get("advisor") != advisor or str(r.get("date")) != ds:
            continue
        if r.get("status") == ORAL_CANCELLED:
            continue
        if r.get("kind") == ORAL_BOOK:
            booked[str(r.get("slot"))] = r
        elif r.get("kind") == ORAL_BLOCK:
            blocked.add(str(r.get("slot")))
    return booked, blocked

def oral_bookings_on(rows, ds):
    """รายการจองที่ยังใช้งานอยู่ของวัน ds เรียงตามลำดับอาจารย์และเวลา"""
    order = {a: i for i, a in enumerate(ORAL_ADVISORS)}
    out = [r for r in rows
           if str(r.get("date")) == ds and r.get("kind") == ORAL_BOOK
           and r.get("status") != ORAL_CANCELLED]
    out.sort(key=lambda r: (order.get(r.get("advisor"), 99),
                            parse_time(str(r.get("slot")).split("–")[0])))
    return out

ORAL_BKK        = dt_timezone(timedelta(hours=7))   # เวลาไทย (เซิร์ฟเวอร์อาจอยู่คนละเขตเวลา)
ORAL_CLOSE_DAYS = 2                                  # ปิดจองก่อนวันสอบกี่วัน
ORAL_CLOSE_TIME = dt_time(22, 0)                     # ปิดเวลา 22:00 น.

def oral_now():
    return datetime.now(ORAL_BKK).replace(tzinfo=None)

def oral_today():
    return oral_now().date()

def oral_close_at(d_obj):
    """เวลาที่ปิดรับจองของวันสอบ d_obj เช่น สอบ 26 พ.ย. ปิด 24 พ.ย. 22:00 น."""
    return datetime.combine(d_obj - timedelta(days=ORAL_CLOSE_DAYS), ORAL_CLOSE_TIME)

def oral_booking_closed(d_obj):
    return oral_now() >= oral_close_at(d_obj)

def oral_slot_passed(d_obj, slot):
    today = oral_today()
    if d_obj < today:
        return True
    if d_obj > today:
        return False
    now = oral_now()
    return parse_time(slot.split("–")[0]) <= now.hour * 60 + now.minute

def make_oral_row(advisor, ds, slot, kind, name="", phone="", ustatus="", purpose=""):
    return {"id": str(uuid.uuid4())[:8].upper(), "advisor": advisor, "date": ds,
            "slot": slot, "kind": kind, "name": name, "phone_id": phone,
            "user_status": ustatus, "purpose": purpose, "status": ORAL_ACTIVE,
            "created_at": oral_now().strftime("%Y-%m-%d %H:%M:%S")}

@st.dialog("🎓 จองอาจารย์สอบ Oral (515113)")
def show_oral_day_dialog():
    adv = st.session_state.get("oe_advisor")
    ds  = st.session_state.get("oe_selected_date")
    if not adv or not ds:
        return
    d_obj = datetime.strptime(ds, "%Y-%m-%d").date()
    st.markdown(f"**🎓 {adv}**  |  📅 {d_obj.strftime('%d/%m/%Y')}")
    closed = oral_booking_closed(d_obj)
    if closed:
        st.warning(f"🔒 ปิดรับจองวันนี้แล้ว (ปิดเมื่อ {oral_close_at(d_obj).strftime('%d/%m/%Y %H:%M')} น.)")

    rows = load_oral()
    booked, blocked = oral_day_state(rows, adv, ds)

    cells = ""
    for s in ORAL_SLOTS:
        if s in booked:
            cls, txt = "hour-taken", "❌ จองแล้ว"
        elif s in blocked:
            cls, txt = "hour-taken", "🚫 ไม่ว่าง"
        elif oral_slot_passed(d_obj, s):
            cls, txt = "hour-box", "⌛ เลยเวลา"
        else:
            cls, txt = "hour-free", "✅ ว่าง"
        cells += f"<div class='hour-box {cls}'>{s.replace('–', '<br>')}<br>{txt}</div>"
    st.markdown(
        f"<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:6px'>{cells}</div>",
        unsafe_allow_html=True)
    st.caption("ผู้จองคนอื่นจะเห็นเฉพาะสถานะ ไม่เห็นชื่อผู้จอง")
    st.divider()

    free = [s for s in ORAL_SLOTS
            if s not in booked and s not in blocked and not oral_slot_passed(d_obj, s)]

    # ปุ่มระดับวัน: ตั้งไม่ว่างทั้งวัน / ยกเลิกการตั้งไม่ว่างทั้งหมดของวันนี้ (ใช้ได้ทุกโหมด)
    if blocked:
        st.markdown(f"**🚫 ช่วงที่ตั้งเป็นไม่ว่างอยู่:** {', '.join(sorted(blocked))}")
    dc1, dc2 = st.columns(2)
    with dc1:
        if free and st.button(f"🚫 ไม่ว่างทั้งวัน ({len(free)} ช่วงที่ยังว่าง)",
                              use_container_width=True, key=f"oe_allday_btn_{ds}"):
            if add_oral_rows([make_oral_row(adv, ds, s, ORAL_BLOCK) for s in free]):
                st.session_state.oe_flash = (
                    f"🚫 ตั้งไม่ว่างทั้งวันกับ {adv} วันที่ {d_obj.strftime('%d/%m/%Y')} "
                    f"แล้ว {len(free)} ช่วง")
                st.session_state.pop("oe_selected_date", None)
                st.rerun()
    with dc2:
        if blocked and st.button(f"♻️ ยกเลิกการตั้งไม่ว่างของวันนี้ ({len(blocked)} ช่วง)",
                                 use_container_width=True, key=f"oe_unblock_{ds}"):
            ids = [r["id"] for r in rows
                   if r.get("advisor") == adv and str(r.get("date")) == ds
                   and r.get("kind") == ORAL_BLOCK and r.get("status") != ORAL_CANCELLED]
            if cancel_oral_rows(ids):
                st.session_state.oe_flash = "♻️ ยกเลิกการตั้งไม่ว่างของวันนี้แล้ว"
                st.session_state.pop("oe_selected_date", None)
                st.rerun()

    mode = st.radio("ต้องการทำรายการ", ["📝 ต้องการจอง", "🚫 ไม่ว่าง (บางช่วง)"],
                    horizontal=True, key="oe_mode")

    if mode == "📝 ต้องการจอง":
        if closed:
            st.info("ปิดรับจองสำหรับวันนี้แล้ว")
        elif not free:
            st.info("ไม่มีช่วงเวลาว่างในวันนี้")
        else:
            slot = st.selectbox("⏰ เลือกช่วงเวลา (ครั้งละ 20 นาที) *", free,
                                key=f"oe_slot_{ds}")
            c1, c2 = st.columns(2)
            with c1:
                o_name = st.text_input("ชื่อ-สกุล *", key=f"oe_name_{ds}")
            with c2:
                o_phone = st.text_input("เบอร์โทรบุคลากร / รหัสนักศึกษา *", key=f"oe_phone_{ds}")
            o_status  = st.selectbox("สถานะ *", STATUS_OPTIONS, key=f"oe_status_{ds}")
            o_purpose = st.text_input("หัวข้อ / วัตถุประสงค์", key=f"oe_purpose_{ds}")
            if st.button("✅ ยืนยันการจอง", type="primary", use_container_width=True,
                         key=f"oe_confirm_{ds}"):
                if oral_booking_closed(d_obj):
                    st.error("หมดเวลารับจองของวันนี้แล้ว กรุณาเลือกวันอื่น")
                elif not o_name.strip() or not o_phone.strip():
                    st.error("กรุณากรอกชื่อ-สกุล และเบอร์โทร/รหัสนักศึกษา")
                else:
                    # ตรวจซ้ำกับข้อมูลล่าสุดก่อนบันทึก เพื่อกันการจองซ้ำ
                    now_b, now_bl = oral_day_state(load_oral(), adv, ds)
                    if slot in now_b or slot in now_bl:
                        st.error("ช่วงเวลานี้มีผู้จองหรือถูกตั้งเป็นไม่ว่างแล้ว กรุณาเลือกเวลาอื่น")
                    else:
                        row = make_oral_row(adv, ds, slot, ORAL_BOOK, o_name.strip(),
                                            o_phone.strip(), o_status, o_purpose.strip())
                        if add_oral_rows([row]):
                            st.session_state.oe_flash = (
                                f"✅ จองคิวกับ {adv} วันที่ {d_obj.strftime('%d/%m/%Y')} "
                                f"เวลา {slot} สำเร็จ (รหัส {row['id']}) กรุณาบันทึกรหัสนี้ไว้")
                            st.session_state.pop("oe_selected_date", None)
                            st.rerun()
    else:
        if not free:
            st.info("ไม่มีช่วงเวลาที่ตั้งเป็นไม่ว่างเพิ่มได้ในวันนี้")
        else:
            targets = st.multiselect("เลือกช่วงเวลาที่ไม่ว่าง (เลือกได้หลายช่วง)", free,
                                     key=f"oe_block_{ds}")
            if st.button("💾 บันทึกว่าไม่ว่างเฉพาะช่วงที่เลือก", type="primary",
                         use_container_width=True, key=f"oe_block_save_{ds}"):
                if not targets:
                    st.warning("กรุณาเลือกช่วงเวลาอย่างน้อย 1 ช่วง")
                elif add_oral_rows([make_oral_row(adv, ds, s, ORAL_BLOCK) for s in targets]):
                    st.session_state.oe_flash = (
                        f"🚫 ตั้งเป็นไม่ว่างกับ {adv} วันที่ {d_obj.strftime('%d/%m/%Y')} "
                        f"แล้ว {len(targets)} ช่วง")
                    st.session_state.pop("oe_selected_date", None)
                    st.rerun()

    st.divider()
    if st.button("ปิด", use_container_width=True, key=f"oe_close_{ds}"):
        st.session_state.pop("oe_selected_date", None)
        st.rerun()

# ─── Session state ─────────────────────────────────────────────────────────────
today = date.today()
defaults = {
    "page": "หน้าแรก",
    "cal_year": today.year,
    "cal_month": today.month,
    "campus": CAMPUSES[0],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.session_state.bookings = load_bookings()
bookings = st.session_state.bookings

# แสดง popup ยืนยันการจอง หากมีการจอง/ยืมสำเร็จล่าสุด
if st.session_state.get("confirm_booking"):
    show_booking_confirmation()
if st.session_state.get("cal_selected_date"):
    show_day_bookings()
if st.session_state.get("oe_selected_date") and st.session_state.page == "จองอาจารย์":
    show_oral_day_dialog()
# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    _logo_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "RT CMU Logo_1.jpg"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo.ico"),
    ]
    _logo_path = next((p for p in _logo_candidates if os.path.exists(p)), None)
    if _logo_path:
        st.image(_logo_path, use_container_width=True)
    else:
        st.markdown("<div style='text-align:center;font-size:3rem;padding:.5rem 0'>🏥</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center;padding:.3rem 0 .5rem'>
        <div style='font-family:Prompt;font-weight:800;font-size:.95rem;color:#90caf9'>ภาควิชารังสีเทคนิค</div>
        <div style='font-size:.72rem;color:#90caf9;opacity:.7'>ระบบการจองห้องปฏิบัติการ และการยืม-คืนเครื่องมือ และอุปกรณ์</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>📍 เลือกวิทยาเขต</div>", unsafe_allow_html=True)
    camp1, camp2 = st.columns(2)
    with camp1:
        if st.button("🏛️ รังสีเทคนิค", use_container_width=True,
                     type="primary" if st.session_state.campus == CAMPUSES[0] else "secondary",
                     key="campus_1"):
            st.session_state.campus = CAMPUSES[0]
            st.session_state.page = "หน้าแรก"; st.rerun()
    with camp2:
        if st.button("🏢 หริภุญไชย", use_container_width=True,
                     type="primary" if st.session_state.campus == CAMPUSES[1] else "secondary",
                     key="campus_2"):
            st.session_state.campus = CAMPUSES[1]
            st.session_state.page = "หน้าแรก"; st.rerun()
    st.divider()

    if st.button("🏠  หน้าแรก", use_container_width=True,
                 type="primary" if st.session_state.page == "หน้าแรก" else "secondary",
                 key="nav_หน้าแรก"):
        st.session_state.page = "หน้าแรก"; st.rerun()

    if st.session_state.campus == CAMPUSES[0]:
        st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>🔬 อุปกรณ์</div>", unsafe_allow_html=True)
        for label, key in [("📋  ยืมอุปกรณ์","ยืมอุปกรณ์"),("📦  คืนอุปกรณ์","คืนอุปกรณ์")]:
            if st.button(label, use_container_width=True, type="secondary", key=f"nav_{key}"):
                st.session_state.page = key; st.rerun()

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>🏫 ห้องปฏิบัติการ</div>", unsafe_allow_html=True)
    for label, key in [("📅  จองห้อง","จองห้อง"),("❌  ยกเลิกห้อง","ยกเลิกห้อง")]:
        if st.button(label, use_container_width=True, type="secondary", key=f"nav_{key}"):
            st.session_state.page = key; st.rerun()

    if st.session_state.campus == CAMPUSES[0]:
        st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>🎓 การสอบ</div>", unsafe_allow_html=True)
        if st.button("🎓  จองอาจารย์สอบ Oral", use_container_width=True, type="secondary", key="nav_จองอาจารย์"):
            st.session_state.page = "จองอาจารย์"; st.rerun()

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>📊 ภาพรวม</div>", unsafe_allow_html=True)
    for label, key in [("🗓️  ปฏิทินการจอง","ปฏิทิน"),("📊  สรุปการใช้งาน","สรุป")]:
        if st.button(label, use_container_width=True, type="secondary", key=f"nav_{key}"):
            st.session_state.page = key; st.rerun()

    st.divider()
    active_eq   = sum(1 for b in bookings if b["status"]=="ยืมอยู่" and b.get("item_type")=="อุปกรณ์")
    active_room = sum(1 for b in bookings if b["status"]=="ยืมอยู่" and b.get("item_type")=="ห้องปฏิบัติการ")
    st.markdown(f"""
    <div style='font-size:.78rem;color:#90caf9;text-align:center;line-height:1.8'>
        🔬 ยืมอุปกรณ์อยู่ <b style='color:#ffcc02'>{active_eq}</b> รายการ<br>
        🏫 จองห้องอยู่ <b style='color:#ffcc02'>{active_room}</b> รายการ<br>
        <span style='opacity:.65;font-size:.68rem'>พบปัญหาติดต่อ จีรนันท์<br>065-5354782</span>
    </div>
    """, unsafe_allow_html=True)

# ─── Main header ──────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="main-header">
    <div>
        <h2>ระบบการจองห้องปฏิบัติการ และการยืม-คืนเครื่องมือ และอุปกรณ์</h2>
        <p>ภาควิชารังสีเทคนิค • คณะเทคนิคการแพทย์ • มหาวิทยาลัยเชียงใหม่</p>
        <p>📍 วิทยาเขต: <b>{st.session_state.campus}</b></p>
        <p>📅 เปิดบริการ • วันเวลาราชการ • วันจันทร์ - วันศุกร์ • เวลา 08:30–16:30 น. • (หยุดวันนักขัตฤกษ์)</p>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.page != "หน้าแรก":
    _bc1, _bc2, _bc3 = st.columns([1, 1, 6])
    with _bc1:
        if st.button("◀ ย้อนกลับ", key="btn_back", use_container_width=True, type="secondary"):
            _prev = st.session_state.get("prev_page", "หน้าแรก")
            st.session_state.prev_page = st.session_state.page
            st.session_state.page = _prev; st.rerun()
    with _bc2:
        if st.button("🏠 หน้าแรก", key="btn_home_top", use_container_width=True, type="primary"):
            st.session_state.prev_page = st.session_state.page
            st.session_state.page = "หน้าแรก"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ หน้าแรก
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "หน้าแรก":
    active_eq_n   = sum(1 for b in bookings if b["status"]=="ยืมอยู่" and b.get("item_type")=="อุปกรณ์")
    active_room_n = sum(1 for b in bookings if b["status"]=="ยืมอยู่" and b.get("item_type")=="ห้องปฏิบัติการ")
    today_str     = date.today().strftime("%Y-%m-%d")
    today_bk = sum(1 for b in bookings if b.get("status")=="ยืมอยู่" and
                   (b.get("start_date") or b.get("date","")) <= today_str <= (b.get("end_date") or b.get("date","")))

    st.markdown(f"""
    <div style='text-align:center;padding:1rem 0 2rem'>
        <div style='font-size:1rem;color:#607d8b;margin-bottom:.3rem'>วันที่ {date.today().strftime("%d/%m/%Y")}</div>
        <h2 style='font-family:Prompt;color:#0d2137;font-size:1.6rem;margin:0'>ยินดีต้อนรับสู่ระบบการจองห้องปฏิบัติการ และการยืม-คืนเครื่องมือ และอุปกรณ์</h2>
        <div style='color:#607d8b;font-size:.9rem;margin-top:.3rem'>ภาควิชารังสีเทคนิค • คณะเทคนิคการแพทย์ • มหาวิทยาลัยเชียงใหม่</div>
    </div>
    """, unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)
    with s1: st.markdown(f'<div class="stat-card orange"><h3>{active_eq_n}</h3><p>🔬 อุปกรณ์ที่ยืมอยู่</p></div>', unsafe_allow_html=True)
    with s2: st.markdown(f'<div class="stat-card" style="border-left-color:#7b1fa2"><h3>{active_room_n}</h3><p>🏫 ห้องที่จองอยู่</p></div>', unsafe_allow_html=True)
    with s3: st.markdown(f'<div class="stat-card green"><h3>{today_bk}</h3><p>📅 การจองวันนี้</p></div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🚀 เข้าสู่ระบบ")
    if st.session_state.campus == CAMPUSES[0]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""<div style='background:linear-gradient(135deg,#1565c0,#0288d1);border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;box-shadow:0 4px 18px rgba(21,101,192,.3)'>
                <div style='font-size:2.5rem'>📋</div><div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>ยืมอุปกรณ์</div>
                <div style='font-size:.82rem;opacity:.85'>จองและยืมอุปกรณ์ของภาควิชา</div></div>""", unsafe_allow_html=True)
            if st.button("📋  เข้าหน้ายืมอุปกรณ์", use_container_width=True, type="secondary", key="home_borrow"):
                st.session_state.page = "ยืมอุปกรณ์"; st.rerun()
        with col2:
            st.markdown("""<div style='background:linear-gradient(135deg,#ef6c00,#f9a825);border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;box-shadow:0 4px 18px rgba(239,108,0,.3)'>
                <div style='font-size:2.5rem'>📦</div><div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>คืนอุปกรณ์</div>
                <div style='font-size:.82rem;opacity:.85'>บันทึกการคืนอุปกรณ์</div></div>""", unsafe_allow_html=True)
            if st.button("📦  เข้าหน้าคืนอุปกรณ์", use_container_width=True, key="home_return"):
                st.session_state.page = "คืนอุปกรณ์"; st.rerun()

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("""<div style='background:linear-gradient(135deg,#2e7d32,#43a047);border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;box-shadow:0 4px 18px rgba(46,125,50,.3)'>
            <div style='font-size:2.5rem'>📅</div><div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>จองห้องปฏิบัติการ</div>
            <div style='font-size:.82rem;opacity:.85'>จองห้องสำหรับการเรียนและวิจัย</div></div>""", unsafe_allow_html=True)
        if st.button("📅  เข้าหน้าจองห้อง", use_container_width=True, key="home_room"):
            st.session_state.page = "จองห้อง"; st.rerun()
    with col4:
        st.markdown("""<div style='background:linear-gradient(135deg,#c62828,#e53935);border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;box-shadow:0 4px 18px rgba(198,40,40,.3)'>
            <div style='font-size:2.5rem'>❌</div><div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>ยกเลิก/คืนห้องปฏิบัติการ</div>
            <div style='font-size:.82rem;opacity:.85'>บันทึกการยกเลิก/คืนห้องหลังใช้งาน</div></div>""", unsafe_allow_html=True)
        if st.button("❌  เข้าหน้ายกเลิก/คืนห้อง", use_container_width=True, key="home_rroom"):
            st.session_state.page = "ยกเลิกห้อง"; st.rerun()

    st.divider()
    col5, col6 = st.columns(2)
    with col5:
        st.markdown("""<div style='background:white;border-radius:14px;padding:1.2rem 1.5rem;box-shadow:0 2px 12px rgba(0,0,0,.08);border-left:5px solid #1565c0;margin-bottom:.5rem'>
            <div style='font-size:1.8rem'>🗓️</div><div style='font-family:Prompt;font-weight:700;color:#0d2137'>ปฏิทินการจอง</div>
            <div style='font-size:.82rem;color:#607d8b'>ดูภาพรวมการจองรายเดือน</div></div>""", unsafe_allow_html=True)
        if st.button("🗓️  ดูปฏิทิน", use_container_width=True, key="home_cal"):
            st.session_state.page = "ปฏิทิน"; st.rerun()
    with col6:
        st.markdown("""<div style='background:white;border-radius:14px;padding:1.2rem 1.5rem;box-shadow:0 2px 12px rgba(0,0,0,.08);border-left:5px solid #546e7a;margin-bottom:.5rem'>
            <div style='font-size:1.8rem'>📊</div><div style='font-family:Prompt;font-weight:700;color:#0d2137'>สรุปการใช้งาน</div>
            <div style='font-size:.82rem;color:#607d8b'>ตารางและสถิติการยืม-คืน</div></div>""", unsafe_allow_html=True)
        if st.button("📊  ดูสรุป", use_container_width=True, key="home_sum"):
            st.session_state.page = "สรุป"; st.rerun()

    if st.session_state.campus == CAMPUSES[0]:
        st.markdown("""<div style='background:linear-gradient(135deg,#6a1b9a,#8e24aa);border-radius:16px;padding:1.2rem 1.5rem;color:white;margin-bottom:.5rem;box-shadow:0 4px 18px rgba(106,27,154,.3)'>
            <div style='font-size:1.8rem'>🎓</div><div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>จองอาจารย์สอบ Oral Exam (515113)</div>
            <div style='font-size:.82rem;opacity:.85'>เลือกอาจารย์ผู้สอบ แล้วจองคิวครั้งละ 20 นาที</div></div>""", unsafe_allow_html=True)
        if st.button("🎓  เข้าหน้าจองอาจารย์สอบ Oral (515113)", use_container_width=True, key="home_oral"):
            st.session_state.page = "จองอาจารย์"; st.rerun()

    st.divider()
    st.markdown("""<div style='background:#f0f7ff;border-radius:12px;padding:1rem 1.5rem;border:1px solid #bbdefb;font-size:.82rem;color:#1565c0'>
        ℹ️ <b>วิธีใช้งาน:</b> เลือกเมนูจากปุ่มด้านบน หรือคลิกที่แถบเมนูด้านซ้ายมือได้เลยค่ะ<br>
        📞 พบปัญหาการจอง ติดต่อ <b>จีรนันท์ 065-5354782</b></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ ยืมอุปกรณ์
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "ยืมอุปกรณ์":
    st.markdown('<div class="sec-title">📋 ฟอร์มยืมอุปกรณ์</div>', unsafe_allow_html=True)

    with st.expander("🗺️ ภาพรวมความว่างอุปกรณ์ทั้งหมด — เลือกวันที่ต้องการ", expanded=True):
        ov_date = st.date_input("เลือกวันที่", value=date.today(), key="ov_date", min_value=date.today())
        ov_ds   = ov_date.strftime("%Y-%m-%d")
        header = "<tr><th style='text-align:left;min-width:180px'>อุปกรณ์</th>"
        for s in TIME_SLOTS:
            header += f"<th style='font-size:.7rem;padding:4px 3px;white-space:nowrap'>{s.replace('–','<br>')}</th>"
        header += "</tr>"
        rows_html = ""
        for item in current_equipment_list():
            rows_html += f"<tr><td style='font-size:.78rem;padding:5px 8px;white-space:nowrap'>{item}</td>"
            for s in TIME_SLOTS:
                taken = is_slot_taken(bookings, item, ov_ds, s)
                rows_html += "<td style='background:#fde8e8;text-align:center;font-size:.85rem'>❌</td>" if taken else "<td style='background:#e8f5e9;text-align:center;font-size:.85rem'>✅</td>"
            rows_html += "</tr>"
        st.markdown(f"""<div style='overflow-x:auto;margin-top:.5rem'>
        <table style='border-collapse:collapse;width:100%'>
            <thead style='background:#0d2137;color:white'>{header}</thead>
            <tbody>{rows_html}</tbody>
        </table><div style='font-size:.72rem;color:#607d8b;margin-top:6px'>✅ ว่าง &nbsp;|&nbsp; ❌ ไม่ว่าง</div></div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("##### 👤 ข้อมูลผู้ยืม")
    c1, c2, c3 = st.columns(3)
    with c1: name = st.text_input("ชื่อ-สกุล *", placeholder="ชื่อ-สกุลผู้ยืม")
    with c2: phone_id = st.text_input("เบอร์โทรบุคลากร / รหัสนักศึกษา *", placeholder="0801000001/661110000")
    with c3: user_status = st.selectbox("สถานะ *", STATUS_OPTIONS)
    purpose = st.text_input("วัตถุประสงค์", placeholder="ระบุวัตถุประสงค์การใช้งาน")

    st.divider()
    st.markdown("##### 📦 เลือกอุปกรณ์")
    sel_eq = st.selectbox("เลือกอุปกรณ์ *", current_equipment_list(), key="sel_eq")
    other_text = ""
    if sel_eq == OTHER_EQUIP:
        other_text = st.text_input("✏️ ระบุชื่ออุปกรณ์ที่ยืม (อื่นๆ) *", key="eq_other_name",
                                   placeholder="เช่น กล่องใส่ฟิล์ม, สายไฟ, อุปกรณ์เฉพาะทาง", max_chars=100)
    qty    = st.number_input("จำนวน", min_value=1, max_value=50, value=1)
    if st.button("✔️ เลือกอุปกรณ์นี้", type="primary", key="confirm_eq"):
        if sel_eq == OTHER_EQUIP and not other_text.strip():
            st.error("กรุณาระบุชื่ออุปกรณ์ในช่อง อื่นๆ")
        else:
            item_name = equipment_item_name(sel_eq, other_text)
            st.session_state["borrow_item"]      = item_name
            st.session_state["borrow_item_type"] = "อุปกรณ์"
            st.session_state["borrow_qty"]       = qty
            st.success(f"เลือกแล้ว: **{item_name}** จำนวน {qty} ชิ้น")

    chosen      = st.session_state.get("borrow_item")
    chosen_type = st.session_state.get("borrow_item_type", "อุปกรณ์")
    chosen_qty  = st.session_state.get("borrow_qty", 1)

    if chosen:
        st.info(f"**รายการที่เลือก:** {chosen}  |  ประเภท: {chosen_type}  |  จำนวน: {chosen_qty}")
    else:
        st.warning("⚠️ กรุณาเลือกอุปกรณ์ก่อน")

    st.divider()
    st.markdown("##### 📅 วันที่และช่วงเวลา")
    date_range = st.date_input("📅 เลือกช่วงวันที่ยืม *", value=(date.today(), date.today()), min_value=date.today())
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range
    start_str = start_date.strftime("%Y-%m-%d")
    end_str   = end_date.strftime("%Y-%m-%d")

    tc1, tc2 = st.columns(2)
    with tc1: eq_start = st.selectbox("⏰ เวลาเริ่ม *", ALL_STARTS, key="eq_start")
    valid_ends = [e for e in ALL_ENDS if parse_time(e) > parse_time(eq_start)]
    with tc2:
        if valid_ends:
            eq_end = st.selectbox("⏰ เวลาสิ้นสุด *", valid_ends, key="eq_end")
        else:
            st.selectbox("⏰ เวลาสิ้นสุด *", ["—"], key="eq_end", disabled=True)
            eq_end = None

    borrow_slot = None
    if eq_end:
        borrow_slot = f"{eq_start}–{eq_end}"
        conflict_bk = is_range_conflict(bookings, chosen, start_date, end_date, borrow_slot)
        if conflict_bk:
            st.error(f"⛔ ช่วง **{borrow_slot}** ทับซ้อนกับการจองของ **{conflict_bk['name']}**")
            borrow_slot = None
        else:
            st.success(f"✅ ช่วงเวลาที่เลือก: **{borrow_slot}**")
            st.info(f"📅 {start_str} → {end_str} | ⏰ {borrow_slot}")

    st.divider()
    st.markdown("##### 📷 รูปภาพอุปกรณ์ก่อนนำออก (เพิ่มภายหลังได้)")
    borrow_imgs = st.file_uploader("อัปโหลดรูปภาพอุปกรณ์ก่อนยืม (เลือกได้หลายรูป)",
        type=["jpg","jpeg","png","heic","webp"], key="upload_borrow", accept_multiple_files=True)
    if borrow_imgs:
        cols_prev = st.columns(min(len(borrow_imgs), 4))
        for i, f in enumerate(borrow_imgs):
            with cols_prev[i % 4]: st.image(f, caption=f"รูป {i+1}", width=150)

    st.divider()
    col_b, _ = st.columns([1, 3])
    with col_b:
        submit = st.button("✅ ยืนยันการยืม", type="primary", use_container_width=True)

    if submit:
        if not name.strip() or not phone_id.strip():
            st.error("กรุณากรอกชื่อ-สกุล และเบอร์โทรบุคลากร/รหัสนักศึกษา")
        elif not chosen:
            st.error("กรุณาเลือกอุปกรณ์ก่อน")
        elif not borrow_slot:
            st.error("ไม่มีช่วงเวลาว่าง กรุณาเลือกวันอื่น")
        else:
            bid = str(uuid.uuid4())[:8].upper()
            img_path = ""
            if borrow_imgs:
                paths = save_images_multi(bid, borrow_imgs, "borrow")
                img_path = paths_to_str(paths)
            new_bk = {
                "id": bid, "name": name.strip(), "phone_id": phone_id.strip(),
                "user_status": user_status, "purpose": purpose,
                "item": chosen, "item_type": "อุปกรณ์", "quantity": chosen_qty,
                "start_date": start_str, "end_date": end_str, "slot": borrow_slot,
                "borrow_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "return_time": None, "status": "ยืมอยู่",
                "borrow_image": img_path, "return_image": None, "notes": "",
            }
            save_one_booking(new_bk)

            # โหลดข้อมูลล่าสุดจาก Google Sheets
            st.session_state.bookings = load_bookings()
            
            for k in ["borrow_item","borrow_item_type","borrow_qty"]:
                st.session_state.pop(k, None)

            st.session_state["confirm_booking"] = new_bk
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ คืนอุปกรณ์
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "คืนอุปกรณ์":
    st.markdown('<div class="sec-title">📦 บันทึกการคืนอุปกรณ์</div>', unsafe_allow_html=True)

    # ✅ กรองเฉพาะอุปกรณ์เท่านั้น ไม่รวมห้อง และเฉพาะวิทยาเขตที่เลือกอยู่
    active = [b for b in bookings if b["status"] == "ยืมอยู่" and b.get("item_type") == "อุปกรณ์"
              and is_equipment_item(b.get("item"))]

    if not active:
        st.info("✅ ไม่มีรายการที่ยืมอยู่ในขณะนี้")
    else:
        search = st.text_input("🔍 ค้นหาด้วยชื่อผู้ยืม หรือ รหัสการยืม", placeholder="พิมพ์ชื่อ หรือรหัส เช่น A1B2C3D4")
        filtered = [b for b in active if not search or
                    search.lower() in str(b["name"]).lower() or search.upper() in str(b["id"]).upper()]
        st.markdown(f"**พบ {len(filtered)} รายการที่กำลังยืมอยู่**")

        # ── ตารางด่วน (เฉพาะแอดมิน): กดคืนแล้วบันทึกทันที ไม่ต้องแนบรูป ──
        with st.expander("⚡ ตารางด่วน (แอดมิน) — กดคืนเพื่อบันทึกทันที"):
            equip_pin = st.text_input("🔐 รหัสแอดมิน", type="password", key="equip_quick_pin")
            equip_unlocked = equip_pin == ADMIN_PIN
            flash = st.session_state.pop("equip_quick_flash", None)
            if flash:
                st.success(flash)
            if not equip_unlocked:
                st.caption("กรอกรหัสแอดมินก่อน ปุ่มคืนจึงจะกดได้")
            for i, b in enumerate(filtered):
                start, end = get_date_range(b)
                date_show = start if start == end else f"{start} → {end}"
                c1, c2, c3, c4, c5 = st.columns([1.2, 1.5, 2.2, 1.9, 0.8])
                c1.caption(f"`{b['id']}`")
                c2.caption(b["name"])
                c3.caption(b["item"])
                c4.caption(f"{date_show} • {b.get('slot', '-')}")
                c5.button("คืน", key=f"quick_ret_{i}_{b['id']}", disabled=not equip_unlocked,
                          use_container_width=True, on_click=quick_set_status,
                          args=(b["id"], "คืนแล้ว", "คืนด่วนโดยแอดมิน", "equip_quick_flash",
                                f"✅ คืน {b['item']} ของ {b['name']} แล้ว"))

        st.divider()
        st.markdown("##### 📋 รายละเอียด (แนบรูป/หมายเหตุ)")

        for b in filtered:
            start, end = get_date_range(b)
            date_show = start if start == end else f"{start} → {end}"
            slot_disp = b.get("slot", b.get("hour", "-"))

            with st.expander(f"🔖 [{b['id']}]  {b['name']}  —  {b['item']}  ({date_show}  {slot_disp})", expanded=False):
                ci1, ci2 = st.columns([1.5, 1])
                with ci1:
                    st.markdown(f"""| รายละเอียด | ข้อมูล |
|---|---|
| **รหัส** | `{b['id']}` |
| **ชื่อ-สกุล** | {b['name']} |
| **อุปกรณ์** | {b['item']} |
| **วันที่** | {date_show} |
| **ช่วงเวลา** | {slot_disp} |
| **เวลาที่จอง** | {b['borrow_time']} |""")
                with ci2:
                    borrow_paths = str_to_paths(b.get("borrow_image",""))
                    if borrow_paths:
                        for i, p in enumerate(borrow_paths):
                            st.image(p, caption=f"📷 รูปก่อนยืม {i+1}", width=180)
                    else:
                        st.caption("ไม่มีรูปก่อนยืม")

                if not b.get("borrow_image"):
                    st.markdown("**📷 เพิ่มรูปก่อนยืม (ภายหลัง)**")
                    add_borrow_imgs = st.file_uploader("อัปโหลดรูปก่อนยืม",
                        type=["jpg","jpeg","png","heic","webp"], key=f"add_borrow_{b['id']}", accept_multiple_files=True)
                    if add_borrow_imgs:
                        cols_ab = st.columns(min(len(add_borrow_imgs), 4))
                        for i, f in enumerate(add_borrow_imgs):
                            with cols_ab[i % 4]: st.image(f, caption=f"รูป {i+1}", width=130)
                        if st.button("💾 บันทึกรูปก่อนยืม", key=f"save_borrow_{b['id']}"):
                            new_paths = save_images_multi(b["id"], add_borrow_imgs, "borrow_add")
                            for bk in bookings:
                                if bk["id"] == b["id"]:
                                    existing = str_to_paths(bk.get("borrow_image",""))
                                    bk["borrow_image"] = paths_to_str(existing + new_paths)
                            save_bookings(bookings)
                            st.session_state.bookings = bookings
                            st.success(f"✅ บันทึก {len(new_paths)} รูปแล้ว"); st.rerun()

                st.markdown("**📷 รูปภาพอุปกรณ์ขณะคืน**")
                ret_imgs = st.file_uploader("อัปโหลดรูปภาพตอนคืน",
                    type=["jpg","jpeg","png","heic","webp"], key=f"upload_ret_{b['id']}", accept_multiple_files=True)
                if ret_imgs:
                    cols_ret = st.columns(min(len(ret_imgs), 4))
                    for i, f in enumerate(ret_imgs):
                        with cols_ret[i % 4]: st.image(f, caption=f"รูป {i+1}", width=130)

                ret_notes = st.text_input("หมายเหตุ / สภาพอุปกรณ์", placeholder="เช่น ครบถ้วน สภาพดี", key=f"note_{b['id']}")
                col_r, _ = st.columns([1, 3])
                with col_r:
                    if st.button(f"✅ ยืนยันการคืน", key=f"ret_{b['id']}", type="primary", use_container_width=True):
                        img_path = ""
                        if ret_imgs:
                            paths = save_images_multi(b["id"], ret_imgs, "return")
                            img_path = paths_to_str(paths)
                        _ret_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        update_booking_status(b["id"], "คืนแล้ว", _ret_time, img_path, ret_notes)
                        for bk in bookings:
                            if bk["id"] == b["id"]:
                                bk["status"] = "คืนแล้ว"; bk["return_time"] = _ret_time
                                bk["return_image"] = img_path; bk["notes"] = ret_notes
                        st.session_state.bookings = bookings
                        st.success(f"✅ คืนอุปกรณ์ [{b['id']}] เรียบร้อย!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ จองห้องปฏิบัติการ
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "จองห้อง":
    st.markdown('<div class="sec-title">🏫 ฟอร์มจองห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    import numpy as np
    import plotly.graph_objects as go
    
    with st.expander("🗺️ ดูภาพรวมความว่างของห้องทั้งหมด", expanded=False):
    
        rov_date = st.date_input("เลือกวันที่", value=date.today(), key="rov_date")
        rov_ds = rov_date.strftime("%Y-%m-%d")
    
        z_matrix = []
    
        for room in current_rooms_list():
            row = []
            for s in TIME_SLOTS:
                count = count_slot_bookings(bookings, room, rov_ds, s)
                cap = room_capacity(room)
    
                # ratio 0–1
                val = count / cap if cap else 0
                row.append(val)
    
            z_matrix.append(row)
    
        z_matrix = np.array(z_matrix)
    
        fig = go.Figure(
            data=go.Heatmap(
                z=z_matrix,
                x=TIME_SLOTS,
                y=current_rooms_list(),
                colorscale=[
                    [0.0, "#e8f5e9"],
                    [0.5, "#fff176"],
                    [0.8, "#ff9800"],
                    [1.0, "#c62828"],
                ],
                hovertemplate="ห้อง: %{y}<br>เวลา: %{x}<br>ความหนาแน่น: %{z:.0%}<extra></extra>"
            )
        )
    
        fig.update_layout(
            height=600,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(side="top")
        )
    
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("##### 👤 ข้อมูลผู้จอง")
    r1, r2, r3 = st.columns(3)
    with r1: r_name   = st.text_input("ชื่อ-สกุล *", placeholder="ชื่อ-สกุลผู้จอง", key="r_name")
    with r2: r_phone  = st.text_input("เบอร์โทรบุคลากร / รหัสนักศึกษา *", placeholder="0801000001/661110000", key="r_phone")
    with r3: r_status = st.selectbox("สถานะ *", STATUS_OPTIONS, key="r_status")
    r_purpose = st.text_input("วัตถุประสงค์การใช้ห้อง", placeholder="เช่น ปฏิบัติการ CT Scan ปี 3", key="r_purpose")

    st.divider()
    st.markdown("##### 🏫 เลือกห้องปฏิบัติการ")
    r_room = st.selectbox("เลือกห้อง *", current_rooms_list(), key="r_room")

    r_full_room = False
    if r_room in ["ห้องปฏิบัติการคอมพิวเตอร์", "ห้องปฏิบัติการ US (อัลตราซาวด์)"]:
        r_full_room = st.checkbox(
            "🔒 ต้องการจองทั้งห้อง (ห้องจะเต็มทันที ผู้อื่นจองซ้อนในช่วงเวลานี้ไม่ได้)",
            key="r_full_room"
        )
        if r_full_room:
            st.info(f"ห้องนี้จะถูกจองเต็มทั้งหมด {room_capacity(r_room)} ที่นั่ง ในช่วงเวลาที่เลือก")
    r_quantity = room_capacity(r_room) if r_full_room else 1

    st.divider()
    r_mode = st.radio("รูปแบบการจอง *", [SINGLE_MODE, REC_MODE], horizontal=True, key="r_mode")
    if r_mode == REC_MODE:
        # ── จองประจำทุกสัปดาห์ ──
        rec_done = st.session_state.pop("rec_result", None)
        if rec_done:
            st.success(f"✅ จองประจำสำเร็จ {len(rec_done)} ครั้ง ห้อง {r_room}")
            st.dataframe(rec_done, hide_index=True)

        st.markdown("##### 🔁 วันและช่วงเวลาที่ต้องการจองทุกสัปดาห์")
        rec_patterns = st.multiselect("เลือกได้หลายรายการ *", REC_PATTERN_OPTIONS, key="rec_pattern")
        rec_xray = False
        if all(x in current_rooms_list() for x in XRAY_ROOMS):
            rec_xray = st.checkbox("📷 จอง X-ray ทั้ง 3 ห้องพร้อมกัน (ใช้แทนการเลือกห้องด้านบน)", key="rec_xray")
        rec_rooms = XRAY_ROOMS if rec_xray else [r_room]
        rec_qty = 1 if rec_xray else r_quantity

        st.markdown("##### 🗓️ เลือกสัปดาห์จากปฏิทิน")
        st.caption("กดวันใดก็ได้ในสัปดาห์ เพื่อเลือกหรือยกเลิกทั้งสัปดาห์ (สัปดาห์ที่เลือกจะเป็นสีน้ำเงิน)")
        today_rec = oral_today()
        st.session_state.setdefault("rec_year", today_rec.year)
        st.session_state.setdefault("rec_month", today_rec.month)
        st.session_state.setdefault("rec_weeks", [])

        rn1, rn2, rn3 = st.columns([1, 3, 1])
        with rn1:
            if st.button("◀ เดือนก่อน", use_container_width=True, key="rec_prev"):
                if st.session_state.rec_month == 1:
                    st.session_state.rec_month = 12
                    st.session_state.rec_year -= 1
                else:
                    st.session_state.rec_month -= 1
                st.rerun()
        with rn2:
            st.markdown(
                f"<h3 style='text-align:center;font-family:Prompt;color:#0d2137;margin:4px 0'>"
                f"{MONTH_TH[st.session_state.rec_month]} {st.session_state.rec_year + 543}</h3>",
                unsafe_allow_html=True)
        with rn3:
            if st.button("เดือนถัดไป ▶", use_container_width=True, key="rec_next"):
                if st.session_state.rec_month == 12:
                    st.session_state.rec_month = 1
                    st.session_state.rec_year += 1
                else:
                    st.session_state.rec_month += 1
                st.rerun()

        rec_yr, rec_mo = st.session_state.rec_year, st.session_state.rec_month
        hdr_cols = st.columns(7)
        for i, wd in enumerate(WEEKDAY_TH):
            hdr_cols[i].markdown(
                f"<div style='text-align:center;font-weight:700;font-size:.85rem;"
                f"color:{'#c62828' if i >= 5 else '#546e7a'};background:#f0f4f8;"
                f"border-radius:6px;padding:6px 0'>{wd}</div>", unsafe_allow_html=True)
        for week in calendar.monthcalendar(rec_yr, rec_mo):
            wcols = st.columns(7)
            for ci, d in enumerate(week):
                with wcols[ci]:
                    if d == 0:
                        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
                        continue
                    d_obj = date(rec_yr, rec_mo, d)
                    monday = d_obj - timedelta(days=d_obj.weekday())
                    st.button(str(d), key=f"rec_day_{d_obj.isoformat()}", use_container_width=True,
                              type="primary" if monday.isoformat() in st.session_state.rec_weeks else "secondary",
                              disabled=monday + timedelta(days=6) < today_rec,
                              on_click=toggle_rec_week, args=(monday.isoformat(),))

        rec_sel = sorted(st.session_state.rec_weeks)
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            st.markdown(f"**เลือกแล้ว {len(rec_sel)} สัปดาห์**" if rec_sel else "ยังไม่ได้เลือกสัปดาห์")
        with sc2:
            st.button("ล้างการเลือก", use_container_width=True, key="rec_clear",
                      on_click=clear_rec_weeks, disabled=not rec_sel)

        if not rec_patterns or not rec_sel:
            st.info("เลือกวัน-ช่วงเวลา และอย่างน้อย 1 สัปดาห์จากปฏิทิน เพื่อดูรายการจอง")
        else:
            rec_items = rec_plan(bookings, rec_rooms, [date.fromisoformat(m) for m in rec_sel],
                                 rec_patterns, rec_qty, today_rec)
            n_free = sum(1 for x in rec_items if x["status"] == "ว่าง")
            st.markdown("##### 📋 รายการที่จะจอง")
            st.dataframe([{"วันที่": f"{WEEKDAY_TH[x['date'].weekday()]} {x['date'].strftime('%d/%m/%Y')}",
                           "ห้อง": ("X-ray 3 ห้อง" if rec_xray else r_room),
                           "ช่วงเวลา": x["slot"], "สถานะ": x["status"]} for x in rec_items],
                         hide_index=True)
            st.caption(f"จะจองได้ {n_free} จาก {len(rec_items)} ครั้ง (ครั้งที่ไม่ว่างหรือผ่านแล้วจะถูกข้าม)")

            if st.button(f"✅ ยืนยันจองประจำ ({n_free} ครั้ง)", type="primary",
                         use_container_width=True, key="rec_submit", disabled=n_free == 0):
                if not r_name.strip() or not r_phone.strip():
                    st.error("กรุณากรอกชื่อ-สกุล และเบอร์โทร/รหัสนักศึกษาในส่วนข้อมูลผู้จองด้านบน")
                else:
                    done = []
                    now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for x in rec_items:
                        if x["status"] != "ว่าง":
                            continue
                        ds = x["date"].isoformat()
                        for room_name in x["rooms"]:
                            bid = str(uuid.uuid4())[:8].upper()
                            save_one_booking({
                                "id": bid, "name": r_name.strip(), "phone_id": r_phone.strip(),
                                "user_status": r_status, "purpose": r_purpose, "item": room_name,
                                "item_type": "ห้องปฏิบัติการ", "quantity": rec_qty,
                                "date": ds, "start_date": ds, "end_date": ds, "slot": x["slot"],
                                "borrow_time": now_s, "return_time": None, "status": "ยืมอยู่",
                                "borrow_image": "", "return_image": None, "notes": "จองประจำ",
                            })
                            done.append({"วันที่": f"{WEEKDAY_TH[x['date'].weekday()]} {x['date'].strftime('%d/%m/%Y')}",
                                         "ห้อง": room_name.split(" : ")[-1],
                                         "ช่วงเวลา": x["slot"], "รหัสการจอง": bid})
                    st.session_state.bookings = load_bookings()
                    st.session_state.rec_weeks = []
                    st.session_state["rec_result"] = done
                    st.rerun()
    else:
        st.markdown("##### 📅 วันที่และช่วงเวลา")
        r_date     = st.date_input("วันที่จอง *", min_value=date.today(), key="r_date")
        r_date_str = r_date.strftime("%Y-%m-%d")

        rc1, rc2 = st.columns(2)
        with rc1: rm_start = st.selectbox("⏰ เวลาเริ่ม *", ALL_STARTS, key="rm_start")
        valid_r_ends = [e for e in ALL_ENDS if parse_time(e) > parse_time(rm_start)]
        with rc2:
            if valid_r_ends:
                rm_end = st.selectbox("⏰ เวลาสิ้นสุด *", valid_r_ends, key="rm_end")
            else:
                st.selectbox("⏰ เวลาสิ้นสุด *", ["—"], key="rm_end", disabled=True)
                rm_end = None

        r_slot = None
        if rm_end:
            r_slot = f"{rm_start}–{rm_end}"
            room_full = is_range_conflict(bookings, r_room, r_date, r_date, r_slot)

            if room_full:
                st.error("⛔ ห้องนี้เต็มในช่วงเวลาที่เลือก กรุณาเลือกเวลาอื่น")
                r_slot = None
            else:
                st.success(f"✅ ช่วงเวลาที่เลือก: {r_slot}")

        st.divider()
        st.markdown("##### 📷 รูปภาพก่อนเข้าใช้ห้อง (เพิ่มภายหลังได้)")
        r_imgs = st.file_uploader("อัปโหลดรูปภาพสภาพห้องก่อนเข้าใช้",
            type=["jpg","jpeg","png","heic","webp"], key="upload_room", accept_multiple_files=True)
        if r_imgs:
            cols_r = st.columns(min(len(r_imgs), 4))
            for i, f in enumerate(r_imgs):
                with cols_r[i % 4]: st.image(f, caption=f"รูป {i+1}", width=150)

        st.divider()

        col_rb, _ = st.columns([1, 3])
    
        with col_rb:
    
            r_submit = st.button(
                "✅ ยืนยันการจองห้อง",
                type="primary",
                use_container_width=True,
                key="r_submit"
            )
    
            if r_submit:
    
                if not r_name.strip() or not r_phone.strip():
    
                    st.error("กรุณากรอกชื่อ-สกุล และเบอร์โทร/รหัสนักศึกษา")
    
                elif not r_slot:
    
                    st.error("ไม่มีช่วงเวลาว่าง กรุณาเลือกวันอื่น")
    
                else:
    
                    bid = str(uuid.uuid4())[:8].upper()
    
                    img_path = ""
    
                    if r_imgs:
    
                        paths = save_images_multi(bid, r_imgs, "room_borrow")
                        img_path = paths_to_str(paths)
    
                    new_bk = {
                        "id": bid,
                        "name": r_name.strip(),
                        "phone_id": r_phone.strip(),
                        "user_status": r_status,
                        "purpose": r_purpose,
                        "item": r_room,
                        "item_type": "ห้องปฏิบัติการ",
                        "quantity": r_quantity,
                        "date": r_date_str,
                        "start_date": r_date_str,
                        "end_date": r_date_str,
                        "slot": r_slot,
                        "borrow_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "return_time": None,
                        "status": "ยืมอยู่",
                        "borrow_image": img_path,
                        "return_image": None,
                        "notes": "",
                    }
    
                    save_one_booking(new_bk)
    
                    # โหลดข้อมูลล่าสุดจาก Google Sheets ใหม่
                    st.session_state.bookings = load_bookings()
    
                    st.session_state["confirm_booking"] = new_bk
    
                    st.rerun()

        # ── จอง X-ray ทั้ง 3 ห้องพร้อมกัน (ใช้วันและเวลาเดียวกับที่เลือกด้านบน) ──
        if all(x in current_rooms_list() for x in XRAY_ROOMS):
            xr_done = st.session_state.pop("xray_result", None)
            if xr_done:
                st.success(f"✅ จอง X-ray 3 ห้องพร้อมกันสำเร็จ • {r_date.strftime('%d/%m/%Y')} เวลา {xr_done[0]['ช่วงเวลา']}")
                st.dataframe(xr_done, hide_index=True)
            st.markdown("##### 📷 จอง X-ray ทั้ง 3 ห้องพร้อมกัน")
            st.caption("บันทึกทั้ง 3 ห้องในวันและเวลาที่เลือก ถ้ามีห้องใดไม่ว่าง จะไม่บันทึกทั้งหมด")
            if st.button("📷 ยืนยันจอง X-ray ทั้ง 3 ห้อง (Shimadzu • DRGem • นวัตกรรม)",
                         use_container_width=True, key="r_submit_xray", disabled=not rm_end):
                if not r_name.strip() or not r_phone.strip():
                    st.error("กรุณากรอกชื่อ-สกุล และเบอร์โทรบุคลากร/รหัสนักศึกษาก่อน")
                else:
                    slot_x = f"{rm_start}–{rm_end}"
                    busy = [x for x in XRAY_ROOMS if is_range_conflict(bookings, x, r_date, r_date, slot_x)]
                    if busy:
                        st.error("⛔ ยังไม่ได้บันทึก เพราะห้องต่อไปนี้ไม่ว่างในช่วงเวลานี้: "
                                 + ", ".join(x.split(" : ")[-1] for x in busy))
                    else:
                        now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ds = r_date.strftime("%Y-%m-%d")
                        done = []
                        for x in XRAY_ROOMS:
                            bid = str(uuid.uuid4())[:8].upper()
                            save_one_booking({
                                "id": bid, "name": r_name.strip(), "phone_id": r_phone.strip(),
                                "user_status": r_status, "purpose": r_purpose, "item": x,
                                "item_type": "ห้องปฏิบัติการ", "quantity": 1,
                                "date": ds, "start_date": ds, "end_date": ds, "slot": slot_x,
                                "borrow_time": now_s, "return_time": None, "status": "ยืมอยู่",
                                "borrow_image": "", "return_image": None, "notes": "จอง X-ray พร้อมกัน 3 ห้อง",
                            })
                            done.append({"ห้อง": x.split(" : ")[-1], "ช่วงเวลา": slot_x, "รหัสการจอง": bid})
                        st.session_state.bookings = load_bookings()
                        st.session_state["xray_result"] = done
                        st.rerun()
# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ ยกเลิกห้องปฏิบัติการ
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "ยกเลิกห้อง":
    st.markdown('<div class="sec-title">❌ ยกเลิกห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    active_rooms = [b for b in bookings if b["status"]=="ยืมอยู่" and b.get("item_type")=="ห้องปฏิบัติการ"
                     and b.get("item") in current_rooms_list()]

    if not active_rooms:
        st.info("✅ ไม่มีห้องที่จองอยู่ในขณะนี้")
    else:
        rs = st.text_input("🔍 ค้นหาด้วยชื่อผู้จอง หรือ รหัสการจอง", placeholder="พิมพ์ชื่อ หรือรหัส", key="room_search")
        rf = [b for b in active_rooms if not rs or
              rs.lower() in str(b["name"]).lower() or rs.upper() in str(b["id"]).upper()]

        st.markdown(f"**พบ {len(rf)} ห้องที่จองอยู่**")

        # ── ตารางด่วน (เฉพาะแอดมิน): กดยกเลิกแล้วบันทึกทันที ไม่ต้องแนบรูป ──
        with st.expander("⚡ ตารางด่วน (แอดมิน) — กดยกเลิกเพื่อบันทึกทันที"):
            room_pin = st.text_input("🔐 รหัสแอดมิน", type="password", key="room_quick_pin")
            room_unlocked = room_pin == ADMIN_PIN
            flash = st.session_state.pop("room_quick_flash", None)
            if flash:
                st.success(flash)
            if not room_unlocked:
                st.caption("กรอกรหัสแอดมินก่อน ปุ่มยกเลิกจึงจะกดได้")
            if not rf:
                st.caption("ไม่พบรายการตามคำค้นหา")
            for i, b in enumerate(rf):
                start, end = get_date_range(b)
                date_show = start if start == end else f"{start} → {end}"
                c1, c2, c3, c4, c5 = st.columns([1.2, 1.5, 2.2, 1.9, 0.8])
                c1.caption(f"`{b['id']}`")
                c2.caption(b["name"])
                c3.caption(b["item"])
                c4.caption(f"{date_show} • {b.get('slot', '-')}")
                c5.button("ยกเลิก", key=f"quick_cancel_room_{i}_{b['id']}", disabled=not room_unlocked,
                          use_container_width=True, on_click=quick_set_status,
                          args=(b["id"], "ยกเลิกแล้ว", "ยกเลิกด่วนโดยแอดมิน", "room_quick_flash",
                                f"✅ ยกเลิกห้อง {b['item']} ของ {b['name']} แล้ว"))

        st.divider()
        st.markdown("##### 📋 รายละเอียด (แนบรูป/หมายเหตุ)")

        for i, b in enumerate(rf):
            slot_disp = b.get("slot", b.get("hour", "-"))
            start, end = get_date_range(b)
            date_show = start if start == end else f"{start} → {end}"

            with st.expander(f"🏫 [{b['id']}]  {b['name']}  —  {b['item']}  ({date_show}  {slot_disp})", expanded=False):
                ci1, ci2 = st.columns([1.5, 1])
                with ci1:
                    st.markdown(f"""| รายละเอียด | ข้อมูล |
|---|---|
| **รหัส** | `{b['id']}` |
| **ชื่อ-สกุล** | {b['name']} |
| **ห้อง** | {b['item']} |
| **วันที่** | {date_show} |
| **ช่วงเวลา** | {slot_disp} |
| **เวลาที่จอง** | {b['borrow_time']} |""")
                with ci2:
                    room_bpaths = str_to_paths(b.get("borrow_image",""))
                    if room_bpaths:
                        for i, p in enumerate(room_bpaths):
                            st.image(p, caption=f"📷 รูปก่อนใช้ {i+1}", width=180)
                    else:
                        st.caption("ไม่มีรูปก่อนใช้")

                if not b.get("borrow_image"):
                    st.markdown("**📷 เพิ่มรูปก่อนเข้าใช้ห้อง (ภายหลัง)**")
                    add_rborrow_imgs = st.file_uploader("อัปโหลดรูปก่อนเข้าใช้ห้อง",
                        type=["jpg","jpeg","png","heic","webp"], key=f"add_rborrow_{i}_{b['id']}", accept_multiple_files=True)
                    if add_rborrow_imgs:
                        cols_arb = st.columns(min(len(add_rborrow_imgs), 4))
                        for j, f in enumerate(add_rborrow_imgs):
                            with cols_arb[j % 4]: st.image(f, caption=f"รูป {j+1}", width=130)
                        if st.button("💾 บันทึกรูปก่อนใช้ห้อง", key=f"save_rborrow_{i}_{b['id']}"):
                            new_paths = save_images_multi(b["id"], add_rborrow_imgs, "room_borrow_add")
                            for bk in bookings:
                                if bk["id"] == b["id"]:
                                    existing = str_to_paths(bk.get("borrow_image",""))
                                    bk["borrow_image"] = paths_to_str(existing + new_paths)
                            save_bookings(bookings)
                            st.session_state.bookings = bookings
                            st.success(f"✅ บันทึก {len(new_paths)} รูปแล้ว"); st.rerun()

                st.markdown("**📷 รูปภาพสภาพห้องหลังใช้งาน**")
                ret_imgs_r = st.file_uploader("อัปโหลดรูปภาพสภาพห้องหลังใช้",
                    type=["jpg","jpeg","png","heic","webp"], key=f"upload_rret_{i}_{b['id']}", accept_multiple_files=True)
                if ret_imgs_r:
                    cols_rr = st.columns(min(len(ret_imgs_r), 4))
                    for j, f in enumerate(ret_imgs_r):
                        with cols_rr[j % 4]: st.image(f, caption=f"รูป {j+1}", width=130)

                ret_notes = st.text_input("หมายเหตุ / สภาพห้อง", placeholder="เช่น ห้องสะอาด อุปกรณ์ครบ", key=f"rnote_{i}_{b['id']}")
                col_r2, _ = st.columns([1, 3])
                with col_r2:
                    if st.button("✅ ยืนยันการยกเลิกห้อง", key=f"rret_{i}_{b['id']}", type="primary", use_container_width=True):
                        img_path = ""
                        if ret_imgs_r:
                            paths = save_images_multi(b["id"], ret_imgs_r, "room_return")
                            img_path = paths_to_str(paths)
                        _ret_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        update_booking_status(b["id"], "ยกเลิกแล้ว", _ret_time, img_path, ret_notes)
                        for bk in bookings:
                            if bk["id"] == b["id"]:
                                bk["status"] = "ยกเลิกแล้ว"; bk["return_time"] = _ret_time
                                bk["return_image"] = img_path; bk["notes"] = ret_notes
                        st.session_state.bookings = bookings
                        st.success(f"✅ ยกเลิกห้อง [{b['id']}] เรียบร้อย!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ จองอาจารย์สอบ Oral
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "จองอาจารย์":
    st.markdown('<div class="sec-title">🎓 จองอาจารย์สอบ Oral Exam (515113)</div>', unsafe_allow_html=True)
    if st.session_state.get("oe_flash"):
        st.success(st.session_state.pop("oe_flash"))
    st.markdown(
        f"<div style='font-size:.85rem;color:#607d8b;margin-bottom:.6rem'>"
        f"📅 จันทร์ – ศุกร์ • เวลา {ORAL_SLOTS[0].split('–')[0]}–{ORAL_SLOTS[-1].split('–')[1]} น. "
        f"• จองได้ครั้งละ {ORAL_SLOT_MIN} นาที • จองซ้ำช่วงเวลาเดิมไม่ได้ • ปิดรับจองเวลา 22:00 น. ของ 2 วันก่อนวันสอบ</div>",
        unsafe_allow_html=True)

    st.markdown("##### 👩‍🏫 เลือกอาจารย์ผู้สอบ")
    adv_cols = st.columns(len(ORAL_ADVISORS))
    for col, name in zip(adv_cols, ORAL_ADVISORS):
        with col:
            is_sel = st.session_state.get("oe_advisor") == name
            if st.button(f"🎓  {name}", use_container_width=True, key=f"oe_adv_{name}",
                         type="primary" if is_sel else "secondary"):
                st.session_state.oe_advisor = name
                st.rerun()

    adv = st.session_state.get("oe_advisor")
    if not adv:
        st.info("👆 กรุณาเลือกอาจารย์ เพื่อดูปฏิทินการจอง")
    else:
        today_obj = oral_today()
        st.session_state.setdefault("oe_year", today_obj.year)
        st.session_state.setdefault("oe_month", today_obj.month)
        st.divider()
        st.markdown(f"#### 🗓️ ปฏิทินของ {adv}")

        nv1, nv2, nv3 = st.columns([1, 3, 1])
        with nv1:
            if st.button("◀ เดือนก่อน", use_container_width=True, key="oe_prev"):
                if st.session_state.oe_month == 1:
                    st.session_state.oe_month = 12
                    st.session_state.oe_year -= 1
                else:
                    st.session_state.oe_month -= 1
                st.rerun()
        with nv2:
            st.markdown(
                f"<h3 style='text-align:center;font-family:Prompt;color:#0d2137;margin:4px 0'>"
                f"{MONTH_TH[st.session_state.oe_month]} {st.session_state.oe_year + 543}</h3>",
                unsafe_allow_html=True)
        with nv3:
            if st.button("เดือนถัดไป ▶", use_container_width=True, key="oe_next"):
                if st.session_state.oe_month == 12:
                    st.session_state.oe_month = 1
                    st.session_state.oe_year += 1
                else:
                    st.session_state.oe_month += 1
                st.rerun()

        yr, mo = st.session_state.oe_year, st.session_state.oe_month
        rows = load_oral()
        hdr = st.columns(7)
        for i, dl in enumerate(["จันทร์", "อังคาร", "พุธ", "พฤหัส", "ศุกร์", "เสาร์", "อาทิตย์"]):
            color = "#c62828" if i >= 5 else "#546e7a"
            hdr[i].markdown(
                f"<div style='text-align:center;font-weight:700;font-size:.85rem;color:{color};"
                f"background:#f0f4f8;border-radius:6px;padding:6px 0'>{dl}</div>",
                unsafe_allow_html=True)
        st.markdown("<div style='margin:4px 0'></div>", unsafe_allow_html=True)

        total = len(ORAL_SLOTS)
        for week in calendar.monthcalendar(yr, mo):
            wcols = st.columns(7)
            for ci, d in enumerate(week):
                with wcols[ci]:
                    if d == 0:
                        st.markdown("<div style='height:64px'></div>", unsafe_allow_html=True)
                        continue
                    d_obj = date(yr, mo, d)
                    ds = d_obj.strftime("%Y-%m-%d")
                    if d_obj < today_obj or ci >= 5:   # ผ่านมาแล้ว หรือเสาร์-อาทิตย์
                        st.markdown("<div class='cal-cell-marker oe-off'></div>", unsafe_allow_html=True)
                        st.button(f"{d}\n\n{'ปิด' if ci >= 5 else '—'}", key=f"oe_day_{ds}",
                                  use_container_width=True, disabled=True)
                        continue
                    booked, blocked = oral_day_state(rows, adv, ds)
                    free_n = sum(1 for s in ORAL_SLOTS
                                 if s not in booked and s not in blocked
                                 and not oral_slot_passed(d_obj, s))
                    if oral_booking_closed(d_obj):
                        cls, txt = "oe-off", "ปิดจอง"
                    elif free_n == 0:
                        cls, txt = ("oe-off", "ไม่ว่าง") if blocked else ("oe-full", "เต็ม")
                    elif booked or blocked:
                        cls, txt = "oe-part", f"ว่าง {free_n}/{total}"
                    else:
                        cls, txt = "oe-free", "ว่าง"
                    st.markdown(f"<div class='cal-cell-marker {cls}'></div>", unsafe_allow_html=True)
                    if st.button(f"{d}\n\n{txt}", key=f"oe_day_{ds}", use_container_width=True):
                        st.session_state.oe_selected_date = ds
                        st.rerun()

        st.markdown(
            "<div style='font-size:.72rem;color:#607d8b;margin-top:6px'>"
            "🟩 ว่าง &nbsp;|&nbsp; 🟨 มีบางช่วงถูกจอง/ตั้งไม่ว่าง &nbsp;|&nbsp; 🟥 เต็ม &nbsp;|&nbsp; "
            "⬜ ไม่ว่างทั้งวัน / ปิดทำการ / ผ่านมาแล้ว<br>"
            "กดที่วันที่ เพื่อจองคิว หรือตั้งเป็นไม่ว่าง</div>",
            unsafe_allow_html=True)

    # ── ตารางรายชื่อผู้จองคิว เลือกวันที่ดูได้ ──
    st.divider()
    st.markdown("#### 📋 รายชื่อผู้จองคิว")
    list_day = st.date_input("📅 เลือกวันที่ต้องการดู", value=oral_today(),
                             key="oe_list_date", format="DD/MM/YYYY")
    list_ds = list_day.strftime("%Y-%m-%d")
    list_rows = oral_bookings_on(load_oral(), list_ds)
    if not list_rows:
        st.info(f"ยังไม่มีการจองในวันที่ {list_day.strftime('%d/%m/%Y')}")
    else:
        st.caption(f"วันที่ {list_day.strftime('%d/%m/%Y')} • จองแล้ว {len(list_rows)} คิว")
        st.dataframe([
            {"เวลา": r.get("slot"), "อาจารย์": r.get("advisor"),
             "ชื่อ-สกุล": r.get("name"), "สถานะ": r.get("user_status"),
             "หัวข้อ": r.get("purpose") or "—"}
            for r in list_rows
        ], hide_index=True)

    with st.expander("🔐 แอดมิน: ลบการจอง (ต้องใช้รหัสแอดมิน)"):
        if not list_rows:
            st.caption("ไม่มีการจองให้ลบในวันที่เลือก")
        else:
            pick_map = {f"{r.get('slot')} • {r.get('advisor')} • {r.get('name')}": r.get("id")
                        for r in list_rows}
            pick = st.selectbox("เลือกการจองที่ต้องการลบ", list(pick_map.keys()),
                                key="oe_del_pick")
            admin_pin = st.text_input("รหัสแอดมิน *", type="password", key="oe_del_pin")
            if st.button("🗑️ ยืนยันลบการจองนี้", type="primary", key="oe_del_go"):
                if not admin_pin:
                    st.error("กรุณากรอกรหัสแอดมินก่อนยืนยันลบ")
                elif admin_pin != ADMIN_PIN:
                    st.error("รหัสแอดมินไม่ถูกต้อง ยังไม่ได้ลบ")
                elif cancel_oral_rows([pick_map[pick]]):
                    st.session_state.oe_flash = (
                        f"🗑️ ลบการจอง {pick} แล้ว (เก็บประวัติเป็นสถานะยกเลิก คิวนี้ว่างให้จองใหม่ได้)")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ ปฏิทิน
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "ปฏิทิน":
    st.markdown('<div class="sec-title">🗓️ ปฏิทินการยืมอุปกรณ์และการจองห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("◀ เดือนก่อน", use_container_width=True):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12; st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.rerun()
    with nav2:
        st.markdown(f"<h3 style='text-align:center;font-family:Prompt;color:#0d2137;margin:4px 0'>📅 {MONTH_TH[st.session_state.cal_month]} {st.session_state.cal_year + 543}</h3>", unsafe_allow_html=True)
    with nav3:
        if st.button("เดือนถัดไป ▶", use_container_width=True):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1; st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.rerun()

    all_items = ["ทั้งหมด"] + EQUIPMENT_LIST + ALL_ROOMS
    fil_item = st.selectbox("กรองตามอุปกรณ์/ห้อง", all_items, key="cal_filter")
    yr = st.session_state.cal_year
    mo = st.session_state.cal_month

    def day_count(d):
        ds_date = date(yr, mo, d)
        def safe_to_date(x):
            if not x: return None
            return datetime.strptime(x, "%Y-%m-%d").date() if isinstance(x, str) else x
        return sum(1 for b in bookings if
            b.get("status") != "คืนแล้ว" and
            (fil_item == "ทั้งหมด" or b.get("item") == fil_item
             or (fil_item == OTHER_EQUIP and is_other_item(b.get("item")))) and
            (lambda s,e: s and e and s <= ds_date <= e)(
                safe_to_date(b.get("start_date") or b.get("date")),
                safe_to_date(b.get("end_date") or b.get("date"))))

    cal_matrix = calendar.monthcalendar(yr, mo)
    days_label = ["จันทร์","อังคาร","พุธ","พฤหัส","ศุกร์","เสาร์","อาทิตย์"]
    
    hdr_cols = st.columns(7)
    for i, dl in enumerate(days_label):
        color = "#c62828" if i == 6 else "#546e7a"
        hdr_cols[i].markdown(
            f"<div style='text-align:center;font-weight:700;font-size:.85rem;color:{color};"
            f"background:#f0f4f8;border-radius:6px;padding:6px 0'>{dl}</div>",
            unsafe_allow_html=True)
    
    st.markdown("<div style='margin:4px 0'></div>", unsafe_allow_html=True)
    
    today_obj = date.today()
    for week in cal_matrix:
        week_cols = st.columns(7)
        for col_i, d in enumerate(week):
            with week_cols[col_i]:
                if d == 0:
                    st.markdown("<div style='height:64px'></div>", unsafe_allow_html=True)
                    continue
                cnt = day_count(d)
                is_today = (d == today_obj.day and mo == today_obj.month and yr == today_obj.year)
    
                marker_cls = "cal-cell-marker"
                if is_today: marker_cls += " cal-today"
                elif cnt > 0: marker_cls += " cal-has"
    
                label = f"{d}\n\n{cnt} รายการ" if cnt > 0 else f"{d}\n\n\u00A0"
    
                st.markdown(f"<div class='{marker_cls}'></div>", unsafe_allow_html=True)
                if st.button(label, key=f"cal_day_{yr}_{mo}_{d}", use_container_width=True):
                    st.session_state.cal_selected_date = date(yr, mo, d).strftime("%Y-%m-%d")
                    st.rerun()

    st.divider()
    st.markdown("#### 🔍 รายการจองตามวันที่")
    sel_date = st.date_input("เลือกวันที่", value=today_obj, key="cal_dt")
    sel_ds   = sel_date.strftime("%Y-%m-%d")
    day_bks  = [b for b in bookings if b.get("status") != "ยกเลิกแล้ว" and
                (b.get("start_date") or b.get("date","")) <= sel_ds <= (b.get("end_date") or b.get("date",""))]

    if not day_bks:
        st.info(f"ไม่มีการจองในวันที่ {sel_ds}")
    else:
        for b in sorted(day_bks, key=lambda x: x.get("slot","")):
            pill = '<span class="slot-pill pill-booked">ยืมอยู่</span>' if b["status"]=="ยืมอยู่" else '<span class="slot-pill pill-returned">คืนแล้ว</span>'
            st.markdown(f"""<div style='background:white;border-radius:10px;padding:.7rem 1.1rem;margin-bottom:.4rem;
                box-shadow:0 1px 8px rgba(0,0,0,.07);border-left:3.5px solid #1565c0;
                display:flex;justify-content:space-between;align-items:center'>
                <div><b style='color:#0d2137'>{b.get('slot','-')}</b>&nbsp;—&nbsp;{b['item']}
                <br><small style='color:#607d8b'>{b['name']}&nbsp;|&nbsp;{str(b.get('user_status',''))[:30]}</small></div>
                {pill}</div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### ⏰ ตารางความว่างรายชั่วโมง")
    h1, h2 = st.columns([2, 1])
    with h1: avail_item = st.selectbox("เลือกอุปกรณ์/ห้อง", EQUIPMENT_LIST + ALL_ROOMS, key="avail_item")
    with h2: avail_date = st.date_input("วันที่", value=today_obj, key="avail_date")
    avail_ds = avail_date.strftime("%Y-%m-%d")
    cols = st.columns(len(TIME_SLOTS))
    for i, slot in enumerate(TIME_SLOTS):
        taken = is_slot_taken(bookings, avail_item, avail_ds, slot)
        lbl = slot.replace("–","<br>")
        with cols[i]:
            if taken: st.markdown(f'<div class="hour-box hour-taken">{lbl}<br>❌</div>', unsafe_allow_html=True)
            else:     st.markdown(f'<div class="hour-box hour-free">{lbl}<br>✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ สรุป
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "สรุป":
    st.markdown('<div class="sec-title">📊 สรุปการใช้งานอุปกรณ์และห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    total      = len(bookings)
    active_n   = sum(1 for b in bookings if b["status"]=="ยืมอยู่")
    returned_n = sum(1 for b in bookings if b["status"]=="คืนแล้ว")
    today_str  = date.today().strftime("%Y-%m-%d")
    today_n    = sum(1 for b in bookings if (b.get("start_date") or b.get("date","")) == today_str)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="stat-card"><h3>{total}</h3><p>🗂️ รายการทั้งหมด</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card orange"><h3>{active_n}</h3><p>📤 กำลังยืมอยู่</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card green"><h3>{returned_n}</h3><p>📥 คืนแล้ว</p></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="stat-card red"><h3>{today_n}</h3><p>📅 จองวันนี้</p></div>', unsafe_allow_html=True)

    st.divider()
    f1, f2, f3 = st.columns(3)
    with f1: flt_status = st.selectbox("สถานะ", ["ทั้งหมด","ยืมอยู่","คืนแล้ว","ยกเลิกแล้ว"])
    with f2: flt_type   = st.selectbox("ประเภท", ["ทั้งหมด","อุปกรณ์","ห้องปฏิบัติการ"])
    with f3: dr         = st.date_input("ช่วงวันที่", value=(date.today()-timedelta(days=30), date.today()), key="sum_dr")

    flt = bookings[:]
    if flt_status != "ทั้งหมด": flt = [b for b in flt if b.get("status")==flt_status]
    if flt_type   != "ทั้งหมด": flt = [b for b in flt if b.get("item_type","อุปกรณ์")==flt_type]
    if isinstance(dr,(list,tuple)) and len(dr)==2:
        s_str = dr[0].strftime("%Y-%m-%d"); e_str = dr[1].strftime("%Y-%m-%d")
        flt = [b for b in flt if (b.get("start_date") or b.get("date","")) <= e_str and
               (b.get("end_date") or b.get("date","")) >= s_str]

    st.markdown(f"#### 📋 ตารางรายการจอง ({len(flt)} รายการ)")
    if not flt:
        st.info("ไม่พบข้อมูลตามเงื่อนไข")
    else:
        rows = ""
        for b in sorted(flt, key=lambda x: (get_date_range(x)[0] or "")+(x.get("slot","")), reverse=True):
            start, end = get_date_range(b)
            date_show = start if start == end else f"{start} → {end}"
            pill = '<span class="slot-pill pill-booked">ยืมอยู่</span>' if b["status"]=="ยืมอยู่" else '<span class="slot-pill pill-returned">คืนแล้ว</span>'
            rows += f"""<tr>
                <td><code>{b['id']}</code></td><td>{b['name']}</td>
                <td style='text-align:left'>{b['item']}</td><td>{date_show}</td>
                <td style='white-space:nowrap'>{b.get('slot','-')}</td><td>{b.get('quantity',1)}</td>
                <td style='white-space:nowrap'>{b['borrow_time'][:16] if b.get('borrow_time') else '-'}</td>
                <td style='white-space:nowrap'>{b['return_time'][:16] if b.get('return_time') else '-'}</td>
                <td>{pill}</td><td>{b.get('notes','') or '-'}</td></tr>"""
        st.markdown(f"""<div style='overflow-x:auto'><table class="sum-table">
            <thead><tr><th>รหัส</th><th>ชื่อ</th><th>อุปกรณ์/ห้อง</th><th>วันที่</th>
            <th>เวลา</th><th>จำนวน</th><th>เวลายืม</th><th>เวลาคืน</th><th>สถานะ</th><th>หมายเหตุ</th></tr></thead>
            <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

    if bookings:
        st.divider()
        st.markdown("#### 🏆 อุปกรณ์/ห้องที่มีการจองสูงสุด")
        top = Counter(b["item"] for b in bookings).most_common(12)
        if top:
            df_c = pd.DataFrame({"รายการ":[t[0][:35] for t in top],"จำนวนครั้ง":[t[1] for t in top]})
            st.bar_chart(df_c.set_index("รายการ"))
        st.divider()
        df_ex = pd.DataFrame(bookings).drop(columns=["borrow_image","return_image"], errors="ignore")
        csv = df_ex.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Export ข้อมูลเป็น CSV", csv, "rt_bookings.csv", "text/csv")
