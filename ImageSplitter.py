import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import math
import threading
from tkinterdnd2 import TkinterDnD, DND_FILES

root = TkinterDnD.Tk()
root.geometry("740x640")
root.title("Image Splitter v1.3 —— QwejayHuang")

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
grid_update_id = None  # 用于存储延迟更新的ID

# 新增全局变量保存缩放比例
scale_width = 1.0
scale_height = 1.0

# 函数定义

def get_original_image(file_path, file_extension, page_num=None):
    if file_extension == '.pdf':
        doc = fitz.open(file_path)
        images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # 限制 DPI 为 150，避免高分辨率图像占用过多内存
            pix = page.get_pixmap(alpha=True, dpi=150)
            img_rgba = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            img_white = Image.new("RGB", img_rgba.size, (255, 255, 255))
            img_rgb = Image.alpha_composite(img_white.convert("RGBA"), img_rgba).convert('RGB')
            images.append(img_rgb)
        return images
    else:
        return [Image.open(file_path).convert("RGB")]

def split_image(imgs, direction, grid_num=1):
    split_imgs = []
    if direction == '多宫格':
        try:
            grid_num = int(grid_num)
            if grid_num < 1:
                raise ValueError
            rows = int(math.ceil(math.sqrt(grid_num)))
            cols = int(math.ceil(grid_num / rows))
            for img in imgs:
                img_width, img_height = img.size
                cell_width = img_width // cols
                cell_height = img_height // rows
                for r in range(rows):
                    for c in range(cols):
                        left = c * cell_width
                        upper = r * cell_height
                        right = left + cell_width
                        lower = upper + cell_height
                        split_img = img.crop((left, upper, right, lower))
                        split_imgs.append(split_img)
        except ValueError:
            set_status("宫格数必须为大于等于1的整数。", "red")
            return split_imgs
    elif direction == '垂直':
        for img in imgs:
            split_width = int(img.width * split_position)
            left_img = img.crop((0, 0, split_width, img.height))
            right_img = img.crop((split_width, 0, img.width, img.height))
            split_imgs.extend([left_img, right_img])
    elif direction == '水平':
        for img in imgs:
            split_height = int(img.height * split_position)
            top_img = img.crop((0, 0, img.width, split_height))
            bottom_img = img.crop((0, split_height, img.width, img.height))
            split_imgs.extend([top_img, bottom_img])
    elif direction == '不分割':
        split_imgs.extend(imgs)
    return split_imgs

def convert_image_mode(img, extension):
    if extension.lower() in ['.jpg', '.jpeg']:
        return img.convert('RGB')
    else:
        return img

def save_images(imgs, extension):
    selected_dpi = dpi_var.get()
    for i, img in enumerate(imgs):
        save_path = os.path.splitext(file_path)[0] + f"_part{i+1}" + extension
        if selected_dpi != "默认":
            dpi = int(selected_dpi)
            original_dpi = img.info.get('dpi', (300, 300))
            scaling_factor = dpi / original_dpi[0]
            new_width = int(img.width * scaling_factor)
            new_height = int(img.height * scaling_factor)
            img = img.resize((new_width, new_height), resample=Image.LANCZOS)
            img = convert_image_mode(img, extension)
            if extension.lower() in ['.pdf', '.tiff']:
                img.save(save_path, dpi=(dpi, dpi))
            else:
                img.save(save_path)
        else:
            img = convert_image_mode(img, extension)
            img.save(save_path)
    set_status(f"图像保存成功，共 {len(imgs)} 个部分。", "green")

def save_file():
    if not file_path:
        set_status("错误: 没有选择文件。", "red")
        return
    
    save_extension = save_format_var.get()
    original_imgs = imgs
    
    direction = split_direction_var.get()
    
    if direction == '多宫格':
        grid_num = grid_entry.get()
        if grid_num == "":
            grid_num = "1"
        try:
            grid_num = int(grid_num)
            if grid_num < 1:
                raise ValueError
        except ValueError:
            set_status("宫格数必须为大于等于1的整数。", "red")
            return
        imgs_to_save = split_image(original_imgs, direction, grid_num)
    else:
        imgs_to_save = split_image(original_imgs, direction)
    
    save_images(imgs_to_save, save_extension)

def load_file_in_background(file_path, file_extension):
    global imgs, total_pages, current_page
    set_status("正在加载文件，请稍候...", "blue")
    try:
        imgs = get_original_image(file_path, file_extension)
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
        set_status(f"文件加载完成: {file_path}", "green")
        display_image()  # 显示图片
        draw_split_line()  # 重新绘制分割线
    except Exception as e:
        set_status(f"文件加载失败: {str(e)}", "red")

