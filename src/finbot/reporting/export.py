import re
import os
import tempfile
import platform
import urllib.request
from fpdf import FPDF

def download_font():

    font_path = "DejaVuSans.ttf"
    # Сначала ищем уже установленный шрифт (в Docker: пакет fonts-dejavu-core)
    for candidate in (font_path, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(candidate):
            return candidate
    if not os.path.exists(font_path):
        print("Скачиваем кириллический шрифт для PDF...")
        try:
            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            print(f"Ошибка загрузки шрифта: {e}")
    return font_path

def clean_text(text):
    text = text.replace('₽', 'руб.')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^а-яА-ЯёЁa-zA-Z0-9\s\.,:;%()\-+/!?=<>@]', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text

def create_pdf(analytics_text, abc_text, opt_text, graph_buf, opt_graph_buf=None, anomaly_text=None, anomaly_graph_buf=None):
    font_path = download_font()
    
    pdf = FPDF()
    pdf.add_page()
    
    font_name = "Arial"

    if os.path.exists(font_path):
        try:
            pdf.add_font("DejaVu", "", font_path, uni=True)
        except TypeError:
            pdf.add_font("DejaVu", "", font_path)
        font_name = "DejaVu"
    elif platform.system() == "Windows" and os.path.exists("C:\\Windows\\Fonts\\arial.ttf"):
        try:
            pdf.add_font("SysArial", "", "C:\\Windows\\Fonts\\arial.ttf", uni=True)
        except TypeError:
            pdf.add_font("SysArial", "", "C:\\Windows\\Fonts\\arial.ttf")
        font_name = "SysArial"
        
    pdf.set_font(font_name, "", 16)

    pdf.cell(0, 10, "Комплексный Финансовый Отчет", ln=1, align="C")
    pdf.ln(5)
    
    pdf.set_font(font_name, "", 10)
    pdf.multi_cell(0, 6, clean_text(analytics_text))
    pdf.ln(5)
    
    if abc_text:
        pdf.add_page()
        pdf.set_font(font_name, "", 14)
        pdf.cell(0, 10, "ABC-анализ ассортимента", ln=1, align="L")
        pdf.ln(5)
        pdf.set_font(font_name, "", 10)
        pdf.multi_cell(0, 6, clean_text(abc_text))
        
    # ОПТИМИЗАЦИЯ БЮДЖЕТА (ML)
    if opt_text:
        pdf.add_page()
        pdf.set_font(font_name, "", 14)
        pdf.cell(0, 10, "SCM-Оптимизация и распределение бюджета", ln=1, align="L")
        pdf.ln(5)
        pdf.set_font(font_name, "", 10)
        pdf.multi_cell(0, 6, clean_text(opt_text))
        
        if opt_graph_buf:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_opt_img:
                tmp_opt_img.write(opt_graph_buf.getvalue())
                tmp_opt_img_path = tmp_opt_img.name
            
            current_y = pdf.get_y()
            if current_y > 130:
                pdf.add_page()
                current_y = 20
                
            pdf.image(tmp_opt_img_path, x=20, y=current_y + 10, w=170)
            os.remove(tmp_opt_img_path)
        
    if anomaly_text:
        pdf.add_page()
        pdf.set_font(font_name, "", 14)
        pdf.cell(0, 10, "Детекция аномалий (Isolation Forest)", ln=1, align="L")
        pdf.ln(5)
        pdf.set_font(font_name, "", 10)
        pdf.multi_cell(0, 6, clean_text(anomaly_text))
        
        if anomaly_graph_buf:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_anom_img:
                tmp_anom_img.write(anomaly_graph_buf.getvalue())
                tmp_anom_img_path = tmp_anom_img.name
            
            current_y = pdf.get_y()
            if current_y > 110:
                pdf.add_page()
                current_y = 20
                
            pdf.image(tmp_anom_img_path, x=20, y=current_y + 10, w=170)
            os.remove(tmp_anom_img_path)

    pdf.add_page()
    pdf.set_font(font_name, "", 14)
    pdf.cell(0, 10, "Финансовый Дашборд", ln=1, align="L")
    pdf.ln(5)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
        tmp_img.write(graph_buf.getvalue())
        tmp_img_path = tmp_img.name
        
    pdf.image(tmp_img_path, x=10, w=190)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name
        
    pdf.output(tmp_pdf_path)
    
    with open(tmp_pdf_path, "rb") as f:
        pdf_bytes = f.read()
        
    os.remove(tmp_img_path)
    os.remove(tmp_pdf_path)
    
    return pdf_bytes
