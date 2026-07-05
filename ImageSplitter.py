import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import threading
import webbrowser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pillow_heif
import sys

# 尝试导入 tkinterdnd2，失败则降级
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DROP_SUPPORTED = True
except ImportError:
    DROP_SUPPORTED = False
    print("Warning: tkinterdnd2 not installed. Drag-and-drop disabled.")

__app_name__ = "ImageSplitter"
__version__ = "2.1"
__author__ = "QwejayHuang"
__company__ = "QwejayHuang"
__description__ = "图片与 PDF 自动裁剪及分割工具"

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
last_mouse_x = 0
last_mouse_y = 0
auto_fit_on_load = True  # 首次加载或换页时自动适应窗口
zoom_display_label = None  # 缩放比例显示标签

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
    global imgs, total_pages, current_page, auto_fit_on_load
    set_status("正在加载文件，请稍候...", "info")
    try:
        imgs = get_original_image(file_path, file_extension)
        total_pages = len(imgs)
        page_spinbox.config(from_=1, to=total_pages)
        page_spinbox.state(['!disabled'])
        current_page = 1
        page_var.set(current_page)
        auto_fit_on_load = True  # 关键：加载完成自动适应
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
    global current_page, auto_fit_on_load
    current_page = int(page_var.get())
    auto_fit_on_load = True  # 切换页面时重新适应窗口
    display_image()
    set_status(f"当前页面: {current_page}/{total_pages}", "info")

def display_image():
    global img_display_x, img_display_y, img_display_width, img_display_height, zoom_scale, auto_fit_on_load, img_offset_x, img_offset_y
    
    image_canvas.delete("image")
    if not imgs:
        return
        
    canvas_width = image_canvas.winfo_width()
    canvas_height = image_canvas.winfo_height()
    
    if canvas_width <= 1 or canvas_height <= 1:
        return
        
    img_to_display = imgs[current_page - 1]
    img_width, img_height = img_to_display.size
    
    # 👇 自动适应窗口逻辑
    if auto_fit_on_load and img_width > 0 and img_height > 0:
        scale_w = (canvas_width * 0.95) / img_width  # 留5%边距
        scale_h = (canvas_height * 0.95) / img_height
        zoom_scale = min(scale_w, scale_h)
        if zoom_scale < 0.1: zoom_scale = 0.1  # 最小缩放限制
        if zoom_scale > 10: zoom_scale = 10     # 最大缩放限制
        img_offset_x = 0
        img_offset_y = 0
        auto_fit_on_load = False  # 只触发一次
    
    # 计算缩放后的尺寸
    scaled_width = img_width * zoom_scale
    scaled_height = img_height * zoom_scale
    
    # 确保图像至少显示一部分
    if scaled_width < 10:
        scaled_width = 10
    if scaled_height < 10:
        scaled_height = 10
    
    # 创建缩放后的图像
    try:
        resized_img = img_to_display.resize((int(scaled_width), int(scaled_height)), Image.LANCZOS)
        photo = ImageTk.PhotoImage(resized_img)
        
        # 设置图像位置（考虑偏移量）
        img_display_x = canvas_width / 2 - scaled_width / 2 + img_offset_x
        img_display_y = canvas_height / 2 - scaled_height / 2 + img_offset_y
        img_display_width = scaled_width
        img_display_height = scaled_height
        
        # 显示图像
        image_canvas.create_image(img_display_x, img_display_y, anchor='nw', image=photo, tags="image")
        image_canvas.image = photo  # 保持引用防止被垃圾回收
        
        # 更新缩放比例显示
        update_zoom_display()
        
        # 绘制分割线
        draw_split_line()
        
    except Exception as e:
        set_status(f"图像显示错误: {str(e)}", "danger")