def open_file():
    global file_path, imgs, file_extension, total_pages, current_page
    file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.pdf;*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.gif;*.webp;*.ico")])
    if file_path:
        if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
            file_extension = os.path.splitext(file_path)[1].lower()
            supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp', '.ico']
            if file_extension in supported_extensions:
                # 使用后台线程加载文件
                threading.Thread(target=load_file_in_background, args=(file_path, file_extension), daemon=True).start()
            else:
                set_status(f"不支持的文件类型: {file_extension}", "red")
        else:
            set_status("文件不存在或不可读。", "red")
    else:
        set_status("未选择文件。", "orange")

def update_current_page():
    global current_page
    current_page = int(page_spinbox.get())
    display_image()
    set_status(f"当前页面: {current_page}/{total_pages}", "blue")

def display_image():
    global scale_width, scale_height, image_position, img_width, img_height
    image_canvas.delete("image")  # 只清除图片部分，保留分割线
    if imgs:
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
        scale_width = new_width / img_width
        scale_height = new_height / img_height
        resized_img = img_to_display.resize((new_width, new_height))
        photo = ImageTk.PhotoImage(resized_img)
        x = (canvas_width - new_width) / 2
        y = (canvas_height - new_height) / 2
        image_position = (x, y)
        image_canvas.create_image(x, y, anchor='nw', image=photo, tags="image")
        image_canvas.image = photo
        draw_split_line()  # 重新绘制分割线
        update_split_percentage_label()
    else:
        set_status("没有可供显示的图像。", "orange")

def draw_split_line():
    global img_width, img_height, image_position
    image_canvas.delete("split_line")  # 清除旧的分割线
    if 'image_position' in globals():
        x, y = image_position
        img_displayed_width = int(img_width * scale_width)
        img_displayed_height = int(img_height * scale_height)
        direction = split_direction_var.get()
        if direction == '垂直':
            split_x = x + img_displayed_width * split_position
            image_canvas.create_line(split_x, y, split_x, y + img_displayed_height, fill='red', width=2, tags="split_line")
        elif direction == '水平':
            split_y = y + img_displayed_height * split_position
            image_canvas.create_line(x, split_y, x + img_displayed_width, split_y, fill='red', width=2, tags="split_line")
        elif direction == '多宫格':
            try:
                grid_num = int(grid_entry.get())
                rows = int(math.ceil(math.sqrt(grid_num)))
                cols = int(math.ceil(grid_num / rows))
                cell_width = img_displayed_width / cols
                cell_height = img_displayed_height / rows
                for i in range(1, cols):
                    split_x = x + cell_width * i
                    image_canvas.create_line(split_x, y, split_x, y + img_displayed_height, fill='red', width=2, tags="split_line")
                for j in range(1, rows):
                    split_y = y + cell_height * j
                    image_canvas.create_line(x, split_y, x + img_displayed_width, split_y, fill='red', width=2, tags="split_line")
            except ValueError:
                pass

def update_split_percentage_label():
    split_percentage_label.config(text=f"分割位置: {int(split_position * 100)}%")

def update_split_direction(*args):
    direction = split_direction_var.get()
    if direction == '多宫格':
        grid_entry.config(state='normal')
        split_percentage_label.pack_forget()
        image_canvas.unbind("<B1-Motion>")
    else:
        grid_entry.config(state='disabled')
        split_percentage_label.pack(side='top', pady=5)
        image_canvas.bind("<B1-Motion>", drag_split_line)
    draw_split_line()
    set_status(f"分割方向已更改为: {direction}", "blue")

def drag_split_line(event):
    direction = split_direction_var.get()
    if direction == '不分割' or direction == '多宫格':
        return
    global split_position
    canvas_width = image_canvas.winfo_width()
    canvas_height = image_canvas.winfo_height()
    if direction == '垂直':
        split_position = max(0, min(1, event.x / (scale_width * canvas_width)))
    elif direction == '水平':
        split_position = max(0, min(1, event.y / (scale_height * canvas_height)))
    draw_split_line()
    update_split_percentage_label()
    set_status(f"分割位置已调整为: {int(split_position * 100)}%", "blue")

def handle_drop(event):
    global file_path, imgs, file_extension, total_pages, current_page
    file_path = event.data.strip('{}')
    if file_path:
        if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
            file_extension = os.path.splitext(file_path)[1].lower()
            supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp', '.ico']
            if file_extension in supported_extensions:
                # 使用后台线程加载文件
                threading.Thread(target=load_file_in_background, args=(file_path, file_extension), daemon=True).start()
            else:
                set_status(f"不支持的文件类型: {file_extension}", "red")
        else:
            set_status("文件不存在或不可读。", "red")
    else:
        set_status("未选择文件。", "orange")

