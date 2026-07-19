import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import fitz
import os
import threading
import webbrowser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pillow_heif
import sys

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DROP_SUPPORTED = True
except ImportError:
    DROP_SUPPORTED = False

__app_name__ = "ImageSplitter"
__version__ = "2.6"
__author__ = "QwejayHuang"
__company__ = "QwejayHuang"
__description__ = "图片与 PDF 自动裁剪及分割工具"

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
zoom_scale = 1.0
img_offset_x = 0
img_offset_y = 0
is_dragging = False
drag_start_x = 0
drag_start_y = 0
last_mouse_x = 0
last_mouse_y = 0
auto_fit_on_load = True
zoom_display_label = None
is_rendering = False
pending_render = False

DEFAULT_STATUS_MSG = "就绪 - 支持文件拖拽 | 鼠标滚轮缩放 | 拖拽平移"
status_timer_id = None

last_canvas_width = 0
last_canvas_height = 0

color_mapping = {
    '红色': 'red',
    '蓝色': 'blue',
    '绿色': 'green',
    '黑色': 'black',
    '黄色': 'yellow'
}

def parse_page_range(range_str, total_pages):
    pages = set()
    for part in range_str.split(','):
        part = part.strip()
        if not part: continue
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                start = max(1, start)
                end = min(total_pages, end)
                if start <= end:
                    pages.update(range(start - 1, end))
            except ValueError:
                pass
        else:
            try:
                val = int(part)
                if 1 <= val <= total_pages:
                    pages.add(val - 1)
            except ValueError:
                pass
    return sorted(list(pages))

def split_image(imgs, direction, grid_row=1, grid_col=1):
    split_imgs = []
    if direction == '多宫格':
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
                    split_imgs.append(img.crop((left, upper, right, lower)))
    elif direction == '垂直':
        for img in imgs:
            img_width, img_height = img.size
            cell_width = img_width // grid_col
            for c in range(grid_col):
                left = c * cell_width
                right = left + cell_width
                split_imgs.append(img.crop((left, 0, right, img_height)))
    elif direction == '水平':
        for img in imgs:
            img_width, img_height = img.size
            cell_height = img_height // grid_row
            for r in range(grid_row):
                upper = r * cell_height
                lower = upper + cell_height
                split_imgs.append(img.crop((0, upper, img_width, lower)))
    elif direction == '不分割':
        split_imgs.extend(imgs)
    return split_imgs

def convert_image_mode(img, extension):
    ext = extension.lower()
    if ext in ['.jpg', '.jpeg', '.bmp', '.webp', '.heic']:
        return img.convert("RGB")
    elif ext == '.png':
        return img.convert("RGBA")
    return img

def save_images(imgs, extension, selected_dpi):
    for i, img in enumerate(imgs):
        save_path = os.path.splitext(file_path)[0] + f"_part{i+1}" + extension

        if selected_dpi != "默认":
            try:
                dpi = int(selected_dpi)
            except ValueError:
                set_status("DPI必须为整数或'默认'。", "danger")
                continue
            
            orig_dpi = img.info.get('dpi')
            if isinstance(orig_dpi, (tuple, list)) and len(orig_dpi) >= 2 and isinstance(orig_dpi[0], (int, float)) and orig_dpi[0] > 0:
                original_dpi = orig_dpi
            else:
                original_dpi = (300, 300)
                
            scaling_factor = dpi / original_dpi[0]
            new_width = int(img.width * scaling_factor)
            new_height = int(img.height * scaling_factor)
            img = img.resize((new_width, new_height), resample=Image.LANCZOS)
            img = convert_image_mode(img, extension)
            if extension.lower() in ['.pdf']:
                img.save(save_path, dpi=(dpi, dpi))
            elif extension.lower() == '.heic':
                pillow_heif.from_pillow(img).save(save_path)
            else:
                img.save(save_path, dpi=(dpi, dpi))
        else:
            img = convert_image_mode(img, extension)
            if extension.lower() == '.heic':
                pillow_heif.from_pillow(img).save(save_path)
            else:
                img.save(save_path)
    set_status(f"图像保存成功，共导出 {len(imgs)} 个部分。", "success")

