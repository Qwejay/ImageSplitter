import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import threading
from tkinterdnd2 import TkinterDnD, DND_FILES
import webbrowser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pillow_heif

# 全局变量
file_path = ""
imgs = []
file_extension = ""
split_position = 0.5
split_direction = '不分割'
save_format = '.pdf'
current_page = 1
total_pages = 1
split_percentage_label = None
window_resize_id = None
grid_row_entry = None
grid_col_entry = None
img_display_x = 0
img_display_y = 0
img_display_width = 0
img_display_height = 0
split_color_var = None
zoom_scale = 1.0  # 缩放比例
img_offset_x = 0  # 图像偏移量
img_offset_y = 0
is_dragging = False  # 是否正在拖动
drag_start_x = 0  # 拖动起始位置
drag_start_y = 0

# 颜色映射字典
color_mapping = {
    '红色': 'red',
    '蓝色': 'blue',
    '绿色': 'green',
    '黑色': 'black',
    '黄色': 'yellow'
}

# 函数定义
def split_image(imgs, direction, grid_row=1, grid_col=1):
    """根据方向分割图像"""
    split_imgs = []
    if direction == '多宫格':
        try:
            grid_row = int(grid_row_entry.get())
            grid_col = int(grid_col_entry.get())
            if grid_row < 1 or grid_col < 1:
                raise ValueError
            for img in imgs:
                img_width, img_height = img.size
                cell_width = img_width // grid_col
                cell_height = img_height // grid_row
                for r in range(grid_row):
                    for c in range(grid_col):
                        left = c * cell_width
                        upper = r * cell_height
                        right = left + cell_width
                        lower = upper + cell_height
                        split_img = img.crop((left, upper, right, lower))
                        split_imgs.append(split_img)
        except ValueError:
            set_status("行数和列数必须为大于等于1的整数。", "danger")
            return split_imgs
    elif direction == '垂直':
        try:
            grid_col = int(grid_col_entry.get())
            if grid_col < 1:
                raise ValueError
            for img in imgs:
                img_width, img_height = img.size
                cell_width = img_width // grid_col
                cell_height = img_height
                for c in range(grid_col):
                    left = c * cell_width
                    upper = 0
                    right = left + cell_width
                    lower = img_height
                    split_img = img.crop((left, upper, right, lower))
                    split_imgs.append(split_img)
        except ValueError:
            set_status("列数必须为大于等于1的整数。", "danger")
            return split_imgs
    elif direction == '水平':
        try:
            grid_row = int(grid_row_entry.get())
            if grid_row < 1:
                raise ValueError
            for img in imgs:
                img_width, img_height = img.size
                cell_width = img_width
                cell_height = img_height // grid_row
                for r in range(grid_row):
                    left = 0
                    upper = r * cell_height
                    right = img_width
                    lower = upper + cell_height
                    split_img = img.crop((left, upper, right, lower))
                    split_imgs.append(split_img)
        except ValueError:
            set_status("行数必须为大于等于1的整数。", "danger")
            return split_imgs
    elif direction == '不分割':
        split_imgs.extend(imgs)
    return split_imgs

def convert_image_mode(img, extension):
    """根据文件扩展名转换图像模式"""
    if extension.lower() in ['.jpg', '.jpeg', '.bmp', '.webp', '.heic']:
        return img.convert("RGB")
    elif extension.lower() == '.png':
        return img.convert("RGBA")
    elif extension.lower() == '.heic':
        return img.convert("RGB")  # HEIC 格式需要 RGB 模式
    return img

