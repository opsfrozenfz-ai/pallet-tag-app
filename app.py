import streamlit as st
import pandas as pd
import math
from datetime import datetime

# 1. ตั้งค่าหน้าเว็บให้กว้างขึ้น
st.set_page_config(page_title="ระบบสร้างใบงานกระจายสินค้า", page_icon="📦", layout="wide")

st.title("📦 โปรแกรมสร้างใบงานกระจายสินค้า (Pallet Tag)")
st.write("อัปโหลดไฟล์ > เลือกวันที่และตัวกรอง > ตั้งค่าใบงาน > สร้างใบงาน")

# 2. อัปโหลดไฟล์
col_up1, col_up2 = st.columns(2)
with col_up1:
    # ✨ แก้ไขตรงนี้: เพิ่ม 'xlsm' ให้โปรแกรมรองรับไฟล์ที่มีมาโครได้แล้วครับ
    uploaded_file = st.file_uploader("📂 1. อัปโหลดไฟล์ Order Report", type=['csv', 'xlsx', 'xlsm'])
with col_up2:
    route_file = st.file_uploader("🚚 2. อัปโหลดไฟล์ รอบรถ (อุปกรณ์เสริม: เช็ครอบส่ง)", type=['csv', 'xlsx', 'xlsm'])

def clean_branch_code(val):
    if pd.isna(val): return ""
    try:
        v = float(val)
        return str(int(v)) if v.is_integer() else str(val).strip()
    except:
        return str(val).strip()

route_dict = {}
if route_file is not None:
    try:
        if route_file.name.endswith('.csv'):
            route_df = pd.read_csv(route_file, header=1)
        else:
            route_df = pd.read_excel(route_file, header=1)
        
        def extract_branches(col_idx):
            if col_idx < len(route_df.columns):
                return set(route_df.iloc[:, col_idx].apply(clean_branch_code))
            return set()

        route_dict['Monday'] = extract_branches(0)
        route_dict['Tuesday'] = extract_branches(2)
        route_dict['Wednesday'] = extract_branches(4)
        route_dict['Thursday'] = extract_branches(6)
        route_dict['Friday'] = extract_branches(8)
        route_dict['Saturday'] = extract_branches(10)
        route_dict['Sunday'] = set()
    except Exception as e:
        st.error(f"❌ อ่านไฟล์รอบรถไม่สำเร็จ (Error: {e})")