def save_file():
    if not file_path:
        set_status("错误: 没有选择文件。", "danger")
        return
        
    range_str = save_range_var.get().strip()
    if range_str == "全部" or not range_str:
        selected_indices = list(range(len(imgs)))
    elif range_str == "当前页":
        selected_indices = [current_page - 1]
    else:
        selected_indices = parse_page_range(range_str, len(imgs))
        
    if not selected_indices:
        set_status("错误: 导出的页面范围无效。", "danger")
        return
        
    imgs_to_process = [imgs[i] for i in selected_indices]

    save_extension = save_format_var.get()
    direction = split_direction_var.get()
    selected_dpi = dpi_var.get()
    
    try:
        grid_row = int(grid_row_entry.get()) if direction in ['多宫格', '水平'] else 1
        grid_col = int(grid_col_entry.get()) if direction in ['多宫格', '垂直'] else 1
        if grid_row < 1 or grid_col < 1:
            raise ValueError
    except ValueError:
        set_status("行数和列数必须为大于等于1的整数。", "danger")
        return

    save_button.state(['disabled'])
    set_status("正在后台处理并保存，请稍候...", "info")

    def _save_task():
        try:
            imgs_to_save = split_image(imgs_to_process, direction, grid_row, grid_col)
            save_images(imgs_to_save, save_extension, selected_dpi)
        except Exception as e:
            set_status(f"保存发生错误: {str(e)}", "danger")
        finally:
            root.after(0, lambda: save_button.state(['!disabled']))

    threading.Thread(target=_save_task, daemon=True).start()

def load_file_in_background(target_file_path, target_file_extension):
    set_status("正在加载文件，请稍候...", "info")
    try:
        loaded_imgs = get_original_image(target_file_path, target_file_extension)
        def update_gui():
            global imgs, total_pages, current_page, auto_fit_on_load, file_path, file_extension
            file_path = target_file_path
            file_extension = target_file_extension
            imgs = loaded_imgs
            total_pages = len(imgs)
            page_spinbox.config(from_=1, to=total_pages)
            page_spinbox.state(['!disabled'])
            current_page = 1
            page_var.set(str(current_page))
            auto_fit_on_load = True
            display_image()
            set_status(f"文件加载完成: {target_file_path}, 共 {total_pages} 页", "success")

        root.after(0, update_gui)
    except Exception as e:
        error_msg = str(e)
        root.after(0, lambda: set_status(f"文件加载失败: {error_msg}", "danger"))

def open_file():
    selected_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.pdf;*.jpg;*.jpeg;*.png;*.bmp;*.webp;*.heic")])
    if selected_path:
        ext = os.path.splitext(selected_path)[1].lower()
        if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic']:
            threading.Thread(target=load_file_in_background, args=(selected_path, ext), daemon=True).start()
        else:
            set_status(f"不支持的文件类型: {ext}", "danger")
    else:
        set_status("未选择文件。", "warning")

def update_current_page():
    global current_page, auto_fit_on_load
    val = page_var.get().strip()
    if not val:
        return
    try:
        page_num = int(val)
        if 1 <= page_num <= total_pages:
            current_page = page_num
            auto_fit_on_load = True
            display_image()
            set_status(f"当前页面: {current_page}/{total_pages}", "info")
    except ValueError:
        pass

def schedule_display():
    global is_rendering, pending_render
    if is_rendering:
        pending_render = True
    else:
        is_rendering = True
        root.after(1, _do_display)

def _do_display():
    global is_rendering, pending_render
    try:
        display_image()
    finally:
        is_rendering = False
        if pending_render:
            pending_render = False
            schedule_display()

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
    
    if auto_fit_on_load and img_width > 0 and img_height > 0:
        scale_w = (canvas_width * 0.95) / img_width
        scale_h = (canvas_height * 0.95) / img_height
        zoom_scale = min(scale_w, scale_h)
        if zoom_scale < 0.1: zoom_scale = 0.1
        if zoom_scale > 10: zoom_scale = 10
        img_offset_x = 0
        img_offset_y = 0
        auto_fit_on_load = False
    
    scaled_width = img_width * zoom_scale
    scaled_height = img_height * zoom_scale
    
    if scaled_width < 10:
        scaled_width = 10
    if scaled_height < 10:
        scaled_height = 10
    
    try:
        resized_img = img_to_display.resize((int(scaled_width), int(scaled_height)), Image.BILINEAR)
        photo = ImageTk.PhotoImage(resized_img)
        
        img_display_x = canvas_width / 2 - scaled_width / 2 + img_offset_x
        img_display_y = canvas_height / 2 - scaled_height / 2 + img_offset_y
        img_display_width = scaled_width
        img_display_height = scaled_height
        
        image_canvas.create_image(img_display_x, img_display_y, anchor='nw', image=photo, tags="image")
        image_canvas.image = photo
        
        update_zoom_display()
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
    def _set():
        global status_timer_id
        if status_timer_id is not None:
            root.after_cancel(status_timer_id)
        
        status_label.config(text=message, bootstyle=color)
        status_timer_id = root.after(5000, lambda: status_label.config(text=DEFAULT_STATUS_MSG, bootstyle="secondary"))
    
    root.after(0, _set)