def save_images(imgs, extension):
    """保存分割后的图像"""
    selected_dpi = dpi_var.get()
    for i, img in enumerate(imgs):
        save_path = os.path.splitext(file_path)[0] + f"_part{i+1}" + extension

        if selected_dpi != "默认":
            try:
                dpi = int(selected_dpi)
            except ValueError:
                set_status("DPI必须为整数或'默认'。", "danger")
                continue
            original_dpi = img.info.get('dpi', (300, 300))  # 默认假设原始 DPI 为 300
            scaling_factor = dpi / original_dpi[0]  # 计算缩放比例
            new_width = int(img.width * scaling_factor)
            new_height = int(img.height * scaling_factor)
            img = img.resize((new_width, new_height), resample=Image.LANCZOS)
            img = convert_image_mode(img, extension)  # 转换图像模式
            if extension.lower() in ['.pdf']:
                img.save(save_path, dpi=(dpi, dpi))  # 保存 PDF 时设置 DPI
            elif extension.lower() == '.heic':
                # 保存 HEIC 格式
                pillow_heif.from_pillow(img).save(save_path)
            else:
                img.save(save_path, dpi=(dpi, dpi))  # 保存其他格式时设置 DPI
        else:
            # 如果 DPI 为默认，直接保存图像
            img = convert_image_mode(img, extension)  # 转换图像模式
            if extension.lower() == '.heic':
                # 保存 HEIC 格式
                pillow_heif.from_pillow(img).save(save_path)
            else:
                img.save(save_path)  # 保存其他格式
    set_status(f"图像保存成功，共 {len(imgs)} 个部分。", "success")

def save_file():
    """保存"""
    if not file_path:
        set_status("错误: 没有选择文件。", "danger")
        return
    save_extension = save_format_var.get()
    direction = split_direction_var.get()
    grid_row = grid_row_entry.get()
    grid_col = grid_col_entry.get()
    if direction == '多宫格':
        try:
            grid_row = int(grid_row)
            grid_col = int(grid_col)
            if grid_row < 1 or grid_col < 1:
                raise ValueError
        except ValueError:
            set_status("行数和列数必须为大于等于1的整数。", "danger")
            return
    elif direction == '垂直':
        try:
            grid_col = int(grid_col)
            if grid_col < 1:
                raise ValueError
        except ValueError:
            set_status("列数必须为大于等于1的整数。", "danger")
            return
    elif direction == '水平':
        try:
            grid_row = int(grid_row)
            if grid_row < 1:
                raise ValueError
        except ValueError:
            set_status("行数必须为大于等于1的整数。", "danger")
            return
    imgs_to_save = split_image(imgs, direction, grid_row, grid_col)
    save_images(imgs_to_save, save_extension)

def load_file_in_background(file_path, file_extension):
    """后台加载文件"""
    global imgs, total_pages, current_page
    set_status("正在加载文件，请稍候...", "info")
    try:
        imgs = get_original_image(file_path, file_extension)
        total_pages = len(imgs)
        page_spinbox.config(from_=1, to=total_pages)
        page_spinbox.state(['!disabled'])
        current_page = 1
        page_var.set(current_page)
        root.after(0, display_image)
        set_status(f"文件加载完成: {file_path}, 共 {total_pages} 页", "success")
    except Exception as e:
        set_status(f"文件加载失败: {str(e)}", "danger")

def open_file():
    """打开文件"""
    global file_path, file_extension
    file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.pdf;*.jpg;*.jpeg;*.png;*.bmp;*.webp;*.heic")])
    if file_path:
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic']:
            threading.Thread(target=load_file_in_background, args=(file_path, file_extension), daemon=True).start()
        else:
            set_status(f"不支持的文件类型: {file_extension}", "danger")
    else:
        set_status("未选择文件。", "warning")

def update_current_page():
    """更新当前页面"""
    global current_page
    current_page = int(page_var.get())
    display_image()
    set_status(f"当前页面: {current_page}/{total_pages}", "info")

def display_image():
    global img_display_x, img_display_y, img_display_width, img_display_height, zoom_scale, img_offset_x, img_offset_y
    image_canvas.delete("image")
    if imgs:
        canvas_width = image_canvas.winfo_width()
        canvas_height = image_canvas.winfo_height()
        img_to_display = imgs[current_page - 1]
        img_width, img_height = img_to_display.size
        if img_width / img_height > canvas_width / canvas_height:
            new_width = canvas_width * zoom_scale
            new_height = int(new_width * img_height / img_width)
        else:
            new_height = canvas_height * zoom_scale
            new_width = int(new_height * img_width / img_height)
        resized_img = img_to_display.resize((int(new_width), int(new_height)))
        photo = ImageTk.PhotoImage(resized_img)
        img_display_x = (canvas_width - new_width) / 2 + img_offset_x
        img_display_y = (canvas_height - new_height) / 2 + img_offset_y
        img_display_width = new_width
        img_display_height = new_height
        image_canvas.create_image(img_display_x, img_display_y, anchor='nw', image=photo, tags="image")
        image_canvas.image = photo
        draw_split_line()

