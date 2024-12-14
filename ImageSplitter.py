import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import math
import threading
from tkinterdnd2 import TkinterDnD, DND_FILES
import webbrowser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

root = TkinterDnD.Tk()
root.geometry("780x640")
root.title("Image Splitter v1.4 —— QwejayHuang")

# 初始化 ttkbootstrap 样式
style = ttk.Style("cosmo")

# 设置网格布局权重
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
grid_update_id = None  # 用于存储延迟网格更新的ID

# 新的全局变量以保存缩放比例
scale_width = 1.0
scale_height = 1.0

# 函数定义

def get_original_image(file_path, file_extension, page_num=None):
    if file_extension == '.pdf':
        doc = fitz.open(file_path)
        images = []
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                pix = page.get_pixmap(alpha=True, dpi=150)
                img_rgba = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
                img_white = Image.new("RGB", img_rgba.size, (255, 255, 255))
                img_rgb = Image.alpha_composite(img_white.convert("RGBA"), img_rgba).convert('RGB')
                images.append(img_rgb)
            except Exception as e:
                print(f"加载页面 {page_num} 时出错: {e}")
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
            set_status("宫格数必须为大于等于1的整数。", "danger")
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
            if extension.lower() in ['.pdf']:
                img.save(save_path, dpi=(dpi, dpi))
            else:
                img.save(save_path)
        else:
            img = convert_image_mode(img, extension)
            img.save(save_path)
    set_status(f"图像保存成功，共 {len(imgs)} 个部分。", "success")

def save_file():
    global imgs, file_extension, save_format_var, split_direction_var, grid_entry, dpi_var
    if not file_path:
        set_status("错误: 没有选择文件。", "danger")
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
            set_status("宫格数必须为大于等于1的整数。", "danger")
            return
        imgs_to_save = split_image(original_imgs, direction, grid_num)
    else:
        imgs_to_save = split_image(original_imgs, direction)
    
    save_images(imgs_to_save, save_extension)

def load_file_in_background(file_path, file_extension):
    global imgs, total_pages, current_page
    set_status("正在加载文件，请稍候...", "info")
    try:
        imgs = get_original_image(file_path, file_extension)
        if file_extension == '.pdf':
            doc = fitz.open(file_path)
            total_pages = len(doc)
            if total_pages > 1:
                page_spinbox.config(from_=1, to=total_pages)
                page_spinbox.state(['!disabled'])
                current_page = 1
                page_var.set(current_page)
                page_control_frame.grid(row=0, column=0, sticky='ew')  # 显示页码控件
            else:
                total_pages = 1
                page_spinbox.config(from_=1, to=1)
                page_spinbox.state(['disabled'])
                current_page = 1
                page_var.set(current_page)
                page_control_frame.grid_remove()  # 隐藏页码控件
        else:
            total_pages = 1
            page_spinbox.config(from_=1, to=1)
            page_spinbox.state(['disabled'])
            current_page = 1
            page_var.set(current_page)
            page_control_frame.grid_remove()  # 隐藏页码控件
        root.after(0, display_image)  # 在主线程中调度 display_image
        set_status(f"文件加载完成: {file_path}, 共 {total_pages} 页", "success")
    except Exception as e:
        set_status(f"文件加载失败: {str(e)}", "danger")

def open_file():
    global file_path, imgs, file_extension, total_pages, current_page
    file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.pdf;*.jpg;*.jpeg;*.png;*.bmp;*.webp")])
    if file_path:
        if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
            file_extension = os.path.splitext(file_path)[1].lower()
            supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.webp']
            if file_extension in supported_extensions:
                threading.Thread(target=load_file_in_background, args=(file_path, file_extension), daemon=True).start()
            else:
                set_status(f"不支持的文件类型: {file_extension}", "danger")
        else:
            set_status("文件不存在或不可读。", "danger")
    else:
        set_status("未选择文件。", "warning")

def update_current_page():
    global current_page
    current_page = int(page_var.get())
    display_image()
    set_status(f"当前页面: {current_page}/{total_pages}", "info")

def display_image():
    global scale_width, scale_height, image_position, img_width, img_height, image_canvas, imgs, current_page
    image_canvas.delete("image")  # 移除现有图像
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
        global image_position  # 声明为全局变量
        image_position = (x, y)  # 赋值图片位置
        image_canvas.create_image(x, y, anchor='nw', image=photo, tags="image")
        image_canvas.image = photo
        draw_split_line()  # 绘制分割线
        update_split_percentage_label()
    else:
        set_status("没有可供显示的图像。", "warning")