def update_split_direction(*args):
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
    global file_path, file_extension
    paths = root.tk.splitlist(event.data)
    if not paths:
        return
    dropped_path = paths[0]
    ext = os.path.splitext(dropped_path)[1].lower()
    if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic']:
        threading.Thread(target=load_file_in_background, args=(dropped_path, ext), daemon=True).start()
    else:
        set_status(f"不支持的文件类型: {ext}", "danger")

def update_grid_lines(event):
    row_val = grid_row_entry.get().strip()
    col_val = grid_col_entry.get().strip()
    if not row_val or not col_val:
        return
    try:
        grid_row = int(row_val)
        grid_col = int(col_val)
        if grid_row < 1 or grid_col < 1:
            raise ValueError
        draw_split_line()
    except ValueError:
        pass

def get_original_image(target_file_path, target_file_extension):
    if target_file_extension == '.heic':
        heif_file = pillow_heif.read_heif(target_file_path)
        img = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        return [img.convert("RGB")]
    elif target_file_extension == '.pdf':
        doc = fitz.open(target_file_path)
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
        return [Image.open(target_file_path).convert("RGB")]

def on_dpi_change(*args):
    global file_path, file_extension
    set_status(f"DPI设置为: {dpi_var.get()}", "info")
    if file_path and file_extension == '.pdf':
        threading.Thread(target=load_file_in_background, args=(file_path, file_extension), daemon=True).start()

def open_update_link():
    webbrowser.open("https://github.com/Qwejay/ImageSplitter")

def rotate_image():
    global imgs, current_page
    if imgs:
        if apply_all_var.get():
            imgs = [img.rotate(90, expand=True) for img in imgs]
            set_status("所有页面已旋转 90 度。", "info")
        else:
            imgs[current_page - 1] = imgs[current_page - 1].rotate(90, expand=True)
            set_status("当前页面已旋转 90 度。", "info")
        display_image()

def horizontal_flip():
    global imgs, current_page
    if imgs:
        if apply_all_var.get():
            imgs = [img.transpose(Image.FLIP_LEFT_RIGHT) for img in imgs]
            set_status("所有页面已水平翻转。", "info")
        else:
            imgs[current_page - 1] = imgs[current_page - 1].transpose(Image.FLIP_LEFT_RIGHT)
            set_status("当前页面已水平翻转。", "info")
        display_image()

def vertical_flip():
    global imgs, current_page
    if imgs:
        if apply_all_var.get():
            imgs = [img.transpose(Image.FLIP_TOP_BOTTOM) for img in imgs]
            set_status("所有页面已垂直翻转。", "info")
        else:
            imgs[current_page - 1] = imgs[current_page - 1].transpose(Image.FLIP_TOP_BOTTOM)
            set_status("当前页面已垂直翻转。", "info")
        display_image()

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
        schedule_display()

def adjust_offset_for_zoom(old_scale, new_scale, mouse_x, mouse_y):
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
    
    schedule_display()

def zoom_out(event=None):
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
    
    schedule_display()

def reset_zoom():
    global zoom_scale, img_offset_x, img_offset_y
    zoom_scale = 1.0
    img_offset_x = 0
    img_offset_y = 0
    display_image()
    set_status("缩放已重置为原始尺寸", "info")

def fit_to_window():
    global auto_fit_on_load
    auto_fit_on_load = True
    display_image()
    set_status("已适应窗口", "info")

def update_zoom_display():
    if zoom_display_label:
        percentage = int(zoom_scale * 100)
        zoom_display_label.config(text=f"{percentage}%")

