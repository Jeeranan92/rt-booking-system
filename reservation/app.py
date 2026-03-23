import streamlit as st
import json
import os
from datetime import datetime, date, timedelta
import calendar
import uuid
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import cloudinary
import cloudinary.uploader
import io
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

# ─── Google Sheets setup ──────────────────────────────────────────────────────
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# ตั้งค่า: ใส่ SHEET_ID ของคุณตรงนี้
SHEET_ID = "1yWLwkCDuagzpBajvphTtSD9i_MiunH20aUO_slOPD9g"
CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")

COLUMNS = ["id","name","phone_id","user_status","purpose","item","item_type",
           "quantity","date","slot","borrow_time","return_time","status",
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

def _use_gsheets():
    return GSHEETS_AVAILABLE and "gcp" in st.secrets and SHEET_ID != "YOUR_GOOGLE_SHEET_ID_HERE"

def _load_icon():
    import os as _os
    from PIL import Image as _Img
    _candidates = [
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "RT CMU Logo.ico"),
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "RT CMU Logo.png"),
        "c:/Users/adminnistrator/Downloads/reservation/RT CMU Logo.ico",
        "c:/Users/adminnistrator/Downloads/reservation/RT CMU Logo.png",
    ]
    for _p in _candidates:
        if _os.path.exists(_p):
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

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&family=Prompt:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #0d2137 0%, #1565c0 55%, #0288d1 100%);
    padding: 1.8rem 2.5rem;
    border-radius: 18px;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(13,110,253,0.22);
    display: flex;
    align-items: center;
    gap: 1.5rem;
}
.main-header h1 { font-family:'Prompt'; font-size:1.7rem; font-weight:800; margin:0; }
.main-header p  { margin:0; opacity:.85; font-size:.9rem; }