def draw_split_line():
    image_canvas.delete("split_line")
    if imgs:
        direction = split_direction_var.get()
        selected_color = split_color_var.get()
        color = color_mapping.get(selected_color, 'red')
        if direction == '多宫格':
            try:
                grid_row = int(grid_row_entry.get())
                grid_col = int(grid_col_entry.get())
                if grid_row < 1 or grid_col < 1:
                    raise ValueError
                cell_width = img_display_width / grid_col
                cell_height = img_display_height / grid_row
                for i in range(1, grid_col):
                    split_x = img_display_x + cell_width * i
                    image_canvas.create_line(split_x, img_display_y, split_x, img_display_y + img_display_height, fill=color, width=2, tags="split_line")
                for j in range(1, grid_row):
                    split_y = img_display_y + cell_height * j
                    image_canvas.create_line(img_display_x, split_y, img_display_x + img_display_width, split_y, fill=color, width=2, tags="split_line")
            except ValueError:
                pass
        elif direction == '垂直':
            try:
                grid_col = int(grid_col_entry.get())
                if grid_col < 1:
                    raise ValueError
                cell_width = img_display_width / grid_col
                for i in range(1, grid_col):
                    split_x = img_display_x + cell_width * i
                    image_canvas.create_line(split_x, img_display_y, split_x, img_display_y + img_display_height, fill=color, width=2, tags="split_line")
            except ValueError:
                pass
        elif direction == '水平':
            try:
                grid_row = int(grid_row_entry.get())
                if grid_row < 1:
                    raise ValueError
                cell_height = img_display_height / grid_row
                for j in range(1, grid_row):
                    split_y = img_display_y + cell_height * j
                    image_canvas.create_line(img_display_x, split_y, img_display_x + img_display_width, split_y, fill=color, width=2, tags="split_line")
            except ValueError:
                pass
        elif direction == '不分割':
            pass

def set_status(message, color="secondary"):
    """设置状态栏信息"""
    status_label.config(text=message, bootstyle=color)
    root.after(5000, lambda: status_label.config(text="", bootstyle="secondary"))

def update_split_direction(*args):
    """更新分割方向"""
    global image_canvas, grid_row_entry, grid_col_entry
    direction = split_direction_var.get()
    if direction == '垂直':
        grid_row_entry.delete(0, tk.END)
        grid_row_entry.insert(0, "1")
        grid_row_entry['state'] = 'disabled'
        grid_col_entry.delete(0, tk.END)
        grid_col_entry.insert(0, "2")
        grid_col_entry['state'] = 'normal'
    elif direction == '水平':
        grid_row_entry.delete(0, tk.END)
        grid_row_entry.insert(0, "2")
        grid_row_entry['state'] = 'normal'
        grid_col_entry.delete(0, tk.END)
        grid_col_entry.insert(0, "1")
        grid_col_entry['state'] = 'disabled'
    elif direction == '多宫格':
        grid_row_entry.delete(0, tk.END)
        grid_row_entry.insert(0, "3")
        grid_row_entry['state'] = 'normal'
        grid_col_entry.delete(0, tk.END)
        grid_col_entry.insert(0, "3")
        grid_col_entry['state'] = 'normal'
    else:
        grid_row_entry['state'] = 'disabled'
        grid_col_entry['state'] = 'disabled'
    draw_split_line()

def drag_split_line(event):
    global split_position
    direction = split_direction_var.get()
    if direction not in ['垂直', '水平']:
        return
    if direction == '垂直':
        split_position = max(0, min(1, (event.x - img_display_x) / img_display_width))
    elif direction == '水平':
        split_position = max(0, min(1, (event.y - img_display_y) / img_display_height))
    draw_split_line()
    set_status(f"分割位置已调整为: {int(split_position * 100)}%", "info")

