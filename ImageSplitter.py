import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import io
from tkinterdnd2 import TkinterDnD, DND_FILES

root = TkinterDnD.Tk()
root.title("Image Splitter v1.1 —— QwejayHuang")

# 设置 grid 布局权重
root.grid_rowconfigure(0, weight=0)
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=0)
root.grid_columnconfigure(0, weight=1)

# 全局变量
file_path = ""
imgs = []
file_extension = ""
split_position = 0.5
split_direction = '不分割'
save_format = '.pdf'
current_page = 1
total_pages = 1

# 函数定义

# 获取原始图像
def get_original_image():
    if file_extension == '.pdf':
        doc = fitz.open(file_path)
        images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(alpha=True, dpi=300)
            img_rgba = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            img_white = Image.new("RGB", img_rgba.size, (255, 255, 255)).convert("RGBA")
            img_rgb = Image.alpha_composite(img_white, img_rgba)
            images.append(img_rgb)
        return images
    else:
        return [Image.open(file_path).convert("RGB")]

# 分割图像
def split_image(imgs, direction):
    split_imgs = []
    for img in imgs:
        if direction == '垂直':
            split_width = int(img.width * split_position)
            left_img = img.crop((0, 0, split_width, img.height))
            right_img = img.crop((split_width, 0, img.width, img.height))
            split_imgs.extend([left_img, right_img])
        elif direction == '水平':
            split_height = int(img.height * split_position)
            top_img = img.crop((0, 0, img.width, split_height))
            bottom_img = img.crop((0, split_height, img.width, img.height))
            split_imgs.extend([top_img, bottom_img])
        elif direction == '不分割':
            split_imgs.append(img)
    return split_imgs

# 保存图像
def save_images(imgs, extension):
    selected_dpi = dpi_var.get()
    if extension == '.pdf':
        new_doc = fitz.open()
        for img in imgs:
            original_dpi = img.info.get('dpi', (300, 300))
            if isinstance(original_dpi, (list, tuple)):
                original_dpi_width = original_dpi[0]
                original_dpi_height = original_dpi[1]
            else:
                original_dpi_width = original_dpi
                original_dpi_height = original_dpi
            img_rgb = img.convert("RGB")
            img_rgb = img.resize((int(img.width * selected_dpi / original_dpi_width),
                                  int(img.height * selected_dpi / original_dpi_height)))
            with io.BytesIO() as output:
                img_rgb.save(output, format="JPEG", quality=85)
                image_bytes = output.getvalue()
            width = img_rgb.width / (selected_dpi / 72)
            height = img_rgb.height / (selected_dpi / 72)
            page = new_doc.new_page(width=width, height=height)
            page.insert_image(fitz.Rect(0, 0, width, height), stream=image_bytes)
        save_path = os.path.splitext(file_path)[0] + "_split.pdf"
        new_doc.save(save_path)
        set_status("PDF保存成功。", "green")
    else:
        format_mode_map = {
            '.jpg': 'RGB',
            '.jpeg': 'RGB',
            '.png': 'RGBA',
            '.bmp': 'RGBA',
            '.tiff': 'RGBA',
            '.webp': 'RGBA',
            '.ico': 'RGBA',
        }
        mode = format_mode_map.get(extension.lower(), 'RGBA')
        for i, img in enumerate(imgs):
            original_dpi = img.info.get('dpi', (300, 300))
            if isinstance(original_dpi, (list, tuple)):
                original_dpi_width = original_dpi[0]
                original_dpi_height = original_dpi[1]
            else:
                original_dpi_width = original_dpi
                original_dpi_height = original_dpi
            img = img.resize((int(img.width * selected_dpi / original_dpi_width),
                              int(img.height * selected_dpi / original_dpi_height)))
            save_path = os.path.splitext(file_path)[0] + f"_part{i+1}" + extension
            if mode == 'RGB':
                img.convert("RGB").save(save_path, quality=95)
            else:
                img.save(save_path)
        set_status(f"图像保存成功，共 {len(imgs)} 个部分。", "green")

# 保存文件
def save_file():
    if not file_path:
        set_status("错误: 没有选择文件。", "red")
        return
    
    save_extension = save_format_var.get()
    original_imgs = imgs
    
    direction = split_direction_var.get()
    
    if direction == '不分割':
        imgs_to_save = original_imgs
    else:
        imgs_to_save = split_image(original_imgs, direction)
    
    update_estimated_size()
    save_images(imgs_to_save, save_extension)

# 打开文件按钮
def open_file():
    global file_path, imgs, file_extension, total_pages, current_page
    file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.pdf;*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.gif;*.webp;*.ico")])
    if file_path:
        if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
            file_extension = os.path.splitext(file_path)[1].lower()
            supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp', '.ico']
            if file_extension in supported_extensions:
                imgs = get_original_image()
                if file_extension == '.pdf':
                    doc = fitz.open(file_path)
                    total_pages = len(doc)
                    page_spinbox.config(from_=1, to=total_pages)
                    page_spinbox.config(state='normal')
                    current_page = 1
                else:
                    total_pages = 1
                    page_spinbox.config(from_=1, to=1)
                    page_spinbox.config(state='disabled')
                    current_page = 1
                display_image()
                set_status(f"文件已打开: {file_path}", "blue")
                update_estimated_size()
            else:
                set_status(f"不支持的文件类型: {file_extension}", "red")
        else:
            set_status("文件不存在或不可读。", "red")
    else:
        set_status("未选择文件。", "orange")