def draw_split_line():
    image_canvas.delete("split_line")
    if not imgs:
        return
        
    direction = split_direction_var.get()
    selected_color = split_color_var.get()
    color = color_mapping.get(selected_color, 'red')
    
    if direction == '多宫格':
        try:
            grid_row = int(grid_row_entry.get())
            grid_col = int(grid_col_entry.get())
            if grid_row < 1 or grid_col < 1:
                raise ValueError
                
            if img_display_width > 0 and img_display_height > 0:
                cell_width = img_display_width / grid_col
                cell_height = img_display_height / grid_row
                
                for i in range(1, grid_col):
                    split_x = img_display_x + cell_width * i
                    image_canvas.create_line(
                        split_x, img_display_y, 
                        split_x, img_display_y + img_display_height, 
                        fill=color, width=2, tags="split_line"
                    )
                    
                for j in range(1, grid_row):
                    split_y = img_display_y + cell_height * j
                    image_canvas.create_line(
                        img_display_x, split_y, 
                        img_display_x + img_display_width, split_y, 
                        fill=color, width=2, tags="split_line"
                    )
        except ValueError:
            pass
            
    elif direction == '垂直':
        try:
            grid_col = int(grid_col_entry.get())
            if grid_col < 1:
                raise ValueError
                
            if img_display_width > 0:
                cell_width = img_display_width / grid_col
                for i in range(1, grid_col):
                    split_x = img_display_x + cell_width * i
                    image_canvas.create_line(
                        split_x, img_display_y, 
                        split_x, img_display_y + img_display_height, 
                        fill=color, width=2, tags="split_line"
                    )
        except ValueError:
            pass
            
    elif direction == '水平':
        try:
            grid_row = int(grid_row_entry.get())
            if grid_row < 1:
                raise ValueError
                
            if img_display_height > 0:
                cell_height = img_display_height / grid_row
                for j in range(1, grid_row):
                    split_y = img_display_y + cell_height * j
                    image_canvas.create_line(
                        img_display_x, split_y, 
                        img_display_x + img_display_width, split_y, 
                        fill=color, width=2, tags="split_line"
                    )
        except ValueError:
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
        selected_dpi = dpi_var.get()
        dpi_value = 300 if selected_dpi == "默认" else int(selected_dpi)
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
    global is_dragging, drag_start_x, drag_start_y, last_mouse_x, last_mouse_y
    is_dragging = True
    drag_start_x = event.x
    drag_start_y = event.y
    last_mouse_x = event.x
    last_mouse_y = event.y

def stop_drag(event):
    global is_dragging
    is_dragging = False

def on_drag(event):
    global img_offset_x, img_offset_y, drag_start_x, drag_start_y, last_mouse_x, last_mouse_y
    if is_dragging:
        dx = event.x - drag_start_x
        dy = event.y - drag_start_y
        img_offset_x += dx
        img_offset_y += dy
        drag_start_x = event.x
        drag_start_y = event.y
        last_mouse_x = event.x
        last_mouse_y = event.y
        display_image()

def adjust_offset_for_zoom(old_scale, new_scale, mouse_x, mouse_y):
    """根据鼠标位置调整偏移量以实现精确缩放"""
    global img_offset_x, img_offset_y, img_display_x, img_display_y, img_display_width, img_display_height
    
    if not imgs:
        return
        
    img = imgs[current_page - 1]
    orig_width, orig_height = img.size
    
    old_width = orig_width * old_scale
    old_height = orig_height * old_scale
    new_width = orig_width * new_scale
    new_height = orig_height * new_scale
    
    canvas_width = image_canvas.winfo_width()
    canvas_height = image_canvas.winfo_height()
    canvas_center_x = canvas_width / 2
    canvas_center_y = canvas_height / 2
    
    old_img_x = mouse_x - (canvas_center_x - old_width / 2 + img_offset_x)
    old_img_y = mouse_y - (canvas_center_y - old_height / 2 + img_offset_y)
    
    ratio_x = old_img_x / old_width if old_width > 0 else 0.5
    ratio_y = old_img_y / old_height if old_height > 0 else 0.5
    
    new_img_x = ratio_x * new_width
    new_img_y = ratio_y * new_height
    
    img_offset_x = mouse_x - (canvas_center_x - new_width / 2 + new_img_x)
    img_offset_y = mouse_y - (canvas_center_y - new_height / 2 + new_img_y)

def zoom_in(event=None):
    """放大图像"""
    global zoom_scale, last_mouse_x, last_mouse_y
    
    if not imgs: return
    
    old_scale = zoom_scale
    zoom_scale *= 1.1
    
    if zoom_scale > 10.0:
        zoom_scale = 10.0
        return
    
    if event:
        last_mouse_x = event.x
        last_mouse_y = event.y
        adjust_offset_for_zoom(old_scale, zoom_scale, event.x, event.y)
    
    display_image()

def zoom_out(event=None):
    """缩小图像"""
    global zoom_scale, last_mouse_x, last_mouse_y
    
    if not imgs: return
    
    old_scale = zoom_scale
    zoom_scale /= 1.1
    
    if zoom_scale < 0.1:
        zoom_scale = 0.1
        return
    
    if event:
        last_mouse_x = event.x
        last_mouse_y = event.y
        adjust_offset_for_zoom(old_scale, zoom_scale, event.x, event.y)
    
    display_image()