def on_drop(event):
    """处理拖放文件"""
    global file_path, file_extension
    file_path = event.data.strip('{}')
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic']:
        threading.Thread(target=load_file_in_background, args=(file_path, file_extension), daemon=True).start()
    else:
        set_status(f"不支持的文件类型: {file_extension}", "danger")

def update_grid_lines(event):
    """当宫格数量变化时，更新分割线"""
    try:
        grid_row = int(grid_row_entry.get())
        grid_col = int(grid_col_entry.get())
        if grid_row < 1 or grid_col < 1:
            raise ValueError
        draw_split_line()
    except ValueError:
        set_status("行数和列数必须为大于等于1的整数。", "danger")

def get_original_image(file_path, file_extension):
    """加载原始图像或 PDF 页面"""
    if file_extension == '.heic':
        # 使用 pillow-heif 读取 HEIC 文件
        heif_file = pillow_heif.read_heif(file_path)
        img = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        return [img.convert("RGB")]
    elif file_extension == '.pdf':
        doc = fitz.open(file_path)
        images = []
        # 获取当前选择的DPI，如果没有选择则使用默认DPI
        selected_dpi = dpi_var.get()
        if selected_dpi == "默认":
            dpi_value = 300  # 默认DPI
        else:
            dpi_value = int(selected_dpi)
        for page in doc:
            pix = page.get_pixmap(dpi=dpi_value, alpha=True)
            img_rgba = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            img_white = Image.new("RGB", img_rgba.size, (255, 255, 255))
            img_rgb = Image.alpha_composite(img_white.convert("RGBA"), img_rgba).convert('RGB')
            images.append(img_rgb)
        return images
    else:
        return [Image.open(file_path).convert("RGB")]

def open_update_link():
    """打开更新链接"""
    webbrowser.open("https://github.com/Qwejay/ImageSplitter")

def rotate_image():
    """旋转当前页面图像 90 度"""
    global imgs, current_page
    if imgs:
        imgs[current_page - 1] = imgs[current_page - 1].rotate(90, expand=True)
        display_image()
        set_status("图像已旋转 90 度。", "info")

def horizontal_flip():
    """水平翻转当前页面图像"""
    global imgs, current_page
    if imgs:
        imgs[current_page - 1] = imgs[current_page - 1].transpose(Image.FLIP_LEFT_RIGHT)
        display_image()
        set_status("图像已水平翻转。", "info")

def vertical_flip():
    """垂直翻转当前页面图像"""
    global imgs, current_page
    if imgs:
        imgs[current_page - 1] = imgs[current_page - 1].transpose(Image.FLIP_TOP_BOTTOM)
        display_image()
        set_status("图像已垂直翻转。", "info")

def start_drag(event):
    global is_dragging, drag_start_x, drag_start_y
    is_dragging = True
    drag_start_x = event.x
    drag_start_y = event.y

def stop_drag(event):
    global is_dragging
    is_dragging = False

def on_drag(event):
    global img_offset_x, img_offset_y, drag_start_x, drag_start_y
    if is_dragging:
        # 计算鼠标移动的距离
        dx = event.x - drag_start_x
        dy = event.y - drag_start_y
        # 更新图像偏移量
        img_offset_x += dx
        img_offset_y += dy
        # 更新拖动起始位置
        drag_start_x = event.x
        drag_start_y = event.y
        # 重新显示图像
        display_image()

def zoom_in(event=None):
    global zoom_scale, img_offset_x, img_offset_y
    if event:
        # 获取鼠标指针在画布上的位置
        mouse_x = event.x
        mouse_y = event.y
        # 计算缩放中心相对于图像中心的偏移量
        center_x = img_display_x + img_display_width / 2
        center_y = img_display_y + img_display_height / 2
        offset_x = (mouse_x - center_x) * (1.1 - 1)
        offset_y = (mouse_y - center_y) * (1.1 - 1)
        img_offset_x -= offset_x
        img_offset_y -= offset_y
    zoom_scale *= 1.1
    display_image()

