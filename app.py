import streamlit as st
import pandas as pd
import math

# 1. ตั้งค่าหน้าเว็บให้กว้างขึ้น
st.set_page_config(page_title="ระบบสร้างใบงานกระจายสินค้า", page_icon="📦", layout="wide")

st.title("📦 โปรแกรมสร้างใบงานกระจายสินค้า (Pallet Tag)")
st.write("อัปโหลดไฟล์ > เลือกตัวกรองที่ต้องการ > สร้างใบงาน")

# 2. อัปโหลดไฟล์
uploaded_file = st.file_uploader("📂 กรุณาอัปโหลดไฟล์ Excel หรือ CSV", type=['csv', 'xlsx'])

if uploaded_file is not None:
    with st.spinner("กำลังอ่านไฟล์..."):
        # อ่านไฟล์
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, low_memory=False)
        else:
            df = pd.read_excel(uploaded_file)
            
        # ล้างข้อมูลและดึงรหัสสาขา
        df[['Branch Code', 'Branch Name']] = df['STORES'].str.extract(r'^(\d+)\s*-\s*(.*)$')
        df['Branch Code'] = df['Branch Code'].fillna(df['STORES'])
        
        # แปลงรหัสสาขาเป็นตัวเลขเพื่อใช้เรียงลำดับ (น้อยไปมาก) สาขาที่เป็นตัวหนังสือจะถูกไว้ท้ายสุด
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
        
        # สร้างคอลัมน์ชื่อสินค้าพร้อมรหัส สำหรับแสดงในตัวกรอง
        df['Item_Display'] = df['ITEM_NAME'].astype(str) + " : " + df['DESCRIPTION'].astype(str)

    st.divider()
    
    # 3. สร้างตัวกรองข้อมูล (Filters) มี 4 ช่องเรียงกัน
    st.subheader("🔍 ตัวกรองข้อมูล (Filters)")
    st.caption("💡 ทริค: หากปล่อยเว้นว่างไว้ ระบบจะถือว่า 'เลือกทั้งหมด'")
    
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

    # กรองข้อมูลตามที่ผู้ใช้เลือกทีละเงื่อนไข
    filtered_df = df.copy()
    if len(selected_po) > 0:
        filtered_df = filtered_df[filtered_df['XD_PO_Clean'].isin(selected_po)]
    if len(selected_vendor) > 0:
        filtered_df = filtered_df[filtered_df['VENDER_NAME'].isin(selected_vendor)]
    if len(selected_item) > 0:
        filtered_df = filtered_df[filtered_df['Item_Display'].isin(selected_item)]
    if len(selected_booking) > 0:
        filtered_df = filtered_df[filtered_df['Booking ID'].isin(selected_booking)]

    st.info(f"📊 พบข้อมูลที่ตรงตามเงื่อนไข: **{len(filtered_df)}** รายการ (จากทั้งหมด {len(df)})")

    # 4. ปุ่มสร้างใบงาน
    if st.button("🚀 สร้างใบงานเดี๋ยวนี้", type="primary"):
        if len(filtered_df) == 0:
            st.error("❌ ไม่พบข้อมูล กรุณาปรับเปลี่ยนตัวกรองใหม่")
        else:
            with st.spinner("กำลังประมวลผลการปรับขนาดตัวหนังสือ..."):
                
                # เรียงลำดับข้อมูล: วันที่ -> สินค้า -> PO -> Booking ID -> เลขสาขา(น้อยไปมาก)
                filtered_df = filtered_df.sort_values(by=['Date', 'ITEM_NAME', 'XD_PO_Clean', 'Booking ID', 'Branch Code Num'])
                
                # จัดกลุ่มใบงานแยกตาม Booking ID
                groups = filtered_df.groupby(['Date', 'ITEM_NAME', 'DESCRIPTION', 'XD_PO_Clean', 'VENDER_NAME', 'Booking ID'])
                
                html_content = """
                <!DOCTYPE html>
                <html lang="th">
                <head>
                <meta charset="UTF-8">
                <style>
                    @page { size: A4 portrait; margin: 15mm; }
                    body { font-family: Tahoma, sans-serif; margin: 0; padding: 0; color: #000; font-size: 14pt; }
                    * { box-sizing: border-box; }
                    .page { page-break-after: always; position: relative; }
                    .page:last-child { page-break-after: avoid; }
                    .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 10px; margin-bottom: 15px; }
                    .title { font-size: 22pt; font-weight: bold; }
                    .doc-info { font-size: 13pt; margin-top: 5px; }
                    
                    /* ✨ ปรับขนาดกรอบข้อความด้านบนให้เล็กลงตามสั่ง */
                    .item-card { border: 2px solid #000; padding: 12px; margin-bottom: 15px; background-color: #f9f9f9; display: table; width: 100%; }
                    .card-col { display: table-cell; vertical-align: top; }
                    .card-col.left { width: 72%; }
                    .card-col.right { width: 28%; text-align: right; border-left: 1px dashed #ccc; padding-left: 15px; }
                    .label { font-size: 11pt; color: #555; }
                    .item-code { font-size: 22pt; font-weight: bold; line-height: 1.2; }
                    .po-text { font-size: 16pt; font-weight: bold; color: #d32f2f; margin-left: 10px; }
                    .booking-text { font-size: 13pt; font-weight: bold; color: #2e7d32; margin-top: 4px; }
                    .item-desc { font-size: 15pt; font-weight: bold; margin-top: 4px; line-height: 1.2; }
                    .vender-name { font-size: 12pt; font-weight: bold; color: #0056b3; margin-top: 4px; }
                    .total-qty { font-size: 30pt; font-weight: bold; line-height: 1.1; }
                    
                    /* ✨ ปรับขนาดตารางและตัวหนังสือด้านในให้ใหญ่ขึ้นเพื่อการมองเห็น */
                    table.data-table { width: 100%; border-collapse: collapse; }
                    table.data-table th { background-color: #e0e0e0; text-align: center; font-weight: bold; border: 1px solid #000; padding: 8px; font-size: 14pt; }
                    table.data-table td { border: 1px solid #000; padding: 10px; }
                    .text-center { text-align: center; }
                    
                    .footer-sign { margin-top: 30px; width: 100%; display: table; page-break-inside: avoid; }
                    .sign-box { display: table-cell; width: 50%; text-align: center; padding: 10px; font-size: 12pt; }
                    .sign-box .line { border-bottom: 1px dotted #000; margin: 40px auto 10px auto; width: 70%; }
                    .gap-col { border-top: none !important; border-bottom: none !important; background-color: #fff; width: 2%; padding: 0 !important; }
                </style>
                </head>
                <body>
                """
                
                for (target_date, item_code, item_desc, po_no, vender_name, booking_id), group in groups:
                    total_qty = group['ORDER_QTY'].sum()
                    uom_val = group['UOM'].iloc[0] if 'UOM' in group.columns else 'กล่อง'
                    
                    html_content += f"""
                    <div class="page">
                        <div class="header">
                            <div class="title">ใบจัด/กระจายสินค้า (PALLET TAG)</div>
                            <div class="doc-info">วันที่จัดส่ง: {target_date}</div>
                        </div>
                        <div class="item-card">
                            <div class="card-col left">
                                <div class="label">รหัสสินค้า (Item Code):</div>
                                <div class="item-code">{item_code} <span class="po-text">/ PO: {po_no}</span></div>
                                <div class="label" style="margin-top: 5px;">ชื่อสินค้า:</div>
                                <div class="item-desc">{item_desc}</div>
                                <div class="label" style="margin-top: 5px;">ซัพพลายเออร์:</div>
                                <div class="vender-name">{vender_name}</div>
                                <div class="booking-text">Booking ID: {booking_id}</div>
                            </div>
                            <div class="card-col right">
                                <div class="label">จำนวนรวม:</div>
                                <div class="total-qty">{total_qty:g} <br><span style="font-size:15pt;">{uom_val}</span></div>
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
                    
                    rows = list(group.iterrows())
                    half = math.ceil(len(rows) / 2)
                    
                    for i in range(half):
                        html_content += "<tr>"
                        
                        # ✨ ปรับตัวหนังสือรหัสสาขาและจำนวนกล่องฝั่งซ้ายให้ใหญ่ขึ้น (ขนาด 18pt และ 24pt)
                        row_left = rows[i][1]
                        html_content += f"""
                            <td class="text-center" style="font-size:18pt; font-weight:bold;">{row_left['Branch Code']}</td>
                            <td class="text-center" style="font-weight:bold; font-size:24pt;">{row_left['ORDER_QTY']:g}</td>
                            <td></td>
                            <td class="gap-col"></td>
                        """
                        
                        # ✨ ปรับตัวหนังสือรหัสสาขาและจำนวนกล่องฝั่งขวาให้ใหญ่ขึ้นเหมือนกัน
                        if i + half < len(rows):
                            row_right = rows[i + half][1]
                            html_content += f"""
                                <td class="text-center" style="font-size:18pt; font-weight:bold;">{row_right['Branch Code']}</td>
                                <td class="text-center" style="font-weight:bold; font-size:24pt;">{row_right['ORDER_QTY']:g}</td>
                                <td></td>
                            """
                        else:
                            html_content += "<td></td><td></td><td></td>"
                            
                        html_content += "</tr>"
                        
                    html_content += """
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
                    </div>
                    """
                html_content += "</body></html>"
                
                st.success(f"✅ ประมวลผลเสร็จสิ้น! สร้างใบงานได้ทั้งหมด {len(groups)} แผ่น")
                st.download_button(
                    label="📥 คลิกดาวน์โหลดใบงาน (Pallet Tag)",
                    data=html_content.encode('utf-8'),
                    file_name="Distribution_Tags_Perfect_Size.html",
                    mime="text/html"
                )