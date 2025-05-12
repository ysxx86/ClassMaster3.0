# ClassMaster 2.2 CDN 本地化说明

## 概述

本次更新将系统中使用的CDN资源全部转换为本地文件，以提高系统在无网络或网络不稳定环境下的可靠性。

## 完成的工作

1. 下载并存储了以下库的本地版本：
   - Bootstrap 5.3.0-alpha1（CSS和JS）
   - Boxicons（使用已有的boxicons-local.css）
   - Chart.js
   - jQuery 3.6.0
   - 文档处理库：
     - PizZip 3.1.4
     - Docxtemplater 3.37.11
     - JSZip 3.10.1

2. 修改了所有HTML文件中的CDN引用，替换为对应的本地路径：
   - `/css/bootstrap.min.css`
   - `/css/boxicons-local.css`
   - `/js/libs/bootstrap.bundle.min.js`
   - `/js/libs/chart.js`
   - `/js/libs/jquery.min.js`
   - `/libs/pizzip.min.js`
   - `/libs/docxtemplater.js`
   - `/libs/jszip.min.js`

3. 更新了JavaScript中的动态加载逻辑，确保使用本地文件而非CDN资源。

4. 创建了以下工具脚本：
   - `update_cdn_to_local.py` - 自动将CDN引用替换为本地路径
   - `verify_cdn_replaced.py` - 验证CDN替换是否成功完成

## 文件结构

更新后的库文件结构如下：

```
/css/
  - bootstrap.min.css
  - boxicons-local.css
  - ...

/js/libs/
  - bootstrap.bundle.min.js
  - chart.js
  - jquery.min.js
  - ...

/libs/
  - pizzip.min.js
  - docxtemplater.js
  - jszip.min.js
  - ...

/fonts/
  - boxicons.woff2
  - ...
```

## 回退机制

尽管所有资源都已本地化，系统仍保留了在本地文件加载失败时尝试使用备用路径的逻辑，以增强系统的健壮性。

## 注意事项

1. 如果更新前端库版本，需要同时更新对应的本地文件。
2. 添加新的前端依赖时，建议同时下载到本地并在HTML中使用本地路径。 