def draw_split_line():
    global img_width, img_height, image_position, image_canvas, split_direction_var, grid_entry, split_position
    image_canvas.delete("split_line")  # 清除现有分割线
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
        # "不分割" 不绘制分割线

def update_split_percentage_label():
    global split_percentage_label, split_position
    split_percentage_label.config(text=f"分割位置: {int(split_position * 100)}%")

def update_split_direction(*args):
    global grid_entry, split_direction_var, split_percentage_label, image_canvas
    direction = split_direction_var.get()
    if direction in ['垂直', '水平']:
        grid_entry['state'] = 'disabled'
        split_percentage_label.grid(row=0, column=3, padx=5)
        image_canvas.bind("<B1-Motion>", drag_split_line)
        split_percentage_label.config(text=f"分割位置: {int(split_position * 100)}%")
    elif direction == '多宫格':
        grid_entry['state'] = 'normal'
        split_percentage_label.grid_remove()
        image_canvas.unbind("<B1-Motion>")
    else:  # "不分割"
        grid_entry['state'] = 'disabled'
        split_percentage_label.grid_remove()
        image_canvas.unbind("<B1-Motion>")
    draw_split_line()

def drag_split_line(event):
    global split_position, scale_width, scale_height, image_canvas, split_direction_var, image_position
    direction = split_direction_var.get()
    if direction not in ['垂直', '水平']:
        return
    x, y = image_position
    img_displayed_width = int(img_width * scale_width)
    img_displayed_height = int(img_height * scale_height)
    if direction == '垂直':
        split_position = max(0, min(1, (event.x - x) / img_displayed_width))
    elif direction == '水平':
        split_position = max(0, min(1, (event.y - y) / img_displayed_height))
    draw_split_line()
    update_split_percentage_label()
    set_status(f"分割位置已调整为: {int(split_position * 100)}%", "info")

def handle_drop(event):
    global file_path, imgs, file_extension, total_pages, current_page
    file_paths = event.data.strip('{}').split()
    if file_paths:
        file_path = file_paths[0]
        print("拖放文件路径:", file_path)
        if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
            file_extension = os.path.splitext(file_path)[1].lower()
            supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.webp']
            if file_extension in supported_extensions:
                threading.Thread(target=load_file_in_background, args=(file_path, file_extension), daemon=True).start()
            else:
                set_status(f"不支持的文件类型: {file_extension}", "danger")
        else:
            set_status("文件不存在或不可读。", "danger")
    else:
        set_status("未选择文件。", "warning")

def set_status(message, color="secondary"):
    status_label.config(text=message, bootstyle=color)
    root.after(5000, lambda: status_label.config(text="", bootstyle="secondary"))

def update_dpi_state(*args):
    global dpi_menu
    dpi_menu.state(['!disabled'])

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
    global imgs, current_page, split_direction_var
    if imgs:
        img_width, img_height = imgs[current_page - 1].size
        if img_width > img_height:
            split_direction_var.set('垂直')
        else:
            split_direction_var.set('水平')
        update_split_direction()

def open_update_link():
    webbrowser.open("https://github.com/Qwejay/ImageSplitter")

# 旋转、镜像功能
def rotate_image():
    global imgs, current_page
    if imgs:
        img = imgs[current_page - 1]
        img = img.rotate(270, expand=True)  # 顺时针旋转90度
        imgs[current_page - 1] = img
        display_image()
        set_status("图片旋转成功。", "success")

def horizontal_flip():
    global imgs, current_page
    if imgs:
        img = imgs[current_page - 1]
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        imgs[current_page - 1] = img
        display_image()
        set_status("图片水平镜像成功。", "success")

def vertical_flip():
    global imgs, current_page
    if imgs:
        img = imgs[current_page - 1]
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        imgs[current_page - 1] = img
        display_image()
        set_status("图片垂直镜像成功。", "success")

# 创建GUI组件
top_menu = ttk.Frame(root)
top_menu.grid(row=0, column=0, sticky='ew')

open_button = ttk.Button(top_menu, text="打开文件", command=open_file, bootstyle="primary")
open_button.pack(side=LEFT, padx=10, pady=5)

split_direction_var = tk.StringVar()
split_direction_var.set('不分割')
split_direction_var.trace('w', update_split_direction)
direction_menu_label = ttk.Label(top_menu, text="分割类型:", bootstyle="secondary")
direction_menu_label.pack(side=LEFT, padx=5)
direction_menu = ttk.OptionMenu(top_menu, split_direction_var, '不分割', '不分割', '垂直', '水平', '多宫格')
direction_menu.pack(side=LEFT, padx=10, pady=5)