if DROP_SUPPORTED:
    root = TkinterDnD.Tk()
else:
    root = tk.Tk()

root.geometry("1080x720")
root.title(f"{__app_name__} {__version__} —— {__author__}")

try:
    root.iconbitmap('icon.ico')
except:
    pass

style = ttk.Style("litera")

top_menu = ttk.Frame(root)
top_menu.pack(fill=tk.X, padx=5, pady=5)

open_button = ttk.Button(top_menu, text="打开文件", command=open_file, bootstyle="primary")
open_button.pack(side=tk.LEFT, padx=5, pady=5)

split_direction_var = tk.StringVar(value='不分割')

direction_menu_label = ttk.Label(top_menu, text="分割类型:", bootstyle="secondary")
direction_menu_label.pack(side=tk.LEFT, padx=2)
direction_menu = ttk.OptionMenu(top_menu, split_direction_var, '不分割', '不分割', '垂直', '水平', '多宫格')
direction_menu.pack(side=tk.LEFT, padx=2, pady=5)

split_direction_var.trace('w', update_split_direction)

vcmd = (root.register(lambda value: value.isdigit() or value == ""), '%P')
grid_row_entry_label = ttk.Label(top_menu, text="行数:", bootstyle="secondary")
grid_row_entry_label.pack(side=tk.LEFT, padx=2)
grid_row_entry = ttk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_row_entry.pack(side=tk.LEFT, padx=2)
grid_row_entry.insert(0, "3")
grid_row_entry['state'] = 'disabled'

grid_col_entry_label = ttk.Label(top_menu, text="列数:", bootstyle="secondary")
grid_col_entry_label.pack(side=tk.LEFT, padx=2)
grid_col_entry = ttk.Entry(top_menu, width=5, validate='key', validatecommand=vcmd)
grid_col_entry.pack(side=tk.LEFT, padx=2)
grid_col_entry.insert(0, "3")
grid_col_entry['state'] = 'disabled'

dpi_var = tk.StringVar(value="默认")
dpi_label = ttk.Label(top_menu, text="保存DPI:", bootstyle="secondary")
dpi_label.pack(side=tk.LEFT, padx=2)
dpi_combobox = ttk.Combobox(top_menu, textvariable=dpi_var, values=["默认", "72", "150", "300"], width=5)
dpi_combobox.pack(side=tk.LEFT, padx=2, pady=5)

dpi_combobox.bind("<<ComboboxSelected>>", on_dpi_change)
dpi_combobox.bind("<FocusOut>", on_dpi_change)

save_format_var = tk.StringVar(value='.jpg')
save_format_label = ttk.Label(top_menu, text="保存格式:", bootstyle="secondary")
save_format_label.pack(side=tk.LEFT, padx=2)
save_format_menu = ttk.OptionMenu(top_menu, save_format_var, '.JPG', '.JPG', '.PDF', '.PNG', '.BMP', '.WEBP', '.HEIC')
save_format_menu.pack(side=tk.LEFT, padx=2, pady=5)

save_range_var = tk.StringVar(value="全部")
save_range_label = ttk.Label(top_menu, text="导出范围:", bootstyle="secondary")
save_range_label.pack(side=tk.LEFT, padx=2)
save_range_combo = ttk.Combobox(top_menu, textvariable=save_range_var, values=["全部", "当前页", "1-3,5"], width=7)
save_range_combo.pack(side=tk.LEFT, padx=5, pady=5)

save_button = ttk.Button(top_menu, text="保存文件", command=save_file, bootstyle="primary")
save_button.pack(side=tk.LEFT, padx=5, pady=5)

preview_frame = ttk.Frame(root)
preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

image_canvas = ttk.Canvas(preview_frame, background="#e0e0e0")
image_canvas.pack(fill=tk.BOTH, expand=True)

button_frame = ttk.Frame(preview_frame)
button_frame.pack(fill=tk.X, pady=5)

button_frame.grid_columnconfigure(0, weight=1)
button_frame.grid_columnconfigure(1, weight=0)
button_frame.grid_columnconfigure(2, weight=1)

page_control_frame = ttk.Frame(button_frame)
page_control_frame.grid(row=0, column=1, padx=5, sticky='nsew')