def set_status(message, color="black"):
    status_label.config(text=message, fg=color)
    root.after(5000, lambda: status_label.config(text="", fg="black"))

def update_dpi_state(*args):
    dpi_menu.config(state='normal')  # 始终启用DPI设置

def validate_grid_input(new_value):
    if new_value == "":
        return True
    try:
        int(new_value)
        return True
    except ValueError:
        return False

def on_grid_entry_change(event):
    global grid_update_id
    if grid_update_id:
        root.after_cancel(grid_update_id)
    grid_update_id = root.after(500, update_split_lines)

def update_split_lines():
    draw_split_line()

def auto_detect_split_direction():
    if imgs:
        img_width, img_height = imgs[current_page - 1].size
        if img_width > img_height:
            split_direction_var.set('垂直')
        else:
            split_direction_var.set('水平')
        update_split_direction()

# 创建 GUI 元件

top_menu = tk.Frame(root, bg='white')
top_menu.grid(row=0, column=0, sticky='ew')

open_button = tk.Button(top_menu, text="打开文件", command=open_file, bg='#4CAF50', fg='white')
open_button.pack(side='left', padx=10, pady=5)

split_direction_var = tk.StringVar()
split_direction_var.set('不分割')
split_direction_var.trace('w', update_split_direction)
direction_menu_label = tk.Label(top_menu, text="分割方向:", bg='white', fg='black')
direction_menu_label.pack(side='left', padx=5)
direction_menu = tk.OptionMenu(top_menu, split_direction_var, '不分割', '垂直', '水平', '多宫格')
direction_menu.config(bg='white', fg='black')
direction_menu.pack(side='left', padx=10, pady=5)

vcmd = (root.register(validate_grid_input), '%P')
grid_entry_label = tk.Label(top_menu, text="宫格数:", bg='white', fg='black')
grid_entry_label.pack(side='left', padx=5)
grid_entry = tk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_entry.bind("<KeyRelease>", on_grid_entry_change)
grid_entry.pack(side='left', padx=5)
grid_entry.insert(0, "9")
grid_entry.config(state='disabled')

save_format_var = tk.StringVar()
save_format_var.set('.jpg')
save_format_var.trace('w', update_dpi_state)
save_format_label = tk.Label(top_menu, text="保存格式:", bg='white', fg='black')
save_format_label.pack(side='left', padx=5)
save_format_menu = tk.OptionMenu(top_menu, save_format_var, '.jpg', '.pdf', '.png', '.bmp', '.tiff', '.webp', '.ico')
save_format_menu.config(bg='white', fg='black')
save_format_menu.pack(side='left', padx=10, pady=5)

dpi_var = tk.StringVar()
dpi_var.set("默认")
dpi_label = tk.Label(top_menu, text="保存DPI:", bg='white', fg='black')
dpi_label.pack(side='left', padx=5)
dpi_menu = tk.OptionMenu(top_menu, dpi_var, "默认", "72", "150", "300", "600")
dpi_menu.config(bg='white', fg='black')
dpi_menu.pack(side='left', padx=10, pady=5)

save_button = tk.Button(top_menu, text="保存文件", command=save_file, bg='#4CAF50', fg='white')
save_button.pack(side='left', padx=10, pady=5)

preview_frame = tk.Frame(root, bg='#F2F2F2')
preview_frame.grid(row=1, column=0, sticky='nsew')

split_percentage_label = tk.Label(preview_frame, text="分割位置: 50%", bg='#F2F2F2', fg='black')
split_percentage_label.pack(side='top', pady=5)

image_canvas = tk.Canvas(preview_frame, bg='#E0E0E0')
image_canvas.pack(side='top', fill='both', expand=True)

page_control_frame = tk.Frame(preview_frame, bg='#F2F2F2')
page_control_frame.pack(side='bottom', pady=5, anchor='center')

page_label = tk.Label(page_control_frame, text="当前页面：", bg='#F2F2F2', fg='black')
page_label.pack(side='left', padx=5)

page_spinbox = tk.Spinbox(page_control_frame, from_=1, to=1, command=update_current_page, width=5)
page_spinbox.pack(side='left', padx=5)

image_canvas.bind("<Configure>", lambda event: display_image())

root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', handle_drop)

status_bar = tk.Frame(root, bg='#F2F2F2', relief='sunken', bd=1)
status_bar.grid(row=2, column=0, sticky='ew')

status_label = tk.Label(status_bar, text="", bg='#F2F2F2', fg='black', anchor='w', padx=5)
status_label.pack(side='left', fill='x', expand=True)

update_split_direction()

# 自动检测图片方向并设置默认分割线
auto_detect_split_direction()

root.mainloop()