# Image Splitter

**Image Splitter** 这是一个图像拆分（九宫格神器）小工具，兼具pdf和jpg等格式的互转功能。

## 功能特点

### 图像拆分
- 支持垂直和水平方向的图像拆分
- 支持自定义多宫格的图片分割

### 多种格式的相互转换
- 支持多种图像格式，包括PDF、JPEG、PNG、BMP、WEBP、HEIC格式一键互转。

### 实时预览
- 提供实时预览功能，用户可以在拆分前查看效果
- 支持图像缩放，确保在不同分辨率下都能清晰显示

### 拖放支持
- 支持拖放操作，用户可以直接将图像文件拖入程序界面进行处理

### 用户友好界面
- 简洁直观的用户界面，易于上手

### 下载地址：https://github.com/Qwejay/ImageSplitter/releases

## 版本历史
### Image Splitter v1.4
**发布日期**: 2024-12-15
若没有大BUG或者新的想法，这个版本可以养老
  
**新增功能**:
- 增加图片的旋转、水平镜像、垂直镜像功能
- 使用主题美化了程序界面
- 去除了文件大小预估
- 增加HEIC格式的支持
- 稳定性的提升

### Image Splitter v1.3
**发布日期**: 2024-12-13

**新增功能**:
- 自动检测图片方向并设置默认分割线
- 增加多宫格裁切：可以自定义图片裁切块数，默认九宫格
- 修复分割线超出图片边界：现在分割线可正确显示在图片内

### Image Splitter v1.2
**发布日期**: 2024-12-12

**新增功能**:
- 文件大小预估：在保存文件时显示预估文件大小
- DPI选择：导出文件时可选择多种DPI选项

### Image Splitter v1.1
**发布日期**: 2024-12-11

**更新内容**:
- 根据网友反馈：图像预览现在支持动态调整大小，图像会根据窗口大小自动缩放并居中显示
- 多页PDF支持
- 状态栏改进
- 图像预览改进
- 保存功能改进
- 用户体验优化

## 打包命令

```bash
pyinstaller --onefile --windowed --icon=icon.ico --add-data "tkdnd;tkdnd" ImageSplitter.py