if uploaded_file is not None:
    with st.spinner("กำลังอ่านไฟล์ Order..."):
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, low_memory=False)
        else:
            df = pd.read_excel(uploaded_file)
            
        df[['Branch Code', 'Branch Name']] = df['STORES'].str.extract(r'^(\d+)\s*-\s*(.*)$')
        df['Branch Code'] = df['Branch Code'].fillna(df['STORES'])
        df['Branch Code Clean'] = df['Branch Code'].apply(clean_branch_code)
        
        df['Branch Code Num'] = pd.to_numeric(df['Branch Code'], errors='coerce').fillna(999999)
        df['Date'] = pd.to_datetime(df['DELIVERY_START_DTTM'], format='%d-%m-%Y %H:%M', errors='coerce').dt.strftime('%d-%m-%Y')
        df['ORDER_QTY'] = pd.to_numeric(df['ORDER_QTY'], errors='coerce').fillna(0)
        
        def clean_po(val):
            if pd.isna(val): return "-"
            try:
                v = float(val)
                return str(int(v)) if v.is_integer() else str(val)
            except:
                return str(val)
        
        df['XD_PO_Clean'] = df['XD_PO'].apply(clean_po)
        df['VENDER_NAME'] = df['VENDER_NAME'].fillna("-")
        df['Booking ID'] = df['Booking ID'].fillna("-").astype(str)
        df['UOM'] = df['UOM'].fillna("UNKNOWN")
        
        df = df[df['UOM'].str.upper() != 'L']
        df['Item_Display'] = df['ITEM_NAME'].astype(str) + " : " + df['DESCRIPTION'].astype(str)

    st.divider()
    st.subheader("🔍 ตัวกรองข้อมูลที่อยู่ในไฟล์ (Filters)")
    
    date_options = ["ทั้งหมด"] + sorted(list(df['Date'].dropna().unique()))
    selected_date = st.selectbox("📅 เลือกดึงเฉพาะงานที่มีวันที่ในระบบตรงกับ:", date_options)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        po_options = sorted(list(df['XD_PO_Clean'].unique()))
        selected_po = st.multiselect("📋 เลือกเลข PO", po_options, placeholder="เลือกเลข PO...")
    with col2:
        vendor_options = sorted(list(df['VENDER_NAME'].unique()))
        selected_vendor = st.multiselect("🏢 เลือกซัพพลายเออร์", vendor_options, placeholder="เลือกซัพพลายเออร์...")
    with col3:
        item_options = sorted(list(df['Item_Display'].unique()))
        selected_item = st.multiselect("📦 เลือกรหัสสินค้า", item_options, placeholder="เลือกรหัสสินค้า...")
    with col4:
        booking_options = sorted(list(df['Booking ID'].unique()))
        selected_booking = st.multiselect("🆔 เลือก Booking ID", booking_options, placeholder="เลือก Booking ID...")

    filtered_df = df.copy()
    if selected_date != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df['Date'] == selected_date]
    if len(selected_po) > 0:
        filtered_df = filtered_df[filtered_df['XD_PO_Clean'].isin(selected_po)]
    if len(selected_vendor) > 0:
        filtered_df = filtered_df[filtered_df['VENDER_NAME'].isin(selected_vendor)]
    if len(selected_item) > 0:
        filtered_df = filtered_df[filtered_df['Item_Display'].isin(selected_item)]
    if len(selected_booking) > 0:
        filtered_df = filtered_df[filtered_df['Booking ID'].isin(selected_booking)]

    st.info(f"📊 พบข้อมูลออเดอร์งานที่ตรงตามเงื่อนไข: **{len(filtered_df)}** รายการ")
    st.divider()

    st.subheader("📅 กำหนดวันที่จัดส่งจริง (บังคับใส่ เพื่อตรวจสอบรอบรถ)")
    today_str = datetime.now().strftime("%d/%m/%Y")
    target_delivery_date = st.text_input("✏️ พิมพ์วันที่จัดส่ง (รูปแบบ วว/ดด/ปปปป เช่น 22/06/2026):", value=today_str)

    st.subheader("📐 ตั้งค่าขนาดกระดาษใบงาน")
    paper_size = st.radio(
        "เลือกรูปแบบการจัดวางกระดาษที่ต้องการพิมพ์:",
        [
            "1. A4 ขนาดปกติ (1 หน้ากระดาษ = 1 ใบงานใหญ่)", 
            "2. A4 แบบประหยัด (1 หน้ากระดาษ = 2 ใบงาน) 👉 แนะนำ! พิมพ์แนวนอนแล้วเอากรรไกรตัดครึ่งได้เลย",
            "3. A5 สำหรับเครื่องพิมพ์ที่ใช้กระดาษ A5 โดยตรง"
        ],
        index=1
    )

    if st.button("🚀 สร้างใบงานเดี๋ยวนี้", type="primary"):
        if len(filtered_df) == 0:
            st.error("❌ ไม่พบข้อมูล กรุณาปรับเปลี่ยนตัวกรองใหม่")
        elif not target_delivery_date.strip():
            st.error("❌ กรุณาพิมพ์ระบุ 'วันที่จัดส่งจริง' ในช่องด้านบนก่อนกดสร้างใบงานครับ")
        else:
            try:
                parsed_date = pd.to_datetime(target_delivery_date.strip(), format='%d/%m/%Y')
                day_name = parsed_date.day_name()
                thai_days = {'Monday': 'จันทร์', 'Tuesday': 'อังคาร', 'Wednesday': 'พุธ', 'Thursday': 'พฤหัสบดี', 'Friday': 'ศุกร์', 'Saturday': 'เสาร์', 'Sunday': 'อาทิตย์'}
                day_name_thai = thai_days.get(day_name, day_name)
                
                if route_dict:
                    active_branches = route_dict.get(day_name, set())
                    filtered_df['Has_Route'] = filtered_df['Branch Code Clean'].apply(lambda x: x in active_branches)
                else:
                    filtered_df['Has_Route'] = True

                with st.spinner(f"กำลังเช็ครอบรถของ วัน{day_name_thai} และจับคู่ใบงาน..."):
                    filtered_df = filtered_df.sort_values(by=['XD_PO_Clean', 'ITEM_NAME', 'Date', 'Booking ID', 'Branch Code Num'])
                    groups = filtered_df.groupby(['XD_PO_Clean', 'ITEM_NAME', 'DESCRIPTION', 'Date', 'VENDER_NAME', 'Booking ID'])
                    
                    is_small_size = ("2" in paper_size) or ("3" in paper_size)
                    
                    if not is_small_size: 
                        css_page = "size: A4 portrait; margin: 15mm;"
                        css_body = "font-size: 14pt;"
                        css_title = "font-size: 22pt;"
                        css_item_card = "padding: 12px; margin-bottom: 15px;"
                        css_th = "padding: 8px; font-size: 14pt;"
                        css_td = "padding: 10px;"
                        css_td_branch = "font-size: 16pt; background-color: #ededed;" 
                        css_td_qty = "font-size: 28pt; font-weight: bold; color: #000;" 
                        css_prefix = "font-size: 11pt; color: #666; font-weight: normal;" 
                    else: 
                        css_page = "size: A4 landscape; margin: 10mm;" if "2" in paper_size else "size: A5 portrait; margin: 8mm;"
                        css_body = "font-size: 11pt;"
                        css_title = "font-size: 16pt;"
                        css_item_card = "padding: 8px; margin-bottom: 10px;"
                        css_th = "padding: 5px; font-size: 11pt;"
                        css_td = "padding: 6px;"
                        css_td_branch = "font-size: 13pt; background-color: #ededed;" 
                        css_td_qty = "font-size: 22pt; font-weight: bold; color: #000;" 
                        css_prefix = "font-size: 9pt; color: #666; font-weight: normal;" 

                    html_content = f"""
                    <!DOCTYPE html>
                    <html lang="th">
                    <head>
                    <meta charset="UTF-8">
                    <style>
                        @page {{ {css_page} }}
                        body {{ font-family: Tahoma, sans-serif; margin: 0; padding: 0; color: #000; {css_body} }}
                        * {{ box-sizing: border-box; }}
                        .page {{ page-break-after: always; position: relative; width: 100%; }}
                        .page:last-child {{ page-break-after: avoid; }}
                        .header {{ text-align: center; border-bottom: 3px solid #000; padding-bottom: 8px; margin-bottom: 12px; }}
                        .title {{ {css_title} font-weight: bold; }}
                        .item-card {{ border: 2px solid #000; {css_item_card} background-color: #f9f9f9; display: table; width: 100%; }}
                        .card-col {{ display: table-cell; vertical-align: top; }}
                        .card-col.left {{ width: 72%; }}
                        .card-col.right {{ width: 28%; text-align: right; border-left: 1px dashed #ccc; padding-left: 15px; }}
                        .label {{ font-size: 10pt; color: #555; }}
                        table.data-table {{ width: 100%; border-collapse: collapse; }}
                        table.data-table th {{ background-color: #d0d0d0; text-align: center; font-weight: bold; border: 1px solid #000; {css_th} }}
                        table.data-table td {{ border: 1px solid #000; {css_td} }}
                        .text-center {{ text-align: center; }}
                        .gap-col {{ border: none !important; background-color: #fff; width: 3%; padding: 0 !important; }}
                        table.layout-table {{ width: 100%; border: none; margin: 0; padding: 0; table-layout: fixed; border-collapse: collapse; }}
                        table.layout-table > tbody > tr > td {{ border: none; padding: 0; vertical-align: top; }}
                    </style>
                    </head>
                    <body>
                    """
                    
                    def build_inner_tag(group_key, group_df, target_date_str):
                        po_no, item_code, item_desc, excel_date, vender_name, booking_id = group_key
                        total_qty = group_df['ORDER_QTY'].sum()
                        uom_val = group_df['UOM'].iloc[0] if 'UOM' in group_df.columns else 'กล่อง'
                        
                        inner_html = f"""
                        <div class="header">
                            <div class="title">ใบจัด/กระจายสินค้า (PALLET TAG)</div>
                            <div style="margin-top: 4px;">วันที่จัดส่ง: {target_date_str}</div>
                        </div>
                        <div class="item-card">
                            <div class="card-col left">
                                <div class="label">รหัสสินค้า (Item Code) / PO:</div>
                                <div style="font-weight: bold; line-height: 1.2;">
                                    <span style="font-size: 18pt;">{item_code}</span> 
                                    <span style="color: #d32f2f; font-size: 14pt; margin-left: 10px;">PO: {po_no}</span>
                                </div>
                                <div class="label" style="margin-top: 3px;">ชื่อสินค้า:</div>
                                <div style="font-weight: bold; line-height: 1.2;">{item_desc}</div>
                                
                                <div class="label" style="margin-top: 6px;">
                                    ซัพพลายเออร์: <span style="color: #333;">{vender_name}</span>
                                </div>
                                <div class="label" style="margin-top: 1px;">
                                    Booking ID: <span style="color: #333;">{booking_id}</span>
                                </div>
                                
                            </div>
                            <div class="card-col right">
                                <div class="label">จำนวนรวม:</div>
                                <div style="font-weight: bold; line-height: 1.1; font-size: 26pt;">{total_qty:g} <br><span style="font-size:13pt;">{uom_val}</span></div>
                            </div>
                        </div>
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th width="20%">รหัสสาขา</th><th width="14%">ต้องจ่าย</th><th width="14%">จัดจริง</th>
                                    <th class="gap-col"></th>
                                    <th width="20%">รหัสสาขา</th><th width="14%">ต้องจ่าย</th><th width="14%">จัดจริง</th>
                                </tr>
                            </thead>
                            <tbody>
                        """
                        
                        rows = list(group_df.iterrows())
                        half = math.ceil(len(rows) / 2)
                        
                        for i in range(half):
                            inner_html += "<tr>"
                            
                            row_left = rows[i][1]
                            branch_disp_left = f"<span style='{css_prefix}'>สาขา</span><br>{row_left['Branch Code']}"
                            if not row_left['Has_Route']:
                                branch_disp_left += "<br><span style='color:red; font-size:11pt; font-weight:normal;'>*ไม่มีรอบ*</span>"
                                
                            inner_html += f"""
                                <td class="text-center" style="{css_td_branch} font-weight:bold; line-height: 1.1;">{branch_disp_left}</td>
                                <td class="text-center" style="{css_td_qty}">{row_left['ORDER_QTY']:g}</td>
                                <td></td>
                                <td class="gap-col"></td>
                            """
                            
                            if i + half < len(rows):
                                row_right = rows[i + half][1]
                                branch_disp_right = f"<span style='{css_prefix}'>สาขา</span><br>{row_right['Branch Code']}"
                                if not row_right['Has_Route']:
                                    branch_disp_right += "<br><span style='color:red; font-size:11pt; font-weight:normal;'>*ไม่มีรอบ*</span>"
                                    
                                inner_html += f"""
                                    <td class="text-center" style="{css_td_branch} font-weight:bold; line-height: 1.1;">{branch_disp_right}</td>
                                    <td class="text-center" style="{css_td_qty}">{row_right['ORDER_QTY']:g}</td>
                                    <td></td>
                                """
                            else:
                                inner_html += "<td style='background-color:#ededed;'></td><td></td><td></td>"
                                
                            inner_html += "</tr>"
                            
                        inner_html += f"""
                                </tbody>
                            </table>
                            <div style="margin-top: 25px; width: 100%; display: table; page-break-inside: avoid;">
                                <div style="display: table-cell; width: 50%; text-align: center; padding: 10px;">
                                    <div>ผู้ตรวจสอบ (Checked By)</div><div style="border-bottom: 1px dotted #000; margin: 30px auto 10px auto; width: 70%;"></div>
                                </div>
                                <div style="display: table-cell; width: 50%; text-align: center; padding: 10px;">
                                    <div>ผู้กระจาย (Prepared By)</div><div style="border-bottom: 1px dotted #000; margin: 30px auto 10px auto; width: 70%;"></div>
                                </div>
                            </div>
                        """
                        return inner_html

                    group_list = list(groups)
                    
                    if "2" in paper_size:
                        for i in range(0, len(group_list), 2):
                            html_content += '<div class="page"><table class="layout-table"><tr>'
                            
                            tag1_key, tag1_df = group_list[i]
                            html_content += f'<td style="width:48%; padding-right:15px; border-right:2px dashed #666;">'
                            html_content += build_inner_tag(tag1_key, tag1_df, target_delivery_date)
                            html_content += '</td><td style="width:4%;"></td>' 
                            
                            if i + 1 < len(group_list):
                                tag2_key, tag2_df = group_list[i+1]
                                html_content += f'<td style="width:48%; padding-left:15px;">'
                                html_content += build_inner_tag(tag2_key, tag2_df, target_delivery_date)
                                html_content += '</td>'
                            else:
                                html_content += '<td style="width:48%;"></td>'
                            
                            html_content += '</tr></table></div>'
                    else:
                        for group_key, group_df in group_list:
                            html_content += '<div class="page">'
                            html_content += build_inner_tag(group_key, group_df, target_delivery_date)
                            html_content += '</div>'

                    html_content += "</body></html>"
                    
                    st.success(f"✅ ประมวลผลเสร็จสิ้น! ตอนนี้โปรแกรมรองรับไฟล์นามสกุล .xlsm เรียบร้อยแล้วครับ")
                    st.download_button(
                        label="📥 คลิกดาวน์โหลดใบงานเพื่อนำไปพิมพ์",
                        data=html_content.encode('utf-8'),
                        file_name=f"Distribution_Tags_{parsed_date.strftime('%Y%m%d')}.html",
                        mime="text/html"
                    )

            except ValueError:
                st.error("❌ รูปแบบวันที่ไม่ถูกต้อง! กรุณาพิมพ์ในรูปแบบ วัน/เดือน/ปี เช่น 22/06/2026")