def reset_zoom():
    """重置为原始尺寸（1:1）"""
    global zoom_scale, img_offset_x, img_offset_y
    zoom_scale = 1.0
    img_offset_x = 0
    img_offset_y = 0
    display_image()
    set_status("缩放已重置为原始尺寸", "info")

def fit_to_window():
    """适应窗口"""
    global auto_fit_on_load
    auto_fit_on_load = True
    display_image()
    set_status("已适应窗口", "info")

def update_zoom_display():
    """更新缩放比例显示"""
    if zoom_display_label:
        percentage = int(zoom_scale * 100)
        zoom_display_label.config(text=f"{percentage}%")

# 创建主窗口
if DROP_SUPPORTED:
    root = TkinterDnD.Tk()
else:
    root = tk.Tk()  # 降级使用普通 Tk

root.geometry("880x680")
root.title(f"{__app_name__} {__version__} —— {__author__}")

# 设置窗口图标（忽略错误）
try:
    root.iconbitmap('icon.ico')
except:
    pass

# 初始化 ttkbootstrap 样式
style = ttk.Style("litera")

# 创建顶部菜单
top_menu = ttk.Frame(root)
top_menu.pack(fill=tk.X, padx=10, pady=5)

open_button = ttk.Button(top_menu, text="打开文件", command=open_file, bootstyle="primary")
open_button.pack(side=tk.LEFT, padx=10, pady=5)

split_direction_var = tk.StringVar(value='不分割')

direction_menu_label = ttk.Label(top_menu, text="分割类型:", bootstyle="secondary")
direction_menu_label.pack(side=tk.LEFT, padx=5)
direction_menu = ttk.OptionMenu(top_menu, split_direction_var, '不分割', '不分割', '垂直', '水平', '多宫格')
direction_menu.pack(side=tk.LEFT, padx=10, pady=5)

split_direction_var.trace('w', update_split_direction)

vcmd = (root.register(lambda value: value.isdigit() or value == ""), '%P')
grid_row_entry_label = ttk.Label(top_menu, text="行数:", bootstyle="secondary")
grid_row_entry_label.pack(side=tk.LEFT, padx=5)
grid_row_entry = ttk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_row_entry.pack(side=tk.LEFT, padx=5)
grid_row_entry.insert(0, "3")
grid_row_entry['state'] = 'disabled'

grid_col_entry_label = ttk.Label(top_menu, text="列数:", bootstyle="secondary")
grid_col_entry_label.pack(side=tk.LEFT, padx=5)
grid_col_entry = ttk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_col_entry.pack(side=tk.LEFT, padx=5)
grid_col_entry.insert(0, "3")
grid_col_entry['state'] = 'disabled'

dpi_var = tk.StringVar(value="默认")
dpi_label = ttk.Label(top_menu, text="保存DPI:", bootstyle="secondary")
dpi_label.pack(side=tk.LEFT, padx=5)
dpi_combobox = ttk.Combobox(top_menu, textvariable=dpi_var, values=["默认", "72", "150", "300"], width=5)
dpi_combobox.pack(side=tk.LEFT, padx=10, pady=5)
dpi_combobox.bind("<<ComboboxSelected>>", lambda event: set_status(f"DPI设置为: {dpi_var.get()}", "info"))
dpi_combobox.bind("<FocusOut>", lambda event: set_status(f"DPI设置为: {dpi_var.get()}", "info"))

save_format_var = tk.StringVar(value='.jpg')
save_format_label = ttk.Label(top_menu, text="保存格式:", bootstyle="secondary")
save_format_label.pack(side=tk.LEFT, padx=5)
save_format_menu = ttk.OptionMenu(top_menu, save_format_var, '.JPG', '.JPG', '.PDF', '.PNG', '.BMP', '.WEBP', '.HEIC')
save_format_menu.pack(side=tk.LEFT, padx=10, pady=5)

save_button = ttk.Button(top_menu, text="保存文件", command=save_file, bootstyle="primary")
save_button.pack(side=tk.LEFT, padx=10, pady=5)

# 创建预览区域
preview_frame = ttk.Frame(root)
preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

image_canvas = ttk.Canvas(preview_frame, background="#e0e0e0")
image_canvas.pack(fill=tk.BOTH, expand=True)

# 创建按钮框架
button_frame = ttk.Frame(preview_frame)
button_frame.pack(fill=tk.X, pady=5)

button_frame.grid_columnconfigure(0, weight=1)
button_frame.grid_columnconfigure(1, weight=0)
button_frame.grid_columnconfigure(2, weight=1)