def zoom_out(event=None):
    global zoom_scale, img_offset_x, img_offset_y
    if event:
        # 获取鼠标指针在画布上的位置
        mouse_x = event.x
        mouse_y = event.y
        # 计算缩放中心相对于图像中心的偏移量
        center_x = img_display_x + img_display_width / 2
        center_y = img_display_y + img_display_height / 2
        offset_x = (mouse_x - center_x) * (1 / 1.1 - 1)
        offset_y = (mouse_y - center_y) * (1 / 1.1 - 1)
        img_offset_x -= offset_x
        img_offset_y -= offset_y
    zoom_scale /= 1.1
    display_image()

def reset_zoom():
    global zoom_scale, img_offset_x, img_offset_y
    zoom_scale = 1.0
    img_offset_x = 0
    img_offset_y = 0
    display_image()

# 创建主窗口
root = TkinterDnD.Tk()
root.geometry("880x680")
root.title("Image Splitter 2.1 —— QwejayHuang")

# 设置窗口图标
root.iconbitmap('icon.ico')

# 初始化 ttkbootstrap 样式
style = ttk.Style("litera")

# 创建顶部菜单
top_menu = ttk.Frame(root)
top_menu.pack(fill=X, padx=10, pady=5)

open_button = ttk.Button(top_menu, text="打开文件", command=open_file, bootstyle="primary")
open_button.pack(side=LEFT, padx=10, pady=5)

split_direction_var = tk.StringVar()
split_direction_var.set('不分割')

direction_menu_label = ttk.Label(top_menu, text="分割类型:", bootstyle="secondary")
direction_menu_label.pack(side=LEFT, padx=5)
direction_menu = ttk.OptionMenu(top_menu, split_direction_var, '不分割', '不分割', '垂直', '水平', '多宫格')
direction_menu.pack(side=LEFT, padx=10, pady=5)

split_direction_var.trace('w', update_split_direction)

vcmd = (root.register(lambda value: value.isdigit() or value == ""), '%P')
grid_row_entry_label = ttk.Label(top_menu, text="行数:", bootstyle="secondary")
grid_row_entry_label.pack(side=LEFT, padx=5)
grid_row_entry = ttk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_row_entry.pack(side=LEFT, padx=5)
grid_row_entry.insert(0, "3")
grid_row_entry['state'] = 'disabled'  # 默认不分割，行输入框变灰色

grid_col_entry_label = ttk.Label(top_menu, text="列数:", bootstyle="secondary")
grid_col_entry_label.pack(side=LEFT, padx=5)
grid_col_entry = ttk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_col_entry.pack(side=LEFT, padx=5)
grid_col_entry.insert(0, "3")
grid_col_entry['state'] = 'disabled'  # 默认不分割，列输入框变灰色

# 创建dpi变量
dpi_var = tk.StringVar()
dpi_var.set("默认")

# 创建dpi标签
dpi_label = ttk.Label(top_menu, text="保存DPI:", bootstyle="secondary")
dpi_label.pack(side=LEFT, padx=5)

# 创建Combobox
dpi_combobox = ttk.Combobox(top_menu, textvariable=dpi_var, values=["默认", "72", "150", "300"], width=5)
dpi_combobox.pack(side=LEFT, padx=10, pady=5)
dpi_combobox.bind("<<ComboboxSelected>>", lambda event: set_status(f"DPI设置为: {dpi_var.get()}", "info"))
dpi_combobox.bind("<FocusOut>", lambda event: set_status(f"DPI设置为: {dpi_var.get()}", "info"))

save_format_var = tk.StringVar()
save_format_var.set('.jpg')
save_format_label = ttk.Label(top_menu, text="保存格式:", bootstyle="secondary")
save_format_label.pack(side=LEFT, padx=5)
save_format_menu = ttk.OptionMenu(top_menu, save_format_var, '.JPG', '.JPG', '.PDF', '.PNG', '.BMP', '.WEBP', '.HEIC')
save_format_menu.pack(side=LEFT, padx=10, pady=5)

save_button = ttk.Button(top_menu, text="保存文件", command=save_file, bootstyle="primary")
save_button.pack(side=LEFT, padx=10, pady=5)

# 创建预览区域
preview_frame = ttk.Frame(root)
preview_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

image_canvas = ttk.Canvas(preview_frame, background="#e0e0e0")
image_canvas.pack(fill=BOTH, expand=True)

# 绑定拖动事件
image_canvas.bind("<B1-Motion>", on_drag)

