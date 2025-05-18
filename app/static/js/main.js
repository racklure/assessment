// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 文件上传大小验证
    const photoInput = document.getElementById('photo');
    if (photoInput) {
        photoInput.addEventListener('change', function() {
            const maxSize = 2 * 1024 * 1024; // 2MB
            if (this.files[0] && this.files[0].size > maxSize) {
                alert('文件大小超过2MB限制，请选择较小的文件');
                this.value = '';
            }
        });
    }
    
    // 评分表单验证
    const evaluationForm = document.querySelector('form[enctype="multipart/form-data"]');
    if (evaluationForm) {
        evaluationForm.addEventListener('submit', function(event) {
            const scoreInputs = document.querySelectorAll('input[name^="score_"]');
            let isValid = true;
            
            scoreInputs.forEach(input => {
                const value = parseFloat(input.value);
                const max = parseFloat(input.getAttribute('max'));
                
                if (isNaN(value) || value < 0 || value > max) {
                    isValid = false;
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                event.preventDefault();
                alert('请检查评分，确保所有分数在有效范围内');
            }
        });
    }
});

// 图表绘制函数
function drawChart(canvasId, labels, data, title) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: title,
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}