page_control_frame = ttk.Frame(button_frame)
page_control_frame.grid(row=0, column=1, padx=5, sticky='nsew')

page_label = ttk.Label(page_control_frame, text="当前页面：", bootstyle="secondary")
page_label.pack(side=tk.LEFT, padx=5)

page_var = tk.StringVar(value="1")
page_spinbox = ttk.Spinbox(page_control_frame, from_=1, to=1, textvariable=page_var, width=5)
page_spinbox.pack(side=tk.LEFT, padx=5)
page_var.trace_add('write', lambda *args: update_current_page())

button_inner_frame = ttk.Frame(button_frame)
button_inner_frame.grid(row=0, column=2, padx=5, sticky='e')

split_color_var = tk.StringVar(value='红色')
split_color_var.trace('w', lambda *args: draw_split_line())

color_label = ttk.Label(button_inner_frame, text="分割线颜色：", bootstyle="secondary")
color_label.pack(side=tk.LEFT, padx=5)

color_options = ['红色', '蓝色', '绿色', '黑色', '黄色']
color_menu = ttk.OptionMenu(button_inner_frame, split_color_var, '红色', *color_options)
color_menu.pack(side=tk.LEFT, padx=5)

rotate_button = ttk.Button(button_inner_frame, text="旋转", command=rotate_image, bootstyle="secondary")
rotate_button.pack(side=tk.LEFT, padx=5)

horizontal_flip_button = ttk.Button(button_inner_frame, text="水平镜像", command=horizontal_flip, bootstyle="secondary")
horizontal_flip_button.pack(side=tk.LEFT, padx=5)

vertical_flip_button = ttk.Button(button_inner_frame, text="垂直镜像", command=vertical_flip, bootstyle="secondary")
vertical_flip_button.pack(side=tk.LEFT, padx=5)

# 缩放控制区
zoom_frame = ttk.Frame(button_inner_frame)
zoom_frame.pack(side=tk.LEFT, padx=5)

zoom_in_button = ttk.Button(zoom_frame, text="放大", command=zoom_in, bootstyle="secondary")
zoom_in_button.pack(side=tk.LEFT, padx=2)

zoom_out_button = ttk.Button(zoom_frame, text="缩小", command=zoom_out, bootstyle="secondary")
zoom_out_button.pack(side=tk.LEFT, padx=2)

reset_zoom_button = ttk.Button(zoom_frame, text="重置", command=reset_zoom, bootstyle="secondary")
reset_zoom_button.pack(side=tk.LEFT, padx=2)

fit_window_button = ttk.Button(zoom_frame, text="适应", command=fit_to_window, bootstyle="secondary")
fit_window_button.pack(side=tk.LEFT, padx=2)

zoom_display_label = ttk.Label(zoom_frame, text="100%", bootstyle="secondary", width=6)
zoom_display_label.pack(side=tk.LEFT, padx=5)

# 绑定鼠标事件
image_canvas.bind("<ButtonPress-1>", start_drag)
image_canvas.bind("<ButtonRelease-1>", stop_drag)
image_canvas.bind("<B1-Motion>", on_drag)
image_canvas.bind("<MouseWheel>", lambda event: zoom_in(event) if event.delta > 0 else zoom_out(event))  # Windows
image_canvas.bind("<Button-4>", lambda event: zoom_in(event))  # Linux
image_canvas.bind("<Button-5>", lambda event: zoom_out(event))  # Linux

# 绑定窗口大小变化事件（防抖）
def on_resize(event):
    global window_resize_id
    if window_resize_id:
        root.after_cancel(window_resize_id)
    window_resize_id = root.after(100, display_image)

image_canvas.bind("<Configure>", on_resize)

# 状态栏
status_bar = ttk.Frame(root, relief='sunken', borderwidth=1)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

status_label = ttk.Label(status_bar, text="", bootstyle="secondary", anchor='w', padding=(5, 0))
status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

update_link = ttk.Label(status_bar, text="检查更新", cursor="hand2", foreground="blue")
update_link.pack(side=tk.RIGHT, padx=5)
update_link.bind("<Button-1>", lambda e: open_update_link())

# 绑定拖放事件（如果支持）
if DROP_SUPPORTED:
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>', on_drop)

# 绑定行数和列数输入框的值变化事件
grid_row_entry.bind('<KeyRelease>', update_grid_lines)
grid_col_entry.bind('<KeyRelease>', update_grid_lines)

# 启动主循环
root.mainloop()
