import streamlit as st
import pandas as pd
import math

# 1. ตั้งค่าหน้าเว็บให้กว้างขึ้น
st.set_page_config(page_title="ระบบสร้างใบงานกระจายสินค้า", page_icon="📦", layout="wide")

st.title("📦 โปรแกรมสร้างใบงานกระจายสินค้า (Pallet Tag)")
st.write("อัปโหลดไฟล์ > เลือกวันที่และตัวกรอง > ตั้งค่าใบงาน > สร้างใบงาน")

# 2. อัปโหลดไฟล์ (แบ่งเป็น 2 ช่อง สำหรับ Order และ รอบรถ)
col_up1, col_up2 = st.columns(2)
with col_up1:
    uploaded_file = st.file_uploader("📂 1. อัปโหลดไฟล์ Order Report", type=['csv', 'xlsx'])
with col_up2:
    route_file = st.file_uploader("🚚 2. อัปโหลดไฟล์ รอบรถ (อุปกรณ์เสริม: เช็ครอบส่ง)", type=['csv', 'xlsx'])

# ฟังก์ชันทำความสะอาดรหัสสาขาให้ตรงกันทั้ง 2 ไฟล์
def clean_branch_code(val):
    if pd.isna(val): return ""
    try:
        v = float(val)
        return str(int(v)) if v.is_integer() else str(val).strip()
    except:
        return str(val).strip()

# ดึงข้อมูลรอบรถเก็บไว้เป็นดิกชันนารี (ถ้ามีการอัปโหลดไฟล์)
route_dict = {}
if route_file is not None:
    try:
        if route_file.name.endswith('.csv'):
            route_df = pd.read_csv(route_file, header=1) # ข้ามบรรทัดหัวข้อใหญ่
        else:
            route_df = pd.read_excel(route_file, header=1)
        
        # คอลัมน์ไฟล์รอบรถ: 0=จันทร์, 2=อังคาร, 4=พุธ, 6=พฤหัสฯ, 8=ศุกร์, 10=เสาร์
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
        route_dict['Sunday'] = set() # สมมติว่าวันอาทิตย์ไม่มีรอบส่ง
    except Exception as e:
        st.error(f"❌ อ่านไฟล์รอบรถไม่สำเร็จ กรุณาเช็คฟอร์แมตไฟล์ (Error: {e})")

