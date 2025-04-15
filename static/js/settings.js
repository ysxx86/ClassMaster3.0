// 函数：获取轮播设置
function getCarouselSettings() {
    fetch('/api/carousel/settings')
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const settings = data.settings;
            
            // 设置轮播间隔
            document.getElementById('carouselInterval').value = settings.interval || 5000;
            updateIntervalDisplay();
            
            // 设置最大图片数量
            document.getElementById('maxImages').value = settings.maxImages || 5;
            
            // 设置动画效果
            const animationRadios = document.getElementsByName('animation');
            for (let radio of animationRadios) {
                if (radio.value === settings.animation) {
                    radio.checked = true;
                    break;
                }
            }
            
            // 设置指示器样式
            const indicatorRadios = document.getElementsByName('indicatorStyle');
            for (let radio of indicatorRadios) {
                if (radio.value === settings.indicatorStyle) {
                    radio.checked = true;
                    break;
                }
            }
            
            // 设置指示器颜色
            document.getElementById('indicatorColor').value = settings.indicatorColor || '#ffffff';
            
            // 设置进度显示
            document.getElementById('showProgress').checked = settings.showProgress !== false;
            
            console.log('成功加载轮播设置');
        } else {
            showToast('error', '获取轮播设置失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('获取轮播设置出错:', error);
        showToast('error', '获取轮播设置出错: ' + error.message);
    });
}

// 函数：保存轮播设置
function saveCarouselSettings() {
    // 获取轮播间隔
    const interval = parseInt(document.getElementById('carouselInterval').value);
    
    // 获取最大图片数量
    const maxImages = parseInt(document.getElementById('maxImages').value);
    
    // 获取动画效果
    let animation = 'fade';
    const animationRadios = document.getElementsByName('animation');
    for (let radio of animationRadios) {
        if (radio.checked) {
            animation = radio.value;
            break;
        }
    }
    
    // 获取指示器样式
    let indicatorStyle = 'rounded-pill';
    const indicatorRadios = document.getElementsByName('indicatorStyle');
    for (let radio of indicatorRadios) {
        if (radio.checked) {
            indicatorStyle = radio.value;
            break;
        }
    }
    
    // 获取指示器颜色
    const indicatorColor = document.getElementById('indicatorColor').value;
    
    // 获取进度显示
    const showProgress = document.getElementById('showProgress').checked;
    
    // 构建设置对象
    const settings = {
        interval,
        maxImages,
        animation,
        indicatorStyle,
        indicatorColor,
        showProgress
    };
    
    // 发送设置到服务器
    fetch('/api/carousel/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('success', '轮播设置保存成功');
        } else {
            showToast('error', '轮播设置保存失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('保存轮播设置出错:', error);
        showToast('error', '保存轮播设置出错: ' + error.message);
    });
} 