# 更新当前页面
def update_current_page():
    global current_page
    current_page = int(page_spinbox.get())
    display_image()
    set_status(f"当前页面: {current_page}/{total_pages}", "blue")

# 显示图像到Canvas
def display_image():
    if imgs:
        image_canvas.delete("all")
        canvas_width = image_canvas.winfo_width()
        canvas_height = image_canvas.winfo_height()
        img_to_display = imgs[current_page - 1]
        img_width, img_height = img_to_display.size
        if img_width / img_height > canvas_width / canvas_height:
            new_width = canvas_width
            new_height = int(new_width * img_height / img_width)
        else:
            new_height = canvas_height
            new_width = int(new_height * img_width / img_height)
        resized_img = img_to_display.resize((new_width, new_height))
        photo = ImageTk.PhotoImage(resized_img)
        image_canvas.create_image(canvas_width / 2, canvas_height / 2, anchor='center', image=photo)
        image_canvas.image = photo
        draw_split_line()
        update_split_percentage_label()
    else:
        set_status("没有可供显示的图像。", "orange")

# 绘制分割线
def draw_split_line():
    image_canvas.delete("split_line")
    canvas_width = image_canvas.winfo_width()
    canvas_height = image_canvas.winfo_height()
    direction = split_direction_var.get()
    if direction == '垂直':
        split_x = int(canvas_width * split_position)
        image_canvas.create_line(split_x, 0, split_x, canvas_height, fill='red', width=2, tags="split_line")
    elif direction == '水平':
        split_y = int(canvas_height * split_position)
        image_canvas.create_line(0, split_y, canvas_width, split_y, fill='red', width=2, tags="split_line")
    elif direction == '不分割':
        pass
    update_split_percentage_label()

# 更新分割百分比标签
def update_split_percentage_label():
    split_percentage_label.config(text=f"分割位置: {int(split_position * 100)}%")

# 更新分割方向
def update_split_direction(event=None):
    direction = split_direction_var.get()
    if direction == '不分割':
        split_position = 0.5
    draw_split_line()
    set_status(f"分割方向已更改为: {direction}", "blue")

# 拖动分割线
def drag_split_line(event):
    global split_position
    canvas_width = image_canvas.winfo_width()
    canvas_height = image_canvas.winfo_height()
    direction = split_direction_var.get()
    if direction == '垂直':
        split_position = max(0, min(1, event.x / canvas_width))
    elif direction == '水平':
        split_position = max(0, min(1, event.y / canvas_height))
    draw_split_line()
    set_status(f"分割位置已调整为: {int(split_position * 100)}%", "blue")

# 处理拖放文件
def handle_drop(event):
    global file_path, imgs, file_extension, total_pages, current_page
    file_path = event.data.strip('{}')
    if file_path:
        if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
            file_extension = os.path.splitext(file_path)[1].lower()
            supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp', '.ico']
            if file_extension in supported_extensions:
                imgs = get_original_image()
                if file_extension == '.pdf':
                    doc = fitz.open(file_path)
                    total_pages = len(doc)
                    page_spinbox.config(from_=1, to=total_pages)
                    page_spinbox.config(state='normal')
                    current_page = 1
                else:
                    total_pages = 1
                    page_spinbox.config(from_=1, to=1)
                    page_spinbox.config(state='disabled')
                    current_page = 1
                display_image()
                set_status(f"文件已打开: {file_path}", "blue")
                update_estimated_size()
            else:
                set_status(f"不支持的文件类型: {file_extension}", "red")
        else:
            set_status("文件不存在或不可读。", "red")
    else:
        set_status("未选择文件。", "orange")

# 设置状态栏文本
def set_status(message, color="black"):
    status_label.config(text=message, fg=color)
    root.after(5000, lambda: status_label.config(text="", fg="black"))  # 5秒后清除消息

# 计算图像大小预估
def estimate_size(img, dpi, extension):
    width, height = img.size
    # 获取原始DPI
    original_dpi = img.info.get('dpi', (300, 300))
    if isinstance(original_dpi, (list, tuple)):
        original_dpi_width = original_dpi[0]
        original_dpi_height = original_dpi[1]
    else:
        original_dpi_width = original_dpi
        original_dpi_height = original_dpi
    # 计算调整后的像素数量
    new_width = int(width * dpi / original_dpi_width)
    new_height = int(height * dpi / original_dpi_height)
    # 假设RGB图像，每个像素3字节，压缩率根据格式不同而不同
    pixel_count = new_width * new_height * 3
    if extension.lower() in ['.jpg', '.jpeg']:
        compressed_size = pixel_count / 10  # 假设JPEG压缩率为10倍
    elif extension.lower() == '.png':
        compressed_size = pixel_count / 3  # 假设PNG压缩率为3倍
    elif extension.lower() == '.bmp':
        compressed_size = pixel_count
    else:
        compressed_size = pixel_count / 5  # 其他格式假设压缩率为5倍
    return compressed_size