# 创建宫格数输入框
vcmd = (root.register(validate_grid_input), '%P')
grid_entry_label = ttk.Label(top_menu, text="宫格数:", bootstyle="secondary")
grid_entry_label.pack(side=LEFT, padx=5)
grid_entry = ttk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_entry.bind("<KeyRelease>", on_grid_entry_change)
grid_entry.pack(side=LEFT, padx=5)
grid_entry.insert(0, "9")
grid_entry['state'] = 'disabled'

# 创建保存格式下拉菜单
save_format_var = tk.StringVar()
save_format_var.set('.jpg')
save_format_var.trace('w', update_dpi_state)
save_format_label = ttk.Label(top_menu, text="保存格式:", bootstyle="secondary")
save_format_label.pack(side=LEFT, padx=5)
save_format_menu = ttk.OptionMenu(top_menu, save_format_var, '.JPG', '.PDF', '.JPG', '.PNG', '.BMP', '.WEBP')
save_format_menu.pack(side=LEFT, padx=10, pady=5)

dpi_var = tk.StringVar()
dpi_var.set("默认")
dpi_label = ttk.Label(top_menu, text="保存DPI:", bootstyle="secondary")
dpi_label.pack(side=LEFT, padx=5)
dpi_menu = ttk.OptionMenu(top_menu, dpi_var, "默认", "默认", "72", "150", "300")
dpi_menu.pack(side=LEFT, padx=10, pady=5)

save_button = ttk.Button(top_menu, text="保存文件", command=save_file, bootstyle="primary")
save_button.pack(side=LEFT, padx=10, pady=5)

preview_frame = ttk.Frame(root)
preview_frame.grid(row=1, column=0, sticky='nsew')

# 创建当前页面控制框架
page_control_frame = ttk.Frame(preview_frame, style='Custom.TFrame')
style.configure('Custom.TFrame', background='lightgrey')

page_label = ttk.Label(page_control_frame, text="当前页面：", bootstyle="secondary")
page_label.pack(side=LEFT, padx=5)

page_var = tk.StringVar()
page_spinbox = ttk.Spinbox(page_control_frame, from_=1, to=1, textvariable=page_var, width=5)
page_spinbox.pack(side=LEFT, padx=5)
page_var.trace_add('write', lambda *args: update_current_page())

# 在preview_frame中布局page_control_frame
page_control_frame.grid(row=0, column=0, sticky='ew')

# 布局image_canvas在page_control_frame下方
image_canvas = ttk.Canvas(preview_frame, background="#e0e0e0")
image_canvas.grid(row=1, column=0, sticky='nsew')

# 配置preview_frame的行权重
preview_frame.grid_rowconfigure(0, weight=0)
preview_frame.grid_rowconfigure(1, weight=1)
preview_frame.grid_columnconfigure(0, weight=1)

split_percentage_label = ttk.Label(preview_frame, text="分割位置: 50%", bootstyle="secondary")
split_percentage_label.grid(row=0, column=3, padx=5)

# 创建按钮框架并放置在第1行
button_frame = ttk.Frame(preview_frame)
button_frame.grid(row=2, column=0, sticky='ew')

# 配置按钮框架的列权重
button_frame.grid_columnconfigure(0, weight=0)
button_frame.grid_columnconfigure(1, weight=1)
button_frame.grid_columnconfigure(2, weight=0)
button_frame.grid_columnconfigure(3, weight=1)

# 按钮内框架放置在第2列
button_inner_frame = ttk.Frame(button_frame)
button_inner_frame.grid(row=0, column=2, padx=5)

rotate_button = ttk.Button(button_inner_frame, text="旋转", command=rotate_image, bootstyle="secondary")
rotate_button.pack(side=LEFT, padx=5)

horizontal_flip_button = ttk.Button(button_inner_frame, text="水平镜像", command=horizontal_flip, bootstyle="secondary")
horizontal_flip_button.pack(side=LEFT, padx=5)

vertical_flip_button = ttk.Button(button_inner_frame, text="垂直镜像", command=vertical_flip, bootstyle="secondary")
vertical_flip_button.pack(side=LEFT, padx=5)

root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', handle_drop)

status_bar = ttk.Frame(root, relief='sunken', borderwidth=1)
status_bar.grid(row=2, column=0, sticky='ew')

status_label = ttk.Label(status_bar, text="", bootstyle="secondary", anchor='w', padding=(5, 0))
status_label.pack(side=LEFT, fill=X, expand=True)

update_link = ttk.Label(status_bar, text="检查更新", cursor="hand2", foreground="blue")
update_link.pack(side=RIGHT, padx=5)
update_link.bind("<Button-1>", lambda e: open_update_link())

update_split_direction()

# 自动检测图像方向并设置默认分割方向
auto_detect_split_direction()

root.mainloop()