# เริ่มประมวลผลไฟล์ Order
if uploaded_file is not None:
    with st.spinner("กำลังอ่านไฟล์ Order..."):
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, low_memory=False)
        else:
            df = pd.read_excel(uploaded_file)
            
        # ล้างข้อมูลและดึงรหัสสาขา
        df[['Branch Code', 'Branch Name']] = df['STORES'].str.extract(r'^(\d+)\s*-\s*(.*)$')
        df['Branch Code'] = df['Branch Code'].fillna(df['STORES'])
        df['Branch Code Clean'] = df['Branch Code'].apply(clean_branch_code) # คลีนโค้ดเพื่อเอาไปเทียบรอบรถ
        
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
        
        # กรอง UOM ที่เป็น L ออก
        df = df[df['UOM'].str.upper() != 'L']
        df['Item_Display'] = df['ITEM_NAME'].astype(str) + " : " + df['DESCRIPTION'].astype(str)

    st.divider()
    
    # 3. สร้างตัวกรองข้อมูล (Filters)
    st.subheader("🔍 ตัวกรองข้อมูล (Filters)")
    
    # 3.1 ตัวกรอง วันที่จัดส่ง
    date_options = ["ทั้งหมด"] + sorted(list(df['Date'].dropna().unique()))
    selected_date = st.selectbox("📅 1. เลือกวันที่จัดส่ง", date_options)
    
    st.caption("💡 ทริค: ตัวกรองด้านล่าง หากปล่อยเว้นว่างไว้ ระบบจะถือว่า 'เลือกทั้งหมด'")
    
    # 3.2 ตัวกรอง 4 ช่อง
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

    # ประมวลผลการกรอง
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

    # เช็คว่าสาขามีรอบส่งหรือไม่
    if route_dict:
        def check_route(row):
            dt = pd.to_datetime(row['Date'], format='%d-%m-%Y', errors='coerce')
            if pd.isna(dt): return True 
            day_name = dt.day_name()
            active_branches = route_dict.get(day_name, set())
            return row['Branch Code Clean'] in active_branches

        filtered_df['Has_Route'] = filtered_df.apply(check_route, axis=1)
    else:
        filtered_df['Has_Route'] = True # ถ้าไม่ได้อัปไฟล์รอบรถ ให้ถือว่าส่งได้หมด

    st.info(f"📊 พบข้อมูลที่ตรงตามเงื่อนไข: **{len(filtered_df)}** รายการ")

    st.divider()

    # ✨ ส่วนที่เพิ่มมาใหม่: ให้พิมพ์เปลี่ยนวันที่จัดส่งบนใบงานได้เอง
    st.subheader("📝 กำหนดข้อความบนใบงาน")
    custom_date = st.text_input("✏️ เปลี่ยนวันที่จัดส่งบนใบงาน (สามารถพิมพ์เปลี่ยนได้เอง):", placeholder="เช่น 25 มิ.ย. 67 (หากปล่อยว่างไว้ ระบบจะใช้วันที่จากไฟล์)")

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

    # 4. ปุ่มสร้างใบงาน
    if st.button("🚀 สร้างใบงานเดี๋ยวนี้", type="primary"):
        if len(filtered_df) == 0:
            st.error("❌ ไม่พบข้อมูล กรุณาปรับเปลี่ยนตัวกรองใหม่")
        else:
            with st.spinner("กำลังจัดหน้ากระดาษและจับคู่ใบงาน..."):
                
                filtered_df = filtered_df.sort_values(by=['XD_PO_Clean', 'ITEM_NAME', 'Date', 'Booking ID', 'Branch Code Num'])
                groups = filtered_df.groupby(['XD_PO_Clean', 'ITEM_NAME', 'DESCRIPTION', 'Date', 'VENDER_NAME', 'Booking ID'])
                
                is_small_size = ("2" in paper_size) or ("3" in paper_size)
                
                if not is_small_size: 
                    css_page, css_body, css_title, css_doc_info, css_item_card, css_item_code, css_po_text, css_booking_text, css_item_desc, css_vender_name, css_total_qty, css_th, css_td, css_td_branch, css_td_qty, css_sign_box, css_sign_line = (
                        "size: A4 portrait; margin: 15mm;", "font-size: 14pt;", "font-size: 22pt;", "font-size: 13pt;", "padding: 12px; margin-bottom: 15px;", "font-size: 22pt;", "font-size: 16pt;", "font-size: 13pt; margin-top: 4px;", "font-size: 15pt; margin-top: 4px;", "font-size: 12pt; margin-top: 4px;", "font-size: 30pt;", "padding: 8px; font-size: 14pt;", "padding: 10px;", "font-size: 18pt;", "font-size: 24pt;", "font-size: 12pt; padding: 10px;", "margin: 40px auto 10px auto;"
                    )
                else: 
                    css_page = "size: A4 landscape; margin: 10mm;" if "2" in paper_size else "size: A5 portrait; margin: 8mm;"
                    css_body, css_title, css_doc_info, css_item_card, css_item_code, css_po_text, css_booking_text, css_item_desc, css_vender_name, css_total_qty, css_th, css_td, css_td_branch, css_td_qty, css_sign_box, css_sign_line = (
                        "font-size: 11pt;", "font-size: 16pt;", "font-size: 10pt;", "padding: 8px; margin-bottom: 10px;", "font-size: 16pt;", "font-size: 12pt;", "font-size: 10pt; margin-top: 2px;", "font-size: 12pt; margin-top: 2px;", "font-size: 9pt; margin-top: 2px;", "font-size: 22pt;", "padding: 5px; font-size: 11pt;", "padding: 6px;", "font-size: 13pt;", "font-size: 16pt;", "font-size: 9pt; padding: 5px;", "margin: 25px auto 5px auto;"
                    )

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
                    .doc-info {{ {css_doc_info} margin-top: 4px; }}
                    .item-card {{ border: 2px solid #000; {css_item_card} background-color: #f9f9f9; display: table; width: 100%; }}
                    .card-col {{ display: table-cell; vertical-align: top; }}
                    .card-col.left {{ width: 72%; }}
                    .card-col.right {{ width: 28%; text-align: right; border-left: 1px dashed #ccc; padding-left: 15px; }}
                    .label {{ font-size: 10pt; color: #555; }}
                    .item-code {{ {css_item_code} font-weight: bold; line-height: 1.2; }}
                    .po-text {{ {css_po_text} font-weight: bold; color: #d32f2f; margin-left: 10px; }}
                    .booking-text {{ {css_booking_text} font-weight: bold; color: #2e7d32; }}
                    .item-desc {{ {css_item_desc} font-weight: bold; line-height: 1.2; }}
                    .vender-name {{ {css_vender_name} font-weight: bold; color: #0056b3; }}
                    .total-qty {{ {css_total_qty} font-weight: bold; line-height: 1.1; }}
                    table.data-table {{ width: 100%; border-collapse: collapse; }}
                    table.data-table th {{ background-color: #e0e0e0; text-align: center; font-weight: bold; border: 1px solid #000; {css_th} }}
                    table.data-table td {{ border: 1px solid #000; {css_td} }}
                    .text-center {{ text-align: center; }}
                    .footer-sign {{ margin-top: 25px; width: 100%; display: table; page-break-inside: avoid; }}
                    .sign-box {{ display: table-cell; width: 50%; text-align: center; {css_sign_box} }}
                    .sign-box .line {{ border-bottom: 1px dotted #000; {css_sign_line} width: 70%; }}
                    .gap-col {{ border-top: none !important; border-bottom: none !important; background-color: #fff; width: 2%; padding: 0 !important; }}
                    table.layout-table {{ width: 100%; border: none; margin: 0; padding: 0; table-layout: fixed; border-collapse: collapse; }}
                    table.layout-table > tbody > tr > td {{ border: none; padding: 0; vertical-align: top; }}
                </style>
                </head>
                <body>
                """
                
                # รับค่า custom_date ที่ผู้ใช้พิมพ์ผ่านตัวแปร print_custom_date
                def build_inner_tag(group_key, group_df, print_custom_date):
                    po_no, item_code, item_desc, target_date, vender_name, booking_id = group_key
                    total_qty = group_df['ORDER_QTY'].sum()
                    uom_val = group_df['UOM'].iloc[0] if 'UOM' in group_df.columns else 'กล่อง'
                    
                    # ✨ เช็คว่ามีการพิมพ์เปลี่ยนวันที่มาหรือไม่ (ถ้าไม่ จะใช้วันที่จากระบบ)
                    display_date = print_custom_date if print_custom_date.strip() != "" else target_date
                    
                    inner_html = f"""
                    <div class="header">
                        <div class="title">ใบจัด/กระจายสินค้า (PALLET TAG)</div>
                        <div class="doc-info">วันที่จัดส่ง: {display_date}</div>
                    </div>
                    <div class="item-card">
                        <div class="card-col left">
                            <div class="label">รหัสสินค้า (Item Code):</div>
                            <div class="item-code">{item_code} <span class="po-text">/ PO: {po_no}</span></div>
                            <div class="label" style="margin-top: 3px;">ชื่อสินค้า:</div>
                            <div class="item-desc">{item_desc}</div>
                            <div class="label" style="margin-top: 3px;">ซัพพลายเออร์:</div>
                            <div class="vender-name">{vender_name}</div>
                            <div class="booking-text">Booking ID: {booking_id}</div>
                        </div>
                        <div class="card-col right">
                            <div class="label">จำนวนรวม:</div>
                            <div class="total-qty">{total_qty:g} <br><span style="font-size:13pt;">{uom_val}</span></div>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th width="20%">รหัสสาขา</th><th width="14%">ต้องจ่าย</th><th width="15%">จ่ายจริง</th>
                                <th class="gap-col"></th>
                                <th width="20%">รหัสสาขา</th><th width="14%">ต้องจ่าย</th><th width="15%">จ่ายจริง</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    
                    rows = list(group_df.iterrows())
                    half = math.ceil(len(rows) / 2)
                    
                    for i in range(half):
                        inner_html += "<tr>"
                        
                        # ฝั่งซ้าย
                        row_left = rows[i][1]
                        branch_disp_left = f"{row_left['Branch Code']}"
                        if not row_left['Has_Route']:
                            branch_disp_left += "<br><span style='color:red; font-size:11pt; font-weight:normal;'>*ไม่มีรอบส่ง*</span>"
                            
                        inner_html += f"""
                            <td class="text-center" style="{css_td_branch} font-weight:bold;">{branch_disp_left}</td>
                            <td class="text-center" style="font-weight:bold; {css_td_qty}">{row_left['ORDER_QTY']:g}</td>
                            <td></td>
                            <td class="gap-col"></td>
                        """
                        
                        # ฝั่งขวา
                        if i + half < len(rows):
                            row_right = rows[i + half][1]
                            branch_disp_right = f"{row_right['Branch Code']}"
                            if not row_right['Has_Route']:
                                branch_disp_right += "<br><span style='color:red; font-size:11pt; font-weight:normal;'>*ไม่มีรอบส่ง*</span>"
                                
                            inner_html += f"""
                                <td class="text-center" style="{css_td_branch} font-weight:bold;">{branch_disp_right}</td>
                                <td class="text-center" style="font-weight:bold; {css_td_qty}">{row_right['ORDER_QTY']:g}</td>
                                <td></td>
                            """
                        else:
                            inner_html += "<td></td><td></td><td></td>"
                            
                        inner_html += "</tr>"
                        
                    inner_html += f"""
                            </tbody>
                        </table>
                        <div class="footer-sign">
                            <div class="sign-box">
                                <div>ผู้ตรวจสอบ (Checked By)</div><div class="line"></div><div>วันที่: ____/____/______</div>
                            </div>
                            <div class="sign-box">
                                <div>ผู้กระจาย (Prepared By)</div><div class="line"></div><div>วันที่: ____/____/______</div>
                            </div>
                        </div>
                    """
                    return inner_html

                group_list = list(groups)
                
                if "2" in paper_size:
                    for i in range(0, len(group_list), 2):
                        html_content += '<div class="page"><table class="layout-table"><tr>'
                        
                        tag1_key, tag1_df = group_list[i]
                        html_content += f'<td style="width:48%; padding-right:15px; border-right:1px dashed #999;">'
                        html_content += build_inner_tag(tag1_key, tag1_df, custom_date) # ใส่ custom_date ลงไป
                        html_content += '</td><td style="width:4%;"></td>' 
                        
                        if i + 1 < len(group_list):
                            tag2_key, tag2_df = group_list[i+1]
                            html_content += f'<td style="width:48%; padding-left:15px;">'
                            html_content += build_inner_tag(tag2_key, tag2_df, custom_date) # ใส่ custom_date ลงไป
                            html_content += '</td>'
                        else:
                            html_content += '<td style="width:48%;"></td>'
                        
                        html_content += '</tr></table></div>'
                else:
                    for group_key, group_df in group_list:
                        html_content += '<div class="page">'
                        html_content += build_inner_tag(group_key, group_df, custom_date) # ใส่ custom_date ลงไป
                        html_content += '</div>'

                html_content += "</body></html>"
                
                st.success(f"✅ ประมวลผลเสร็จสิ้น! สามารถคลิกดาวน์โหลดได้เลยครับ")
                st.download_button(
                    label="📥 คลิกดาวน์โหลดใบงานเพื่อนำไปพิมพ์",
                    data=html_content.encode('utf-8'),
                    file_name="Distribution_Tags_Ready.html",
                    mime="text/html"
                )
