import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import io
from tkinterdnd2 import TkinterDnD, DND_FILES

root = TkinterDnD.Tk()
root.title("Image Splitter v1.0 —— QwejayHuang")

# 全局变量
file_path = ""
img = None
file_extension = ""
split_position = 0.5
split_direction = '垂直'
save_format = '.pdf'

# 获取原始图像
def get_original_image():
    if file_extension == '.pdf':
        doc = fitz.open(file_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(alpha=True)  # 保留alpha通道
        return Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
    else:
        return Image.open(file_path).convert("RGBA")

# 拆分图像
def split_image(img, direction):
    if direction == '垂直':
        split_width = int(img.width * split_position)
        left_img = img.crop((0, 0, split_width, img.height))
        right_img = img.crop((split_width, 0, img.width, img.height))
        return [left_img, right_img]
    elif direction == '水平':
        split_height = int(img.height * split_position)
        top_img = img.crop((0, 0, img.width, split_height))
        bottom_img = img.crop((0, split_height, img.width, img.height))
        return [top_img, bottom_img]
    elif direction == '不拆分':
        return [img]

# 保存图像
def save_images(imgs, extension):
    if extension == '.pdf':
        new_doc = fitz.open()
        for i, img in enumerate(imgs):
            with io.BytesIO() as output:
                img.save(output, format="PNG")
                image_bytes = output.getvalue()
            page = new_doc.new_page(width=img.width, height=img.height)
            page.insert_image(fitz.Rect(0, 0, img.width, img.height), stream=image_bytes)
        save_path = os.path.splitext(file_path)[0] + "_split.pdf"
        new_doc.save(save_path)
        messagebox.showinfo("成功", "PDF保存成功。")
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
            save_path = os.path.splitext(file_path)[0] + f"_part{i+1}" + extension
            if mode == 'RGB':
                img.convert("RGB").save(save_path)
            else:
                img.save(save_path)
        messagebox.showinfo("成功", f"图像保存成功，共 {len(imgs)} 个部分。")

# 保存文件
def save_file():
    if not file_path:
        messagebox.showerror("错误", "没有选择文件。")
        return
    
    save_extension = save_format_var.get()
    original_img = get_original_image()
    
    direction = split_direction_var.get()
    
    if direction == '不拆分':
        imgs = [original_img]
    else:
        imgs = split_image(original_img, direction)
    
    save_images(imgs, save_extension)

# 创建顶部菜单栏
top_menu = tk.Frame(root, bg='white')
top_menu.pack(side='top', fill='x')

# 打开文件按钮
def open_file():
    global file_path, img, file_extension
    file_path = filedialog.askopenfilename(filetypes=[("图片文件", "*.pdf;*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.gif;*.webp;*.ico")])
    if file_path:
        file_extension = os.path.splitext(file_path)[1].lower()
        img = get_original_image()
        display_image()

open_button = tk.Button(top_menu, text="打开文件", command=open_file, bg='#4CAF50', fg='white')
open_button.pack(side='left', padx=10, pady=5)

# 拆分方向下拉菜单
split_direction_var = tk.StringVar()
split_direction_var.set('不拆分')  # Set default to '不拆分'
direction_menu = tk.OptionMenu(
    top_menu, split_direction_var, '垂直', '水平', '不拆分',
    command=lambda _: update_split_direction()
)
direction_menu.config(bg='white', fg='black')
direction_menu.pack(side='left', padx=10, pady=5)

# 保存文件格式下拉菜单
save_format_var = tk.StringVar()
save_format_var.set('.jpg')
save_format_menu = tk.OptionMenu(top_menu, save_format_var, '.jpg', '.pdf', '.png', '.bmp', '.tiff', '.webp', '.ico')
save_format_menu.config(bg='white', fg='black')
save_format_menu.pack(side='left', padx=10, pady=5)

save_button = tk.Button(top_menu, text="保存文件", command=save_file, bg='#4CAF50', fg='white')
save_button.pack(side='left', padx=10, pady=5)

# 创建中间控制面板
control_panel = tk.Frame(root, bg='white')
control_panel.pack(side='top', fill='x')

# 创建底部预览区域
preview_frame = tk.Frame(root, bg='#F2F2F2')
preview_frame.pack(side='bottom', fill='both', expand=True)

# 创建Canvas用于显示图像
image_canvas = tk.Canvas(preview_frame, bg='#E0E0E0')
image_canvas.pack(fill='both', expand=True)

# 创建标签用于显示分割百分比
split_percentage_label = tk.Label(preview_frame, text="分割位置: 50%", bg='#F2F2F2', fg='black')
split_percentage_label.pack(side='top', pady=5)

# 显示图像到Canvas
def display_image():
    global img
    if img:
        image_canvas.delete("all")  # 清空Canvas
        img_width, img_height = img.size
        canvas_width = image_canvas.winfo_width()
        canvas_height = image_canvas.winfo_height()
        # 保持AspectRatio
        if img_width / img_height > canvas_width / canvas_height:
            new_width = canvas_width
            new_height = int(new_width * img_height / img_width)
        else:
            new_height = canvas_height
            new_width = int(new_height * img_width / img_height)
        resized_img = img.resize((new_width, new_height))
        photo = ImageTk.PhotoImage(resized_img)
        image_canvas.create_image(0, 0, anchor='nw', image=photo)
        image_canvas.image = photo  # 保持对图像的引用
        # 绘制分割线
        draw_split_line()

# 绘制分割线
def draw_split_line():
    image_canvas.delete("split_line")  # 清空之前的分割线
    canvas_width = image_canvas.winfo_width()
    canvas_height = image_canvas.winfo_height()
    direction = split_direction_var.get()
    
    if direction == '垂直':
        split_x = int(canvas_width * split_position)
        image_canvas.create_line(
            split_x, 0, split_x, canvas_height, fill='red', width=2, tags="split_line"
        )
    elif direction == '水平':
        split_y = int(canvas_height * split_position)
        image_canvas.create_line(
            0, split_y, canvas_width, split_y, fill='red', width=2, tags="split_line"
        )
    elif direction == '不拆分':
        pass  # 不绘制分割线
    
    update_split_percentage_label()

# 更新分割百分比标签
def update_split_percentage_label():
    split_percentage_label.config(text=f"分割位置: {int(split_position * 100)}%")

# 更新分割方向
def update_split_direction():
    global split_direction
    split_direction = split_direction_var.get()
    draw_split_line()

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
    elif direction == '不拆分':
        split_position = 0.5  # 重置分割位置
    draw_split_line()

# 绑定拖动事件
image_canvas.bind("<B1-Motion>", drag_split_line)

# 处理拖放文件
def handle_drop(event):
    global file_path, img, file_extension
    file_path = event.data.strip('{}')
    if file_path:
        file_extension = os.path.splitext(file_path)[1].lower()
        img = get_original_image()
        display_image()

# 绑定拖放事件
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', handle_drop)

root.mainloop()