# 更新状态栏显示预估大小
def update_estimated_size(*args):
    if imgs:
        selected_dpi = dpi_var.get()
        extension = save_format_var.get()
        total_size = 0
        for img in imgs:
            total_size += estimate_size(img, selected_dpi, extension)
        # 将字节转换为MB
        size_mb = total_size / (1024 * 1024)
        estimated_size_label.config(text=f"预计大小: {size_mb:.2f} MB")
    else:
        estimated_size_label.config(text="预计大小: 0.00 MB")

# 更新DPI选择时更新预估大小
def update_dpi(*args):
    update_estimated_size()
    set_status(f"DPI设置为: {dpi_var.get()}", "blue")

# 创建 GUI 元件

# 创建顶部菜单栏
top_menu = tk.Frame(root, bg='white')
top_menu.grid(row=0, column=0, sticky='ew')

open_button = tk.Button(top_menu, text="打开文件", command=open_file, bg='#4CAF50', fg='white')
open_button.pack(side='left', padx=10, pady=5)

split_direction_var = tk.StringVar()
split_direction_var.set('不分割')
direction_menu_label = tk.Label(top_menu, text="分割方向:", bg='white', fg='black')
direction_menu_label.pack(side='left', padx=5)
direction_menu = tk.OptionMenu(top_menu, split_direction_var, '垂直', '水平', '不分割', command=update_split_direction)
direction_menu.config(bg='white', fg='black')
direction_menu.pack(side='left', padx=10, pady=5)

save_format_var = tk.StringVar()
save_format_var.set('.jpg')
save_format_label = tk.Label(top_menu, text="保存格式:", bg='white', fg='black')
save_format_label.pack(side='left', padx=5)
save_format_menu = tk.OptionMenu(top_menu, save_format_var, '.jpg', '.pdf', '.png', '.bmp', '.tiff', '.webp', '.ico', command=update_estimated_size)
save_format_menu.config(bg='white', fg='black')
save_format_menu.pack(side='left', padx=10, pady=5)

# DPI选项
dpi_var = tk.IntVar()
dpi_var.set(150)  # 默认DPI
dpi_label = tk.Label(top_menu, text="保存DPI:", bg='white', fg='black')
dpi_label.pack(side='left', padx=5)
dpi_menu = tk.OptionMenu(top_menu, dpi_var, 72, 150, 300, 600, command=update_dpi)
dpi_menu.config(bg='white', fg='black')
dpi_menu.pack(side='left', padx=10, pady=5)

save_button = tk.Button(top_menu, text="保存文件", command=save_file, bg='#4CAF50', fg='white')
save_button.pack(side='left', padx=10, pady=5)

# 预计文件大小标签
estimated_size_label = tk.Label(top_menu, text="预计大小: 0.00 MB", bg='white', fg='black')
estimated_size_label.pack(side='left', padx=10)

# 创建底部预览区域
preview_frame = tk.Frame(root, bg='#F2F2F2')
preview_frame.grid(row=1, column=0, sticky='nsew')

# 放置“分割位置”标签在顶部
split_percentage_label = tk.Label(preview_frame, text="分割位置: 50%", bg='#F2F2F2', fg='black')
split_percentage_label.pack(side='top', pady=5)

# 放置图像画布在中间，并设置其可扩展
image_canvas = tk.Canvas(preview_frame, bg='#E0E0E0')
image_canvas.pack(side='top', fill='both', expand=True)

# 创建一个新的框架用于页面控制，并在底部居中放置
page_control_frame = tk.Frame(preview_frame, bg='#F2F2F2')
page_control_frame.pack(side='bottom', pady=5, anchor='center')

# 在page_control_frame内部使用pack布局
page_label = tk.Label(page_control_frame, text="当前页面：", bg='#F2F2F2', fg='black')
page_label.pack(side='left', padx=5)

page_spinbox = tk.Spinbox(page_control_frame, from_=1, to=1, command=update_current_page, width=5)
page_spinbox.pack(side='left', padx=5)

# 绑定事件
image_canvas.bind("<Configure>", lambda event: display_image())
image_canvas.bind("<B1-Motion>", drag_split_line)

# 处理拖放文件
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', handle_drop)

# 添加状态栏
status_bar = tk.Frame(root, bg='#F2F2F2', relief='sunken', bd=1)
status_bar.grid(row=2, column=0, sticky='ew')

status_label = tk.Label(status_bar, text="", bg='#F2F2F2', fg='black', anchor='w', padx=5)
status_label.pack(side='left', fill='x', expand=True)

# 进入主循环
root.mainloop()