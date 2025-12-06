import os
from shutil import copy2, copytree
from PIL import Image, ImageDraw, ImageFont
import qrcode

def main():
    base = os.path.dirname(os.path.dirname(__file__))
    os.chdir(base)
    os.makedirs('assets', exist_ok=True)
    if os.path.exists('faults_library.json'):
        copy2('faults_library.json', os.path.join('assets','faults_library.json'))
    if os.path.exists('yolov8n.pt'):
        copy2('yolov8n.pt', os.path.join('assets','yolov8n.pt'))
    src_adapter = os.path.join('backend','models','phi35_lora_adapter')
    dst_adapter = os.path.join('assets','phi35_lora_adapter')
    if os.path.isdir(src_adapter) and not os.path.exists(dst_adapter):
        copytree(src_adapter, dst_adapter)

    logo_path = os.path.join('assets','logo.png')
    if not os.path.exists(logo_path):
        img = Image.new('RGBA', (480, 160), (255, 255, 255, 0))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except Exception:
            font = ImageFont.load_default()
        d.text((20, 50), "Robot-Technician", fill=(0,0,0,255), font=font)
        img.save(logo_path)

    qr_path = os.path.join('assets','qr_code.png')
    if not os.path.exists(qr_path):
        qr = qrcode.QRCode(version=2, box_size=6, border=1)
        qr.add_data('https://example.com/robot-technician')
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)
    print('Assets prepared in', os.path.join(base,'assets'))

if __name__ == '__main__':
    main()