.stat-card {
    background:white; border-radius:14px; padding:1.2rem 1.5rem;
    box-shadow:0 2px 14px rgba(0,0,0,.08); border-left:5px solid #1565c0;
    margin-bottom:1rem;
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

.slot-pill {
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:.72rem; font-weight:700; letter-spacing:.3px;
}
.pill-booked   { background:#fde8e8; color:#c62828; border:1px solid #ffcdd2; }
.pill-returned { background:#e3f2fd; color:#1565c0; border:1px solid #bbdefb; }

.hour-box {
    text-align:center; border-radius:8px; padding:6px 2px;
    font-size:.7rem; font-weight:700; line-height:1.4;
}
.hour-free  { background:#e8f5e9; color:#2e7d32; border:1.5px solid #a5d6a7; }
.hour-taken { background:#fde8e8; color:#c62828; border:1.5px solid #ef9a9a; }

.cal-wrap { overflow-x:auto; margin-top:.5rem; }
.cal-table { width:100%; border-collapse:separate; border-spacing:4px; table-layout:fixed; }
.cal-th { text-align:center; padding:8px 4px; font-weight:700; font-size:.85rem; color:#546e7a;
          background:#f0f4f8; border-radius:6px; }
.cal-th.cal-sun { color:#c62828; }
.cal-td {
    border-radius:10px; padding:6px 4px; min-height:70px;
    background:#f8fafc; vertical-align:top; text-align:center;
    border:1.5px solid transparent;
}
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
            
/* ปุ่มย้อนกลับ / หน้าแรก */
div[data-testid="column"]:has(button[kind="secondary"]#btn_back) button,
div[data-testid="column"]:has(button[kind="secondary"]#btn_home_top) button {
    border-radius: 20px !important;
    font-size: .82rem !important;
    padding: 4px 12px !important;
            
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
DATA_FILE  = "bookings.json"
IMAGES_DIR = "booking_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

EQUIPMENT_LIST = [
    "IC and Solid state box set : Radcal",
    "OSL reader: microStar",
    "MCA : NaI(Te)",
    "SCA พร้อม หัววัด NaI(Te)",
    "Computer : HP",
    "Computer : ASUS",
    "Computer : Lenovo",
    "Computer : Acer",
    "Parallel plate",
    "Digital caliper",
    "เครื่องวัดรังสี Digital (neutron) LUDLUM",
    "Survey meter/Geiger muller แบบเข็ม LUDLUM",
    "Survey meter แบบเข็ม สทน.",
    "Survey meter/Geiger muller แบบdigital : LUDLUM",
    "Digital barometer - วัดอุณหภูมิ ความดัน",
    "Build up cap(high energy)",
    "IC แบบ cylindrical",
    "Pocket dose meter",
    "ชุดหัววัด Cd-Te",
    "แผ่น DR",
    "แผ่น CR ใหญ่",
    "แผ่น CR เล็ก",
    "HVL",
    "ขาตั้งกล้อง",
    "แผ่น filter : Pb AL Cu",
    "View box",
    "Roll up",
    "Backdrop",
    "อื่นๆ",
]

ROOMS_LIST = [
    "ห้องปฏิบัติการ CT Scan",
    "ห้องปฏิบัติการ X-Ray : Shimadzu",
    "ห้องปฏิบัติการ X-Ray : DRGem",
    "ห้องปฏิบัติการ X-Ray : นวัตกรรม",
    "ห้องปฏิบัติการ US (อัลตราซาวด์)",
    "ห้องปฏิบัติการคอมพิวเตอร์",
    "ห้องบรรยาย2 อาคาร3 ชั้น1",
    "ห้องตรวจมวลกระดูก BMD : HOLOGIC",
]

STATUS_OPTIONS = [
    "อาจารย์ประจำภาควิชารังสีเทคนิค",
    "บุคลากรประจำภาควิชารังสีเทคนิค",
    "นักศึกษารังสีเทคนิค ชั้นปีที่ 1",
    "นักศึกษารังสีเทคนิค ชั้นปีที่ 2",
    "นักศึกษารังสีเทคนิค ชั้นปีที่ 3",
    "นักศึกษารังสีเทคนิค ชั้นปีที่ 4",
    "บุคลากรภายนอก สังกัดคณะเทคนิคการแพทย์",
    "บุคลากรภายนอก สังกัดอื่นๆ",
]

# เวลา 08:30–16:30 ทุกชั่วโมง
# TIME_SLOTS ใช้สำหรับปฏิทิน/ตารางภาพรวม (ทุก 30 นาที)
ALL_STARTS = ["08:30","09:00","09:30","10:00","10:30","11:00","11:30",
              "12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30"]
ALL_ENDS   = ["09:00","09:30","10:00","10:30","11:00","11:30","12:00",
              "12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00","16:30"]
TIME_SLOTS = [f"{s}–{e}" for s,e in zip(ALL_STARTS, ["09:00","09:30","10:00","10:30","11:00","11:30","12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00"])]

MONTH_TH = ["","มกราคม","กุมภาพันธ์","มีนาคม","เมษายน",
            "พฤษภาคม","มิถุนายน","กรกฎาคม","สิงหาคม",
            "กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]

# ─── Data helpers ─────────────────────────────────────────────────────────────
def load_bookings():
    """โหลดจาก Google Sheets ถ้าพร้อม ไม่งั้นใช้ JSON"""
    if _use_gsheets():
        try:
            ws = get_sheet()
            if ws:
                rows = ws.get_all_records()
                # แปลง string กลับเป็น type ที่ถูกต้อง
                for r in rows:
                    r["quantity"] = int(r.get("quantity", 1) or 1)
                    if r.get("return_time") == "": r["return_time"] = None
                    if r.get("borrow_image") == "": r["borrow_image"] = None
                    if r.get("return_image") == "": r["return_image"] = None
                return rows
        except Exception as e:
            st.warning(f"โหลดจาก Sheets ไม่ได้: {e}")
    # fallback JSON
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_bookings(data):
    """บันทึกลง Google Sheets + JSON backup"""
    # บันทึก JSON เสมอ (backup)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if _use_gsheets():
        try:
            ws = get_sheet()
            if ws:
                ws.clear()
                ws.insert_row(COLUMNS, 1)
                rows_to_write = []
                for b in data:
                    row = [str(b.get(col, "") or "") for col in COLUMNS]
                    rows_to_write.append(row)
                if rows_to_write:
                    ws.append_rows(rows_to_write, value_input_option="RAW")
        except Exception as e:
            st.warning(f"บันทึกลง Sheets ไม่ได้: {e} — บันทึก JSON แล้ว")

def save_one_booking(b):
    """เพิ่ม row เดียวลง Sheets (เร็วกว่า save ทั้งหมด)"""
    if _use_gsheets():
        try:
            ws = get_sheet()
            if ws:
                row = [str(b.get(col, "") or "") for col in COLUMNS]
                ws.append_row(row, value_input_option="RAW")
                return
        except Exception as e:
            st.warning(f"เพิ่มแถวใน Sheets ไม่ได้: {e}")
    # fallback: save ทั้งหมด
    all_bks = load_bookings()
    all_bks.append(b)
    save_bookings(all_bks)

def update_booking_status(bid, status, return_time, return_image, notes):
    """อัปเดตสถานะใน Sheets หรือ JSON"""
    if _use_gsheets():
        try:
            ws = get_sheet()
            if ws:
                cell = ws.find(bid)
                if cell:
                    row = cell.row
                    status_col    = COLUMNS.index("status") + 1
                    ret_time_col  = COLUMNS.index("return_time") + 1
                    ret_img_col   = COLUMNS.index("return_image") + 1
                    notes_col     = COLUMNS.index("notes") + 1
                    ws.update_cell(row, status_col,   status)
                    ws.update_cell(row, ret_time_col, return_time or "")
                    ws.update_cell(row, ret_img_col,  return_image or "")
                    ws.update_cell(row, notes_col,    notes or "")
                    return
        except Exception as e:
            st.warning(f"อัปเดต Sheets ไม่ได้: {e}")
    # fallback JSON
    all_bks = load_bookings()
    for bk in all_bks:
        if bk["id"] == bid:
            bk["status"]       = status
            bk["return_time"]  = return_time
            bk["return_image"] = return_image
            bk["notes"]        = notes
    save_bookings(all_bks)

def parse_time(t):
    """แปลง HH:MM เป็นนาที"""
    h, m = map(int, t.split(":"))
    return h * 60 + m

def slots_overlap(s1, s2):
    """เช็กว่า 2 ช่วงเวลา overlap กันหรือไม่"""
    try:
        a_start, a_end = s1.split("–")
        b_start, b_end = s2.split("–")
        return parse_time(a_start) < parse_time(b_end) and parse_time(b_start) < parse_time(a_end)
    except:
        return s1 == s2  # fallback สำหรับข้อมูลเก่า

def is_slot_taken(bks, item, date_str, slot):
    for b in bks:
        b_slot = b.get("slot", b.get("hour", ""))
        if b["item"] == item and b["date"] == date_str and b["status"] != "ยกเลิกแล้ว":
            if slots_overlap(slot, b_slot):
                return b
    return None

def add_watermark(file, text="RT CMU"):
    img = Image.open(file).convert("RGBA")

    width, height = img.size

    # layer สำหรับวาด
    txt_layer = Image.new("RGBA", img.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt_layer)

    # font (fallback ถ้าไม่มี)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    # ข้อความ watermark
    watermark_text = f"{text} | {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # ตำแหน่งล่างขวา
    text_w, text_h = draw.textbbox((0,0), watermark_text, font=font)[2:]
    position = (width - text_w - 20, height - text_h - 20)

    # วาดข้อความ (โปร่งใส)
    draw.text(position, watermark_text, fill=(255,255,255,180), font=font)

    # รวมภาพ
    combined = Image.alpha_composite(img, txt_layer)

    # แปลงกลับเป็น bytes
    output = io.BytesIO()
    combined.convert("RGB").save(output, format="JPEG")
    output.seek(0)

    return output
def upload_to_drive(file, filename, folder="rtcmu_booking"):
    # ตั้งค่า Cloudinary
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key    = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"]
    )

    # ใส่ watermark ก่อน upload
    file_stream = add_watermark(file)

    # Upload ไป Cloudinary
    result = cloudinary.uploader.upload(
        file_stream,
        folder="rtcmu_booking",
        public_id=filename.replace(".", "_"),
        overwrite=True,
        resource_type="image"
    )

    return result.get("secure_url", "")

def save_image(bid, img_bytes, prefix):
    """บันทึกรูปภาพ รองรับ bytes หรือ UploadedFile"""
    path = os.path.join(IMAGES_DIR, f"{prefix}_{bid}.jpg")
    data = img_bytes.read() if hasattr(img_bytes, "read") else img_bytes
    with open(path, "wb") as f:
        f.write(data)
    return path

def save_images_multi(bid, files, prefix):
    urls = []
    for i, f in enumerate(files):
        filename = f"{prefix}_{bid}_{i+1}_{f.name}"
        if "return" in prefix:
            fold = "rtcmu_booking/after"
        else:
            fold = "rtcmu_booking/before"
        url = upload_to_drive(f, filename, folder=fold)
        if url:
            urls.append(url)
    return urls

def paths_to_str(paths):
    """แปลง list path เป็น string คั่นด้วย |"""
    if isinstance(paths, list):
        return "|".join(paths)
    return paths or ""

def str_to_paths(s):
    """แปลง string กลับเป็น list path"""
    if not s:
        return []
    if isinstance(s, list):
        return s
    return [p for p in s.split("|") if p]

def add_image_to_booking(bid, img_file, prefix):
    """เพิ่ม/อัปเดตรูปภาพในการจองที่มีอยู่แล้ว"""
    path = save_image(bid, img_file, prefix)
    bookings_data = load_bookings()
    for bk in bookings_data:
        if bk["id"] == bid:
            if prefix.startswith("borrow") or prefix == "room_borrow":
                bk["borrow_image"] = path
            else:
                bk["return_image"] = path
    save_bookings(bookings_data)
    return path

# ─── Session state ─────────────────────────────────────────────────────────────
today = date.today()
defaults = {
    "page": "หน้าแรก",
    "cal_year": today.year,
    "cal_month": today.month,
    "bookings": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.bookings is None:
    st.session_state.bookings = load_bookings()

bookings = st.session_state.bookings
active_cnt = sum(1 for b in bookings if b["status"] == "ยืมอยู่")

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # โหลดโลโก้สำหรับ sidebar
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
        <div style='font-size:.72rem;color:#90caf9;opacity:.7'>ระบบการจองห้องปฏิบัติการ และการยืม-คืนเครื่องมือ และอุปกรณ์ ภาควิชารังสีเทคนิค</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # หน้าแรก
    if st.button("🏠  หน้าแรก", use_container_width=True,
                 type="primary" if st.session_state.page == "หน้าแรก" else "secondary",
                 key="nav_หน้าแรก"):
        st.session_state.page = "หน้าแรก"
        st.rerun()

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # กลุ่ม 1: อุปกรณ์
    st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>🔬 อุปกรณ์</div>", unsafe_allow_html=True)
    for label, key in [("📋  ยืมอุปกรณ์", "ยืมอุปกรณ์"), ("📦  คืนอุปกรณ์", "คืนอุปกรณ์")]:
        if st.button(label, use_container_width=True,
                     type="secondary" if st.session_state.page == key else "secondary",
                     key=f"nav_{key}"):
            st.session_state.page = key
            st.rerun()

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # กลุ่ม 2: ห้องปฏิบัติการ
    st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>🏫 ห้องปฏิบัติการ</div>", unsafe_allow_html=True)
    for label, key in [("📅  จองห้อง", "จองห้อง"), ("❌  ยกเลิกห้อง", "ยกเลิกห้อง")]:
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.page == key else "secondary",
                     key=f"nav_{key}"):
            st.session_state.page = key
            st.rerun()

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # กลุ่ม 3: ภาพรวม
    st.markdown("<div style='font-size:.72rem;font-weight:700;color:#ffcc02;letter-spacing:1px;padding:4px 0'>📊 ภาพรวม</div>", unsafe_allow_html=True)
    for label, key in [("🗓️  ปฏิทินการจอง", "ปฏิทิน"), ("📊  สรุปการใช้งาน", "สรุป")]:
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.page == key else "secondary",
                     key=f"nav_{key}"):
            st.session_state.page = key
            st.rerun()

    st.divider()
    active_eq   = sum(1 for b in bookings if b["status"] == "ยืมอยู่" and b.get("item_type") == "อุปกรณ์")
    active_room = sum(1 for b in bookings if b["status"] == "ยืมอยู่" and b.get("item_type") == "ห้องปฏิบัติการ")
    st.markdown(f"""
    <div style='font-size:.78rem;color:#90caf9;text-align:center;line-height:1.8'>
        🔬 ยืมอุปกรณ์อยู่ <b style='color:#ffcc02'>{active_eq}</b> รายการ<br>
        🏫 จองห้องอยู่ <b style='color:#ffcc02'>{active_room}</b> รายการ<br>
        <span style='opacity:.65;font-size:.68rem'>พบปัญหาติดต่อ จีรนันท์<br>065-5354782</span>
    </div>
    """, unsafe_allow_html=True)

# ─── Main header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div style='font-size:3.2rem'>
    <div>
        <h2>ระบบการจองห้องปฏิบัติการ และการยืม-คืนเครื่องมือ และอุปกรณ์</h2>
        <p>ภาควิชารังสีเทคนิค • คณะเทคนิคการแพทย์ • มหาวิทยาลัยเชียงใหม่</p>
        <p>📅 เปิดบริการ • วันเวลาราชการ • วันจันทร์ - วันศุกร์ • เวลา 08:30–16:30 น. • (หยุดวันนักขัตฤกษ์)</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── ปุ่มย้อนกลับ (แสดงทุกหน้ายกเว้นหน้าแรก) ───────────────────────────────
if st.session_state.page != "หน้าแรก":
    _bc1, _bc2, _bc3 = st.columns([1, 1, 6])
    with _bc1:
        if st.button("◀ ย้อนกลับ", key="btn_back", use_container_width=True,type="secondary"):
            _prev = st.session_state.get("prev_page", "หน้าแรก")
            st.session_state.prev_page = st.session_state.page
            st.session_state.page = _prev
            st.rerun()
    with _bc2:
        if st.button("🏠 หน้าแรก", key="btn_home_top", use_container_width=True,type="primary"):
            st.session_state.prev_page = st.session_state.page
            st.session_state.page = "หน้าแรก"
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ หน้าแรก
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "หน้าแรก":

    # สถิติด่วน
    active_eq_n   = sum(1 for b in bookings if b["status"]=="ยืมอยู่" and b.get("item_type")=="อุปกรณ์")
    active_room_n = sum(1 for b in bookings if b["status"]=="ยืมอยู่" and b.get("item_type")=="ห้องปฏิบัติการ")
    today_str     = date.today().strftime("%Y-%m-%d")
    today_bk      = sum(1 for b in bookings if b["date"]==today_str)

    st.markdown(f"""
    <div style='text-align:center;padding:1rem 0 2rem'>
        <div style='font-size:1rem;color:#607d8b;margin-bottom:.3rem'>วันที่ {date.today().strftime("%d/%m/%Y")}</div>
        <h2 style='font-family:Prompt;color:#0d2137;font-size:1.6rem;margin:0'>ยินดีต้อนรับสู่ระบบการจองห้องปฏิบัติการ และการยืม-คืนเครื่องมือ และอุปกรณ์ ภาควิชารังสีเทคนิค</h2>
        <div style='color:#607d8b;font-size:.9rem;margin-top:.3rem'>ภาควิชารังสีเทคนิค • คณะเทคนิคการแพทย์ • มหาวิทยาลัยเชียงใหม่</div>
    </div>
    """, unsafe_allow_html=True)

    # การ์ดสถิติ
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f"""<div class="stat-card orange">
            <h3>{active_eq_n}</h3><p>🔬 อุปกรณ์ที่ยืมอยู่</p></div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""<div class="stat-card" style='border-left-color:#7b1fa2'>
            <h3>{active_room_n}</h3><p>🏫 ห้องที่จองอยู่</p></div>""", unsafe_allow_html=True)
    with s3:
        st.markdown(f"""<div class="stat-card green">
            <h3>{today_bk}</h3><p>📅 การจองวันนี้</p></div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🚀 เข้าสู่ระบบ")

    # ปุ่มหลัก 4 ปุ่ม
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""<div style='background:linear-gradient(135deg,#1565c0,#0288d1);
            border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;
            box-shadow:0 4px 18px rgba(21,101,192,.3)'>
            <div style='font-size:2.5rem'>📋</div>
            <div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>ยืมอุปกรณ์</div>
            <div style='font-size:.82rem;opacity:.85'>จองและยืมอุปกรณ์ของภาควิชา</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📋  เข้าหน้ายืมอุปกรณ์", use_container_width=True, type="secondary", key="home_borrow"):
            st.session_state.page = "ยืมอุปกรณ์"
            st.rerun()

    with col2:
        st.markdown("""<div style='background:linear-gradient(135deg,#ef6c00,#f9a825);
            border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;
            box-shadow:0 4px 18px rgba(239,108,0,.3)'>
            <div style='font-size:2.5rem'>📦</div>
            <div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>คืนอุปกรณ์</div>
            <div style='font-size:.82rem;opacity:.85'>บันทึกการคืนอุปกรณ์</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📦  เข้าหน้าคืนอุปกรณ์", use_container_width=True, key="home_return"):
            st.session_state.page = "คืนอุปกรณ์"
            st.rerun()

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("""<div style='background:linear-gradient(135deg,#2e7d32,#43a047);
            border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;
            box-shadow:0 4px 18px rgba(46,125,50,.3)'>
            <div style='font-size:2.5rem'>📅</div>
            <div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>จองห้องปฏิบัติการ</div>
            <div style='font-size:.82rem;opacity:.85'>จองห้องสำหรับการเรียนและวิจัย</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📅  เข้าหน้าจองห้อง", use_container_width=True, key="home_room"):
            st.session_state.page = "จองห้อง"
            st.rerun()

    with col4:
        st.markdown("""<div style='background:linear-gradient(135deg,#c62828,#e53935);
            border-radius:16px;padding:1.5rem;color:white;margin-bottom:1rem;
            box-shadow:0 4px 18px rgba(198,40,40,.3)'>
            <div style='font-size:2.5rem'>❌</div>
            <div style='font-family:Prompt;font-weight:700;font-size:1.1rem;margin:.3rem 0'>ยกเลิก/คืนห้องปฏิบัติการ</div>
            <div style='font-size:.82rem;opacity:.85'>บันทึกการยกเลิก/คืนห้องหลังใช้งาน</div>
        </div>""", unsafe_allow_html=True)
        if st.button("❌  เข้าหน้ายกเลิก/คืนห้อง", use_container_width=True, key="home_rroom"):
            st.session_state.page = "ยกเลิกห้อง"
            st.rerun()

    st.divider()

    # แถวที่ 2: ปฏิทิน + สรุป
    col5, col6 = st.columns(2)
    with col5:
        st.markdown("""<div style='background:white;border-radius:14px;padding:1.2rem 1.5rem;
            box-shadow:0 2px 12px rgba(0,0,0,.08);border-left:5px solid #1565c0;margin-bottom:.5rem'>
            <div style='font-size:1.8rem'>🗓️</div>
            <div style='font-family:Prompt;font-weight:700;color:#0d2137'>ปฏิทินการจอง</div>
            <div style='font-size:.82rem;color:#607d8b'>ดูภาพรวมการจองรายเดือน</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🗓️  ดูปฏิทิน", use_container_width=True, key="home_cal"):
            st.session_state.page = "ปฏิทิน"
            st.rerun()

    with col6:
        st.markdown("""<div style='background:white;border-radius:14px;padding:1.2rem 1.5rem;
            box-shadow:0 2px 12px rgba(0,0,0,.08);border-left:5px solid #546e7a;margin-bottom:.5rem'>
            <div style='font-size:1.8rem'>📊</div>
            <div style='font-family:Prompt;font-weight:700;color:#0d2137'>สรุปการใช้งาน</div>
            <div style='font-size:.82rem;color:#607d8b'>ตารางและสถิติการยืม-คืน</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📊  ดูสรุป", use_container_width=True, key="home_sum"):
            st.session_state.page = "สรุป"
            st.rerun()

    st.divider()
    st.markdown("""
    <div style='background:#f0f7ff;border-radius:12px;padding:1rem 1.5rem;
        border:1px solid #bbdefb;font-size:.82rem;color:#1565c0'>
        ℹ️ <b>วิธีใช้งาน:</b> เลือกเมนูจากปุ่มด้านบน หรือคลิกที่แถบเมนูด้านซ้ายมือได้เลยครับ<br>
        📞 พบปัญหาการจอง ติดต่อ <b>จีรนันท์ 065-5354782</b>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ ยืมอุปกรณ์
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "ยืมอุปกรณ์":
    st.markdown('<div class="sec-title">📋 ฟอร์มยืมอุปกรณ์</div>', unsafe_allow_html=True)

    # ── ภาพรวมความว่างก่อนจอง ──────────────────────────────────────────────────
    with st.expander("🗺️ ภาพรวมความว่างอุปกรณ์ทั้งหมด — เลือกวันที่ต้องการ", expanded=True):
        ov_date = st.date_input("เลือกวันที่", value=date.today(), key="ov_date", min_value=date.today())
        ov_ds   = ov_date.strftime("%Y-%m-%d")

        # Header row: ชื่ออุปกรณ์ vs ทุก timeslot
        header = "<tr><th style='text-align:left;min-width:180px'>อุปกรณ์</th>"
        for s in TIME_SLOTS:
            header += f"<th style='font-size:.7rem;padding:4px 3px;white-space:nowrap'>{s.replace('–','<br>')}</th>"
        header += "</tr>"

        rows_html = ""
        for item in EQUIPMENT_LIST:
            rows_html += f"<tr><td style='font-size:.78rem;padding:5px 8px;white-space:nowrap'>{item}</td>"
            for s in TIME_SLOTS:
                taken = is_slot_taken(bookings, item, ov_ds, s)
                if taken:
                    rows_html += "<td style='background:#fde8e8;text-align:center;font-size:.85rem'>❌</td>"
                else:
                    rows_html += "<td style='background:#e8f5e9;text-align:center;font-size:.85rem'>✅</td>"
            rows_html += "</tr>"

        st.markdown(f"""
        <div style='overflow-x:auto;margin-top:.5rem'>
        <table style='border-collapse:collapse;width:100%'>
            <thead style='background:#0d2137;color:white'>{header}</thead>
            <tbody>{rows_html}</tbody>
        </table>
        <div style='font-size:.72rem;color:#607d8b;margin-top:6px'>✅ ว่าง &nbsp;|&nbsp; ❌ ไม่ว่าง</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown("##### 👤 ข้อมูลผู้ยืม")
    c1, c2, c3 = st.columns(3)
    with c1:
        name = st.text_input("ชื่อ-สกุล *", placeholder="ชื่อ-สกุลผู้ยืม")
    with c2:
        phone_id = st.text_input("เบอร์โทรบุคลากร / รหัสนักศึกษา *", placeholder="0801000001/661110000")
    with c3:
        user_status = st.selectbox("สถานะ *", STATUS_OPTIONS)
    purpose = st.text_input("วัตถุประสงค์", placeholder="ระบุวัตถุประสงค์การใช้งาน")

    st.divider()

    st.markdown("##### 📦 เลือกอุปกรณ์ (29 รายการ)")
    sel_eq = st.selectbox("เลือกอุปกรณ์ *", EQUIPMENT_LIST, key="sel_eq")
    qty    = st.number_input("จำนวน", min_value=1, max_value=50, value=1)
    if st.button("✔️ เลือกอุปกรณ์นี้", type="primary", key="confirm_eq"):
        st.session_state["borrow_item"]      = sel_eq
        st.session_state["borrow_item_type"] = "อุปกรณ์"
        st.session_state["borrow_qty"]       = qty
        st.success(f"เลือกแล้ว: **{sel_eq}** จำนวน {qty} ชิ้น")

    # Show selected
    chosen = st.session_state.get("borrow_item")
    chosen_type = st.session_state.get("borrow_item_type", "อุปกรณ์")
    chosen_qty  = st.session_state.get("borrow_qty", 1)

    if chosen:
        st.info(f"**รายการที่เลือก:** {chosen}  |  ประเภท: {chosen_type}  |  จำนวน: {chosen_qty}")
    else:
        st.warning("⚠️ กรุณาเลือกอุปกรณ์หรือห้องปฏิบัติการก่อน")

    st.divider()

    # วันและเวลา
    st.markdown("##### 📅 วันที่และช่วงเวลา")
    borrow_date = st.date_input("วันที่ต้องการยืม *", min_value=date.today())
    date_str = borrow_date.strftime("%Y-%m-%d")

    EQ_STARTS = ["08:30","09:00","09:30","10:00","10:30","11:00","11:30",
                 "12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30"]
    EQ_ENDS   = ["09:00","09:30","10:00","10:30","11:00","11:30","12:00",
                 "12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00","16:30"]

    tc1, tc2 = st.columns(2)
    with tc1:
        eq_start = st.selectbox("⏰ เวลาเริ่ม *", EQ_STARTS, key="eq_start")
    # เวลาสิ้นสุด: เฉพาะที่มากกว่าเวลาเริ่ม
    valid_ends = [e for e in EQ_ENDS if parse_time(e) > parse_time(eq_start)]
    with tc2:
        if valid_ends:
            eq_end = st.selectbox("⏰ เวลาสิ้นสุด *", valid_ends, key="eq_end")
        else:
            st.selectbox("⏰ เวลาสิ้นสุด *", ["—"], key="eq_end", disabled=True)
            eq_end = None

    if eq_end:
        borrow_slot = f"{eq_start}–{eq_end}"
        # เช็ก overlap กับการจองที่มีอยู่
        conflict_bk = is_slot_taken(bookings, chosen, date_str, borrow_slot) if chosen else None
        if conflict_bk:
            st.error(f"⛔ ช่วง **{borrow_slot}** ทับซ้อนกับการจองของ **{conflict_bk['name']}** ({conflict_bk.get('slot','')}) — กรุณาเลือกเวลาอื่น")
            borrow_slot = None
        else:
            st.success(f"✅ ช่วงเวลาที่เลือก: **{borrow_slot}**")
    else:
        borrow_slot = None

    conflict = None

    st.divider()

    st.markdown("##### 📷 รูปภาพอุปกรณ์ก่อนนำออก (เพิ่มภายหลังได้)")
    borrow_imgs = st.file_uploader(
        "อัปโหลดรูปภาพอุปกรณ์ก่อนยืม (เลือกได้หลายรูป)",
        type=["jpg","jpeg","png","heic","webp"],
        key="upload_borrow",
        accept_multiple_files=True,
        help="กด Ctrl/Cmd ค้างเพื่อเลือกหลายไฟล์พร้อมกัน"
    )
    if borrow_imgs:
        cols_prev = st.columns(min(len(borrow_imgs), 4))
        for i, f in enumerate(borrow_imgs):
            with cols_prev[i % 4]:
                st.image(f, caption=f"รูป {i+1}", width=150)

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
                "item": chosen, "item_type": chosen_type, "quantity": chosen_qty,
                "date": date_str, "slot": borrow_slot,
                "borrow_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "return_time": None, "status": "ยืมอยู่",
                "borrow_image": img_path, "return_image": None, "notes": "",
            }
            bookings.append(new_bk)
            save_one_booking(new_bk)
            st.session_state.bookings = bookings
            for k in ["borrow_item", "borrow_item_type", "borrow_qty"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success(f"🎉 ยืมสำเร็จ! รหัสการยืม: **{bid}**")
            st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ คืนอุปกรณ์
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "คืนอุปกรณ์":
    st.markdown('<div class="sec-title">📦 บันทึกการคืนอุปกรณ์</div>', unsafe_allow_html=True)

    active = [b for b in bookings if b["status"] == "ยืมอยู่"]

    if not active:
        st.info("✅ ไม่มีรายการที่ยืมอยู่ในขณะนี้")
    else:
        search = st.text_input("🔍 ค้นหาด้วยชื่อผู้ยืม หรือ รหัสการยืม",
                                placeholder="พิมพ์ชื่อ หรือรหัส เช่น A1B2C3D4")
        filtered = [b for b in active if
                    not search or
                    search.lower() in b["name"].lower() or
                    search.upper() in b["id"].upper()]

        st.markdown(f"**พบ {len(filtered)} รายการที่กำลังยืมอยู่**")
        st.divider()

        for b in filtered:
            with st.expander(
                f"🔖 [{b['id']}]  {b['name']}  —  {b['item']}  ({b['date']}  {b.get('slot', b.get('hour','-'))})",
                expanded=False
            ):
                ci1, ci2 = st.columns([1.5, 1])
                with ci1:
                    st.markdown(f"""
| รายละเอียด | ข้อมูล |
|---|---|
| **รหัส** | `{b['id']}` |
| **ชื่อ-สกุล** | {b['name']} |
| **สถานะผู้ยืม** | {b['user_status']} |
| **อุปกรณ์/ห้อง** | {b['item']} |
| **วันที่** | {b['date']} |
| **ช่วงเวลา** | {b.get('slot', b.get('hour','-'))} |
| **เวลาที่ยืม** | {b['borrow_time']} |
""")
                with ci2:
                    borrow_paths = str_to_paths(b.get("borrow_image",""))
                    valid_bpaths = [p for p in borrow_paths if st.image(p)]
                    if valid_bpaths:
                        for i, p in enumerate(valid_bpaths):
                            st.image(p, caption=f"📷 รูปก่อนยืม {i+1}", width=180)
                    else:
                        st.caption("ไม่มีรูปก่อนยืม")

                # เพิ่มรูปก่อนยืมภายหลัง (ถ้ายังไม่มี)
                if not b.get("borrow_image"):
                    st.markdown("**📷 เพิ่มรูปก่อนยืม (ภายหลัง)**")
                    add_borrow_imgs = st.file_uploader(
                        "อัปโหลดรูปก่อนยืม (เพิ่มภายหลัง — เลือกได้หลายรูป)",
                        type=["jpg","jpeg","png","heic","webp"],
                        key=f"add_borrow_{b['id']}",
                        accept_multiple_files=True
                    )
                    if add_borrow_imgs:
                        cols_ab = st.columns(min(len(add_borrow_imgs), 4))
                        for i, f in enumerate(add_borrow_imgs):
                            with cols_ab[i % 4]:
                                st.image(f, caption=f"รูป {i+1}", width=130)
                        if st.button("💾 บันทึกรูปก่อนยืม", key=f"save_borrow_{b['id']}"):
                            new_paths = save_images_multi(b["id"], add_borrow_imgs, "borrow_add")
                            for bk in bookings:
                                if bk["id"] == b["id"]:
                                    existing = str_to_paths(bk.get("borrow_image",""))
                                    bk["borrow_image"] = paths_to_str(existing + new_paths)
                            save_bookings(bookings)
                            st.session_state.bookings = bookings
                            st.success(f"✅ บันทึก {len(new_paths)} รูปแล้ว")
                            st.rerun()

                st.markdown("**📷 รูปภาพอุปกรณ์ขณะคืน**")
                ret_imgs = st.file_uploader(
                    "อัปโหลดรูปภาพตอนคืน (เลือกได้หลายรูป)",
                    type=["jpg","jpeg","png","heic","webp"],
                    key=f"upload_ret_{b['id']}",
                    accept_multiple_files=True,
                    help="กด Ctrl/Cmd ค้างเพื่อเลือกหลายไฟล์"
                )
                if ret_imgs:
                    cols_ret = st.columns(min(len(ret_imgs), 4))
                    for i, f in enumerate(ret_imgs):
                        with cols_ret[i % 4]:
                            st.image(f, caption=f"รูป {i+1}", width=130)

                ret_notes = st.text_input("หมายเหตุ / สภาพอุปกรณ์",
                                           placeholder="เช่น ครบถ้วน สภาพดี",
                                           key=f"note_{b['id']}")
                col_r, _ = st.columns([1, 3])
                with col_r:
                    if st.button(f"✅ ยืนยันการคืน", key=f"ret_{b['id']}", type="primary",
                                  use_container_width=True):
                        img_path = ""
                        if ret_imgs:
                            paths = save_images_multi(b["id"], ret_imgs, "return")
                            img_path = paths_to_str(paths)
                        _ret_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        update_booking_status(b["id"], "คืนแล้ว", _ret_time, img_path, ret_notes)
                        for bk in bookings:
                            if bk["id"] == b["id"]:
                                bk["status"]       = "คืนแล้ว"
                                bk["return_time"]  = _ret_time
                                bk["return_image"] = img_path
                                bk["notes"]        = ret_notes
                        st.session_state.bookings = bookings
                        st.success(f"✅ คืนอุปกรณ์ [{b['id']}] เรียบร้อย!")
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ ปฏิทิน
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "ปฏิทิน":
    st.markdown('<div class="sec-title">🗓️ ปฏิทินการยืมอุปกรณ์และการจองห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    # nav
    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("◀ เดือนก่อน", use_container_width=True):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.rerun()
    with nav2:
        st.markdown(
            f"<h3 style='text-align:center;font-family:Prompt;color:#0d2137;margin:4px 0'>"
            f"📅 {MONTH_TH[st.session_state.cal_month]} {st.session_state.cal_year + 543}</h3>",
            unsafe_allow_html=True)
    with nav3:
        if st.button("เดือนถัดไป ▶", use_container_width=True):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.rerun()

    # filter
    all_items = ["ทั้งหมด"] + EQUIPMENT_LIST + ROOMS_LIST
    fil_item = st.selectbox("กรองตามอุปกรณ์/ห้อง", all_items, key="cal_filter")

    yr = st.session_state.cal_year
    mo = st.session_state.cal_month

    def day_count(d):
        ds = f"{yr}-{mo:02d}-{d:02d}"
        return sum(1 for b in bookings
                   if b["date"] == ds and b["status"] != "คืนแล้ว"
                   and (fil_item == "ทั้งหมด" or b["item"] == fil_item))

    cal_matrix = calendar.monthcalendar(yr, mo)
    days_label = ["จันทร์", "อังคาร", "พุธ", "พฤหัส", "ศุกร์", "เสาร์", "อาทิตย์"]

    # Build HTML calendar
    html = '<div class="cal-wrap"><table class="cal-table"><thead><tr>'
    for i, dl in enumerate(days_label):
        cls = "cal-th cal-sun" if i == 6 else "cal-th"
        html += f'<th class="{cls}">{dl}</th>'
    html += "</tr></thead><tbody>"

    today_obj = date.today()
    for week in cal_matrix:
        html += "<tr>"
        for col_i, d in enumerate(week):
            is_sun = (col_i == 6)
            if d == 0:
                html += '<td class="cal-td cal-empty"></td>'
                continue
            cnt      = day_count(d)
            is_today = (d == today_obj.day and mo == today_obj.month and yr == today_obj.year)
            td_cls   = "cal-td"
            if is_today:
                td_cls += " cal-today"
            elif cnt > 0:
                td_cls += " cal-has"

            dn_cls = "cal-daynum cal-daynum-sun" if is_sun else "cal-daynum"
            today_badge = ('<div style="font-size:.58rem;background:#1565c0;color:white;'
                           'border-radius:6px;padding:0 5px;margin:2px auto;width:fit-content">วันนี้</div>'
                           if is_today else "")

            dot_color = "#c62828" if is_sun else "#1565c0"
            dots = ""
            if cnt > 0:
                n = min(cnt, 5)
                dots = "".join(f'<span class="cal-dot" style="background:{dot_color}"></span>' for _ in range(n))
                if cnt > 5:
                    dots += f'<span style="font-size:.6rem;color:#ef6c00">+{cnt-5}</span>'

            cnt_txt = (f'<div style="font-size:.65rem;color:{dot_color};font-weight:700">'
                       f'{cnt} รายการ</div>') if cnt > 0 else ""

            html += (f'<td class="{td_cls}">'
                     f'<div class="{dn_cls}">{d}</div>'
                     f'{today_badge}'
                     f'<div style="margin-top:3px">{dots}</div>'
                     f'{cnt_txt}'
                     f'</td>')
        html += "</tr>"
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("""
    <div style='display:flex;gap:14px;margin-top:10px;flex-wrap:wrap;font-size:.78rem;color:#546e7a'>
        <span style='background:#e3f2fd;padding:2px 10px;border-radius:8px;border:1px solid #90caf9'>🔵 วันนี้</span>
        <span style='background:#fff8e1;padding:2px 10px;border-radius:8px;border:1px solid #ffcc80'>🟡 มีการจอง</span>
        <span>• จุดสีน้ำเงิน = จำนวนการจอง</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # รายการวันที่เลือก
    st.markdown("#### 🔍 รายการจองตามวันที่")
    sel_date = st.date_input("เลือกวันที่", value=today_obj, key="cal_dt")
    sel_ds   = sel_date.strftime("%Y-%m-%d")
    day_bks  = [b for b in bookings if b["date"] == sel_ds and
                (fil_item == "ทั้งหมด" or b["item"] == fil_item)]

    if not day_bks:
        st.info(f"ไม่มีการจองในวันที่ {sel_ds}")
    else:
        for b in sorted(day_bks, key=lambda x: x.get("slot", x.get("hour", ""))):
            pill = ('<span class="slot-pill pill-booked">ยืมอยู่</span>'
                    if b["status"] == "ยืมอยู่"
                    else '<span class="slot-pill pill-returned">คืนแล้ว</span>')
            st.markdown(f"""
            <div style='background:white;border-radius:10px;padding:.7rem 1.1rem;margin-bottom:.4rem;
                box-shadow:0 1px 8px rgba(0,0,0,.07);border-left:3.5px solid #1565c0;
                display:flex;justify-content:space-between;align-items:center'>
                <div>
                    <b style='color:#0d2137'>{b.get('slot', b.get('hour','-'))}</b>&nbsp;—&nbsp;{b['item']}
                    <br><small style='color:#607d8b'>{b['name']}&nbsp;|&nbsp;{b['user_status'][:30]}</small>
                </div>
                {pill}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ตารางความว่างรายชั่วโมง
    st.markdown("#### ⏰ ตารางความว่างรายชั่วโมง")
    h1, h2 = st.columns([2, 1])
    with h1:
        avail_item = st.selectbox("เลือกอุปกรณ์/ห้อง", EQUIPMENT_LIST + ROOMS_LIST, key="avail_item")
    with h2:
        avail_date = st.date_input("วันที่", value=today_obj, key="avail_date")
    avail_ds = avail_date.strftime("%Y-%m-%d")

    cols = st.columns(len(TIME_SLOTS))
    for i, slot in enumerate(TIME_SLOTS):
        taken = is_slot_taken(bookings, avail_item, avail_ds, slot)
        lbl = slot.replace("–", "<br>")
        with cols[i]:
            if taken:
                st.markdown(f'<div class="hour-box hour-taken">{lbl}<br>❌</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="hour-box hour-free">{lbl}<br>✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ สรุป
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "สรุป":
    st.markdown('<div class="sec-title">📊 สรุปการใช้งานอุปกรณ์และห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    total      = len(bookings)
    active_n   = sum(1 for b in bookings if b["status"] == "ยืมอยู่")
    returned_n = sum(1 for b in bookings if b["status"] == "คืนแล้ว")
    today_n    = sum(1 for b in bookings if b["date"] == date.today().strftime("%Y-%m-%d"))

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="stat-card"><h3>{total}</h3><p>🗂️ รายการทั้งหมด</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card orange"><h3>{active_n}</h3><p>📤 กำลังยืมอยู่</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card green"><h3>{returned_n}</h3><p>📥 คืนแล้ว</p></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="stat-card red"><h3>{today_n}</h3><p>📅 จองวันนี้</p></div>', unsafe_allow_html=True)

    st.divider()

    f1, f2, f3 = st.columns(3)
    with f1:
        flt_status = st.selectbox("สถานะ", ["ทั้งหมด", "ยืมอยู่", "คืนแล้ว"])
    with f2:
        flt_type = st.selectbox("ประเภท", ["ทั้งหมด", "อุปกรณ์", "ห้องปฏิบัติการ"])
    with f3:
        dr = st.date_input("ช่วงวันที่",
                           value=(date.today() - timedelta(days=30), date.today()),
                           key="sum_dr")

    flt = bookings[:]
    if flt_status != "ทั้งหมด":
        flt = [b for b in flt if b["status"] == flt_status]
    if flt_type != "ทั้งหมด":
        flt = [b for b in flt if b.get("item_type", "อุปกรณ์") == flt_type]
    if len(dr) == 2:
        s, e = dr
        flt = [b for b in flt
               if s.strftime("%Y-%m-%d") <= b["date"] <= e.strftime("%Y-%m-%d")]

    st.markdown(f"#### 📋 ตารางรายการจอง ({len(flt)} รายการ)")
    if not flt:
        st.info("ไม่พบข้อมูลตามเงื่อนไข")
    else:
        rows = ""
        for b in sorted(flt, key=lambda x: x["date"] + x.get("slot", x.get("hour","")), reverse=True):
            pill = ('<span class="slot-pill pill-booked">ยืมอยู่</span>'
                    if b["status"] == "ยืมอยู่"
                    else '<span class="slot-pill pill-returned">คืนแล้ว</span>')
            rows += f"""<tr>
                <td><code>{b['id']}</code></td>
                <td>{b['name']}</td>
                <td style='text-align:left'>{b['item']}</td>
                <td>{b['date']}</td>
                <td style='white-space:nowrap'>{b.get('slot', b.get('hour','-'))}</td>
                <td>{b.get('quantity',1)}</td>
                <td style='white-space:nowrap'>{b['borrow_time'][:16] if b.get('borrow_time') else '-'}</td>
                <td style='white-space:nowrap'>{b['return_time'][:16] if b.get('return_time') else '-'}</td>
                <td>{pill}</td>
                <td>{b.get('notes','') or '-'}</td>
            </tr>"""
        st.markdown(f"""
        <div style='overflow-x:auto'>
        <table class="sum-table">
            <thead><tr>
                <th>รหัส</th><th>ชื่อ</th><th>อุปกรณ์/ห้อง</th>
                <th>วันที่</th><th>เวลา</th><th>จำนวน</th>
                <th>เวลายืม</th><th>เวลาคืน</th><th>สถานะ</th><th>หมายเหตุ</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table></div>
        """, unsafe_allow_html=True)

    if bookings:
        st.divider()
        st.markdown("#### 🏆 อุปกรณ์/ห้องที่มีการจองสูงสุด")
        top = Counter(b["item"] for b in bookings).most_common(12)
        if top:
            df_c = pd.DataFrame({
                "รายการ": [t[0][:35] for t in top],
                "จำนวนครั้ง": [t[1] for t in top]
            })
            st.bar_chart(df_c.set_index("รายการ"))

        st.divider()
        df_ex = pd.DataFrame(bookings).drop(
            columns=["borrow_image", "return_image"], errors="ignore")
        csv = df_ex.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Export ข้อมูลเป็น CSV", csv, "rt_bookings.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ จองห้องปฏิบัติการ
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "จองห้อง":
    st.markdown('<div class="sec-title">🏫 ฟอร์มจองห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    # ── ภาพรวมห้องทั้งหมด ───────────────────────────────────────────────────────
    with st.expander("🗺️ ดูภาพรวมความว่างของห้องทั้งหมดก่อนจอง", expanded=False):
        rov_date = st.date_input("เลือกวันที่", value=date.today(), key="rov_date", min_value=date.today())
        rov_ds   = rov_date.strftime("%Y-%m-%d")

        header = "<tr><th style='text-align:left;min-width:160px'>ห้อง</th>"
        for s in TIME_SLOTS:
            header += f"<th style='font-size:.7rem;padding:4px 3px;white-space:nowrap'>{s.replace('–','<br>')}</th>"
        header += "</tr>"

        rows_html = ""
        for room in ROOMS_LIST:
            rows_html += f"<tr><td style='font-size:.78rem;padding:5px 8px;white-space:nowrap'>{room}</td>"
            for s in TIME_SLOTS:
                taken = is_slot_taken(bookings, room, rov_ds, s)
                if taken:
                    name_short = taken.get("name", "")[:6]
                    rows_html += f"<td style='background:#fde8e8;text-align:center;font-size:.75rem;color:#c62828'>{name_short}..</td>"
                else:
                    rows_html += "<td style='background:#e8f5e9;text-align:center;font-size:.85rem'>✅</td>"
            rows_html += "</tr>"

        st.markdown(f"""
        <div style='overflow-x:auto;margin-top:.5rem'>
        <table style='border-collapse:collapse;width:100%'>
            <thead style='background:#0d2137;color:white'>{header}</thead>
            <tbody>{rows_html}</tbody>
        </table>
        <div style='font-size:.72rem;color:#607d8b;margin-top:6px'>✅ ว่าง &nbsp;|&nbsp; 🔴 ชื่อผู้จอง = ไม่ว่าง</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown("##### 👤 ข้อมูลผู้จอง")
    r1, r2, r3 = st.columns(3)
    with r1:
        r_name = st.text_input("ชื่อ-สกุล *", placeholder="ชื่อ-สกุลผู้จอง", key="r_name")
    with r2:
        r_phone = st.text_input("เบอร์โทรบุคลากร / รหัสนักศึกษา *", placeholder="0801000001/661110000", key="r_phone")
    with r3:
        r_status = st.selectbox("สถานะ *", STATUS_OPTIONS, key="r_status")
    r_purpose = st.text_input("วัตถุประสงค์การใช้ห้อง", placeholder="เช่น ปฏิบัติการ CT Scan ปี 3", key="r_purpose")

    st.divider()

    st.markdown("##### 🏫 เลือกห้องปฏิบัติการ")
    r_room = st.selectbox("เลือกห้อง *", ROOMS_LIST, key="r_room")

    st.divider()

    st.markdown("##### 📅 วันที่และช่วงเวลา")
    r_date = st.date_input("วันที่จอง *", min_value=date.today(), key="r_date")
    r_date_str = r_date.strftime("%Y-%m-%d")

    RM_STARTS = ["08:30","09:00","09:30","10:00","10:30","11:00","11:30",
                 "12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30"]
    RM_ENDS   = ["09:00","09:30","10:00","10:30","11:00","11:30","12:00",
                 "12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00","16:30"]

    rc1, rc2 = st.columns(2)
    with rc1:
        rm_start = st.selectbox("⏰ เวลาเริ่ม *", RM_STARTS, key="rm_start")
    valid_r_ends = [e for e in RM_ENDS if parse_time(e) > parse_time(rm_start)]
    with rc2:
        if valid_r_ends:
            rm_end = st.selectbox("⏰ เวลาสิ้นสุด *", valid_r_ends, key="rm_end")
        else:
            st.selectbox("⏰ เวลาสิ้นสุด *", ["—"], key="rm_end", disabled=True)
            rm_end = None

    if rm_end:
        r_slot = f"{rm_start}–{rm_end}"
        r_conflict_bk = is_slot_taken(bookings, r_room, r_date_str, r_slot)
        if r_conflict_bk:
            st.error(f"⛔ ช่วง **{r_slot}** ทับซ้อนกับการจองของ **{r_conflict_bk['name']}** ({r_conflict_bk.get('slot','')}) — กรุณาเลือกเวลาอื่น")
            r_slot = None
        else:
            st.success(f"✅ ช่วงเวลาที่เลือก: **{r_slot}**")
    else:
        r_slot = None

    r_conflict = None

    st.divider()
    st.markdown("##### 📷 รูปภาพก่อนเข้าใช้ห้อง (เพิ่มภายหลังได้)")
    r_imgs = st.file_uploader(
        "อัปโหลดรูปภาพสภาพห้องก่อนเข้าใช้ (เลือกได้หลายรูป)",
        type=["jpg","jpeg","png","heic","webp"],
        key="upload_room",
        accept_multiple_files=True,
        help="กด Ctrl/Cmd ค้างเพื่อเลือกหลายไฟล์"
    )
    if r_imgs:
        cols_r = st.columns(min(len(r_imgs), 4))
        for i, f in enumerate(r_imgs):
            with cols_r[i % 4]:
                st.image(f, caption=f"รูป {i+1}", width=150)

    st.divider()
    col_rb, _ = st.columns([1, 3])
    with col_rb:
        r_submit = st.button("✅ ยืนยันการจองห้อง", type="primary", use_container_width=True, key="r_submit")

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
                "id": bid, "name": r_name.strip(), "phone_id": r_phone.strip(),
                "user_status": r_status, "purpose": r_purpose,
                "item": r_room, "item_type": "ห้องปฏิบัติการ", "quantity": 1,
                "date": r_date_str, "slot": r_slot,
                "borrow_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "return_time": None, "status": "ยืมอยู่",
                "borrow_image": img_path, "return_image": None, "notes": "",
            }
            bookings.append(new_bk)
            save_one_booking(new_bk)
            st.session_state.bookings = bookings
            st.success(f"🎉 จองห้องสำเร็จ! รหัสการจอง: **{bid}**")
            st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ▸ ยกเลิกห้องปฏิบัติการ
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "ยกเลิกห้อง":
    st.markdown('<div class="sec-title">❌ ยกเลิกห้องปฏิบัติการ</div>', unsafe_allow_html=True)

    active_rooms = [b for b in bookings if b["status"] == "ยืมอยู่" and b.get("item_type") == "ห้องปฏิบัติการ"]

    if not active_rooms:
        st.info("✅ ไม่มีห้องที่จองอยู่ในขณะนี้")
    else:
        rs = st.text_input("🔍 ค้นหาด้วยชื่อผู้จอง หรือ รหัสการจอง",
                           placeholder="พิมพ์ชื่อ หรือรหัส", key="room_search")
        rf = [b for b in active_rooms if
              not rs or rs.lower() in b["name"].lower() or rs.upper() in b["id"].upper()]

        st.markdown(f"**พบ {len(rf)} ห้องที่จองอยู่**")
        st.divider()

        for b in rf:
            slot_disp = b.get("slot", b.get("hour", "-"))
            with st.expander(
                f"🏫 [{b['id']}]  {b['name']}  —  {b['item']}  ({b['date']}  {slot_disp})",
                expanded=False
            ):
                ci1, ci2 = st.columns([1.5, 1])
                with ci1:
                    st.markdown(f"""
| รายละเอียด | ข้อมูล |
|---|---|
| **รหัส** | `{b['id']}` |
| **ชื่อ-สกุล** | {b['name']} |
| **ห้อง** | {b['item']} |
| **วันที่** | {b['date']} |
| **ช่วงเวลา** | {slot_disp} |
| **เวลาที่จอง** | {b['borrow_time']} |
""")
                with ci2:
                    room_bpaths = str_to_paths(b.get("borrow_image",""))
                    valid_rbpaths = [p for p in room_bpaths if st.image(p)]
                    if valid_rbpaths:
                        for i, p in enumerate(valid_rbpaths):
                            st.image(p, caption=f"📷 รูปก่อนใช้ {i+1}", width=180)
                    else:
                        st.caption("ไม่มีรูปก่อนใช้")

                # เพิ่มรูปก่อนใช้ห้องภายหลัง (ถ้ายังไม่มี)
                if not b.get("borrow_image"):
                    st.markdown("**📷 เพิ่มรูปก่อนเข้าใช้ห้อง (ภายหลัง)**")
                    add_rborrow_imgs = st.file_uploader(
                        "อัปโหลดรูปก่อนเข้าใช้ห้อง (เพิ่มภายหลัง — หลายรูปได้)",
                        type=["jpg","jpeg","png","heic","webp"],
                        key=f"add_rborrow_{b['id']}",
                        accept_multiple_files=True
                    )
                    if add_rborrow_imgs:
                        cols_arb = st.columns(min(len(add_rborrow_imgs), 4))
                        for i, f in enumerate(add_rborrow_imgs):
                            with cols_arb[i % 4]:
                                st.image(f, caption=f"รูป {i+1}", width=130)
                        if st.button("💾 บันทึกรูปก่อนใช้ห้อง", key=f"save_rborrow_{b['id']}"):
                            new_paths = save_images_multi(b["id"], add_rborrow_imgs, "room_borrow_add")
                            for bk in bookings:
                                if bk["id"] == b["id"]:
                                    existing = str_to_paths(bk.get("borrow_image",""))
                                    bk["borrow_image"] = paths_to_str(existing + new_paths)
                            save_bookings(bookings)
                            st.session_state.bookings = bookings
                            st.success(f"✅ บันทึก {len(new_paths)} รูปแล้ว")
                            st.rerun()

                st.markdown("**📷 รูปภาพสภาพห้องหลังใช้งาน**")
                ret_imgs_r = st.file_uploader(
                    "อัปโหลดรูปภาพสภาพห้องหลังใช้ (เลือกได้หลายรูป)",
                    type=["jpg","jpeg","png","heic","webp"],
                    key=f"upload_rret_{b['id']}",
                    accept_multiple_files=True,
                    help="กด Ctrl/Cmd ค้างเพื่อเลือกหลายไฟล์"
                )
                if ret_imgs_r:
                    cols_rr = st.columns(min(len(ret_imgs_r), 4))
                    for i, f in enumerate(ret_imgs_r):
                        with cols_rr[i % 4]:
                            st.image(f, caption=f"รูป {i+1}", width=130)

                ret_notes = st.text_input("หมายเหตุ / สภาพห้อง",
                                           placeholder="เช่น ห้องสะอาด อุปกรณ์ครบ",
                                           key=f"rnote_{b['id']}")
                col_r2, _ = st.columns([1, 3])
                with col_r2:
                    if st.button("✅ ยืนยันการยกเลิกห้อง", key=f"rret_{b['id']}", type="primary",
                                  use_container_width=True):
                        img_path = ""
                        if ret_imgs_r:
                            paths = save_images_multi(b["id"], ret_imgs_r, "room_return")
                            img_path = paths_to_str(paths)
                        _ret_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        update_booking_status(b["id"], "ยกเลิกแล้ว", _ret_time, img_path, ret_notes)
                        for bk in bookings:
                            if bk["id"] == b["id"]:
                                bk["status"]       = "ยกเลิกแล้ว"
                                bk["return_time"]  = _ret_time
                                bk["return_image"] = img_path
                                bk["notes"]        = ret_notes
                        st.session_state.bookings = bookings
                        st.success(f"✅ ยกเลิกห้อง [{b['id']}] เรียบร้อย!")
                        st.rerun()