page_label = ttk.Label(page_control_frame, text="当前页面：", bootstyle="secondary")
page_label.pack(side=tk.LEFT, padx=2)

prev_page_btn = ttk.Button(page_control_frame, text="◀", command=lambda: page_var.set(str(current_page-1)) if current_page > 1 else None, bootstyle="secondary-outline")
prev_page_btn.pack(side=tk.LEFT, padx=2)

page_var = tk.StringVar(value="1")
page_spinbox = ttk.Spinbox(page_control_frame, from_=1, to=1, textvariable=page_var, width=4)
page_spinbox.pack(side=tk.LEFT, padx=2)
page_var.trace_add('write', lambda *args: update_current_page())

next_page_btn = ttk.Button(page_control_frame, text="▶", command=lambda: page_var.set(str(current_page+1)) if current_page < total_pages else None, bootstyle="secondary-outline")
next_page_btn.pack(side=tk.LEFT, padx=2)

button_inner_frame = ttk.Frame(button_frame)
button_inner_frame.grid(row=0, column=2, padx=5, sticky='e')

split_color_var = tk.StringVar(value='红色')
split_color_var.trace('w', lambda *args: draw_split_line())

color_label = ttk.Label(button_inner_frame, text="分割线：", bootstyle="secondary")
color_label.pack(side=tk.LEFT, padx=2)

color_options = ['红色', '蓝色', '绿色', '黑色', '黄色']
color_menu = ttk.OptionMenu(button_inner_frame, split_color_var, '红色', *color_options)
color_menu.pack(side=tk.LEFT, padx=2)

apply_all_var = tk.BooleanVar(value=False)
apply_all_chk = ttk.Checkbutton(button_inner_frame, text="操作全部页", variable=apply_all_var, bootstyle="round-toggle")
apply_all_chk.pack(side=tk.LEFT, padx=5)

rotate_button = ttk.Button(button_inner_frame, text="旋转", command=rotate_image, bootstyle="secondary")
rotate_button.pack(side=tk.LEFT, padx=2)

horizontal_flip_button = ttk.Button(button_inner_frame, text="水平镜像", command=horizontal_flip, bootstyle="secondary")
horizontal_flip_button.pack(side=tk.LEFT, padx=2)

vertical_flip_button = ttk.Button(button_inner_frame, text="垂直镜像", command=vertical_flip, bootstyle="secondary")
vertical_flip_button.pack(side=tk.LEFT, padx=2)

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

zoom_display_label = ttk.Label(zoom_frame, text="100%", bootstyle="secondary", width=5)
zoom_display_label.pack(side=tk.LEFT, padx=2)

image_canvas.bind("<ButtonPress-1>", start_drag)
image_canvas.bind("<ButtonRelease-1>", stop_drag)
image_canvas.bind("<B1-Motion>", on_drag)
image_canvas.bind("<MouseWheel>", lambda event: zoom_in(event) if event.delta > 0 else zoom_out(event))
image_canvas.bind("<Button-4>", lambda event: zoom_in(event))
image_canvas.bind("<Button-5>", lambda event: zoom_out(event))

def on_resize(event):
    global window_resize_id, last_canvas_width, last_canvas_height
    if event.width == last_canvas_width and event.height == last_canvas_height:
        return
    last_canvas_width = event.width
    last_canvas_height = event.height
    
    if window_resize_id:
        root.after_cancel(window_resize_id)
    window_resize_id = root.after(100, display_image)

image_canvas.bind("<Configure>", on_resize)

status_bar = ttk.Frame(root, relief='sunken', borderwidth=1)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

status_label = ttk.Label(status_bar, text=DEFAULT_STATUS_MSG, bootstyle="secondary", anchor='w', padding=(5, 0))
status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

update_link = ttk.Label(status_bar, text="检查更新", cursor="hand2", foreground="blue")
update_link.pack(side=tk.RIGHT, padx=5)
update_link.bind("<Button-1>", lambda e: open_update_link())

if DROP_SUPPORTED:
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>', on_drop)
    image_canvas.drop_target_register(DND_FILES)
    image_canvas.dnd_bind('<<Drop>>', on_drop)

grid_row_entry.bind('<KeyRelease>', update_grid_lines)
grid_col_entry.bind('<KeyRelease>', update_grid_lines)

root.mainloop()