# 绑定窗口大小变化事件
def on_resize(event):
    display_image()

image_canvas.bind("<Configure>", on_resize)

# 创建按钮框架
button_frame = ttk.Frame(preview_frame)
button_frame.pack(fill=X, pady=5)

button_frame.grid_columnconfigure(0, weight=1)
button_frame.grid_columnconfigure(1, weight=0)
button_frame.grid_columnconfigure(2, weight=1)

page_control_frame = ttk.Frame(button_frame)
page_control_frame.grid(row=0, column=1, padx=5, sticky='nsew')

page_label = ttk.Label(page_control_frame, text="当前页面：", bootstyle="secondary")
page_label.pack(side=LEFT, padx=5)

page_var = tk.StringVar()
page_var.set("1")
page_spinbox = ttk.Spinbox(page_control_frame, from_=1, to=1, textvariable=page_var, width=5)
page_spinbox.pack(side=LEFT, padx=5)
page_var.trace_add('write', lambda *args: update_current_page())

button_inner_frame = ttk.Frame(button_frame)
button_inner_frame.grid(row=0, column=2, padx=5, sticky='e')

# 新增颜色选择器
split_color_var = tk.StringVar()
split_color_var.set('红色')  # 默认颜色
split_color_var.trace('w', lambda *args: draw_split_line())  # 绑定变量变化事件

# 添加标签
color_label = ttk.Label(button_inner_frame, text="分割线颜色：", bootstyle="secondary")
color_label.pack(side=LEFT, padx=5)

color_options = ['红色', '蓝色', '绿色', '黑色', '黄色']
color_menu = ttk.OptionMenu(button_inner_frame, split_color_var, '红色', *color_options)
color_menu.pack(side=LEFT, padx=5)

rotate_button = ttk.Button(button_inner_frame, text="旋转", command=lambda: rotate_image(), bootstyle="secondary")
rotate_button.pack(side=LEFT, padx=5)

horizontal_flip_button = ttk.Button(button_inner_frame, text="水平镜像", command=lambda: horizontal_flip(), bootstyle="secondary")
horizontal_flip_button.pack(side=LEFT, padx=5)

vertical_flip_button = ttk.Button(button_inner_frame, text="垂直镜像", command=lambda: vertical_flip(), bootstyle="secondary")
vertical_flip_button.pack(side=LEFT, padx=5)

# 添加缩放按钮
zoom_in_button = ttk.Button(button_inner_frame, text="放大", command=zoom_in, bootstyle="secondary")
zoom_in_button.pack(side=LEFT, padx=5)

zoom_out_button = ttk.Button(button_inner_frame, text="缩小", command=zoom_out, bootstyle="secondary")
zoom_out_button.pack(side=LEFT, padx=5)

reset_zoom_button = ttk.Button(button_inner_frame, text="重置", command=reset_zoom, bootstyle="secondary")
reset_zoom_button.pack(side=LEFT, padx=5)

# 绑定鼠标事件
image_canvas.bind("<ButtonPress-1>", start_drag)
image_canvas.bind("<ButtonRelease-1>", stop_drag)
image_canvas.bind("<B1-Motion>", on_drag)
image_canvas.bind("<MouseWheel>", lambda event: zoom_in(event) if event.delta > 0 else zoom_out(event))  # 鼠标滚轮缩放

# 状态栏
status_bar = ttk.Frame(root, relief='sunken', borderwidth=1)
status_bar.pack(side=BOTTOM, fill=X)

status_label = ttk.Label(status_bar, text="", bootstyle="secondary", anchor='w', padding=(5, 0))
status_label.pack(side=LEFT, fill=X, expand=True)

update_link = ttk.Label(status_bar, text="检查更新", cursor="hand2", foreground="blue")
update_link.pack(side=RIGHT, padx=5)
update_link.bind("<Button-1>", lambda e: open_update_link())

# 绑定拖放事件
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', on_drop)

# 绑定行数和列数输入框的值变化事件
grid_row_entry.bind('<KeyRelease>', update_grid_lines)
grid_col_entry.bind('<KeyRelease>', update_grid_lines)

# 启动主循环
root.mainloop()