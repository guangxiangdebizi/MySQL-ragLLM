/**
 * 数据可视化模块
 * 负责SQL查询结果的可视化展示和图表导出功能
 */

// 存储当前图表数据
let currentChartData = null;
let currentChartType = null;
let currentChartObject = null;

// 初始化可视化模块
function initDataVisualization() {
    // 添加事件监听
    document.getElementById('visualize-btn').addEventListener('click', visualizeCurrentQuery);
    document.getElementById('export-chart-btn').addEventListener('click', exportChart);
    document.getElementById('change-chart-type').addEventListener('click', changeChartType);
}

// 可视化当前查询
async function visualizeCurrentQuery() {
    const visualContainer = document.getElementById('chart-container');
    const sqlEditor = document.querySelector('.CodeMirror').CodeMirror;
    const sql = sqlEditor.getValue();
    
    if (!sql) {
        showMessage('请先输入SQL查询', 'error');
        return;
    }
    
    visualContainer.innerHTML = '<div class="loading p-8 flex justify-center items-center min-h-[300px]">正在生成可视化...</div>';
    
    try {
        // 获取数据库配置
        const dbConfig = getDbConfig();
        if (!dbConfig) {
            visualContainer.innerHTML = '<div class="p-4 bg-red-100 text-red-700 rounded">请先配置并连接数据库</div>';
            return;
        }
        
        // 发送查询请求
        const response = await fetch('/api/visualize-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                config: dbConfig,
                query: sql
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            visualContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">生成可视化失败: ${result.error}</div>`;
            return;
        }
        
        if (result.visualization_type === 'none') {
            visualContainer.innerHTML = `<div class="p-4 bg-yellow-100 text-yellow-700 rounded">查询结果为空或无法可视化</div>`;
            return;
        }
        
        // 保存当前图表数据
        currentChartData = result.chart_data;
        currentChartType = result.visualization_type;
        
        // 准备图表容器
        visualContainer.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded shadow p-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold">查询结果可视化</h3>
                    <div class="flex space-x-2">
                        <button id="change-chart-type" class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600">
                            切换图表类型
                        </button>
                        <button id="export-chart-btn" class="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600">
                            导出图表
                        </button>
                    </div>
                </div>
                <div class="border rounded p-4 bg-white dark:bg-gray-700 min-h-[300px]">
                    <canvas id="chart-canvas"></canvas>
                </div>
            </div>
        `;
        
        // 重新绑定事件
        document.getElementById('change-chart-type').addEventListener('click', changeChartType);
        document.getElementById('export-chart-btn').addEventListener('click', exportChart);
        
        // 渲染图表
        renderChart(result.visualization_type, result.chart_data);
        
    } catch (error) {
        visualContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">可视化过程中发生错误: ${error.message}</div>`;
    }
}

// 渲染图表
function renderChart(chartType, chartData) {
    // 确保Chart.js已加载
    if (!window.Chart) {
        loadScript('https://cdn.jsdelivr.net/npm/chart.js', () => {
            renderChartWithType(chartType, chartData);
        });
    } else {
        renderChartWithType(chartType, chartData);
    }
}

// 根据图表类型渲染
function renderChartWithType(chartType, chartData) {
    const ctx = document.getElementById('chart-canvas').getContext('2d');
    
    // 如果有现有图表，先销毁
    if (currentChartObject) {
        currentChartObject.destroy();
    }
    
    // 图表配置
    let chartConfig = {
        responsive: true,
        maintainAspectRatio: false
    };
    
    // 根据图表类型创建不同的图表
    switch (chartType) {
        case 'bar':
            currentChartObject = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chartData.labels,
                    datasets: chartData.datasets.map(ds => ({
                        ...ds,
                        backgroundColor: generateColors(chartData.labels.length)
                    }))
                },
                options: {
                    ...chartConfig,
                    plugins: {
                        title: {
                            display: true,
                            text: '柱状图'
                        }
                    }
                }
            });
            break;
            
        case 'line':
            currentChartObject = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: chartData.datasets.map(ds => ({
                        ...ds,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.1
                    }))
                },
                options: {
                    ...chartConfig,
                    plugins: {
                        title: {
                            display: true,
                            text: '折线图'
                        }
                    }
                }
            });
            break;
            
        case 'pie':
            currentChartObject = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: chartData.labels,
                    datasets: chartData.datasets.map(ds => ({
                        ...ds,
                        backgroundColor: generateColors(chartData.labels.length)
                    }))
                },
                options: {
                    ...chartConfig,
                    plugins: {
                        title: {
                            display: true,
                            text: '饼图'
                        }
                    }
                }
            });
            break;
            
        case 'scatter':
            currentChartObject = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: chartData.datasets.map(ds => ({
                        ...ds,
                        backgroundColor: '#3b82f6'
                    }))
                },
                options: {
                    ...chartConfig,
                    plugins: {
                        title: {
                            display: true,
                            text: '散点图'
                        }
                    }
                }
            });
            break;
            
        case 'table':
            // 表格视图，使用Tabulator
            renderTableView(chartData.data);
            break;
            
        default:
            showMessage('不支持的图表类型: ' + chartType, 'error');
    }
}

// 渲染表格视图
function renderTableView(data) {
    // 销毁任何存在的图表
    if (currentChartObject) {
        currentChartObject.destroy();
        currentChartObject = null;
    }
    
    const canvasContainer = document.getElementById('chart-canvas').parentNode;
    canvasContainer.innerHTML = '<div id="results-table"></div>';
    
    // 使用Tabulator渲染表格
    if (!window.Tabulator) {
        loadScript('https://unpkg.com/tabulator-tables@5.5.0/dist/js/tabulator.min.js', () => {
            createTabulator(data);
        });
    } else {
        createTabulator(data);
    }
}

// 创建Tabulator表格
function createTabulator(data) {
    if (!data || data.length === 0) {
        document.getElementById('results-table').innerHTML = '<div class="p-4 text-center text-gray-500">无数据可显示</div>';
        return;
    }
    
    // 从第一行数据获取列
    const columns = Object.keys(data[0]).map(key => ({
        title: key,
        field: key,
        sorter: 'string'
    }));
    
    // 创建表格
    new Tabulator('#results-table', {
        data: data,
        columns: columns,
        layout: 'fitColumns',
        pagination: 'local',
        paginationSize: 10,
        paginationSizeSelector: [5, 10, 20, 50],
        movableColumns: true,
        resizableRows: true,
        responsiveLayout: 'collapse',
        height: '400px'
    });
}

// 切换图表类型
function changeChartType() {
    if (!currentChartData) {
        showMessage('没有可用的图表数据', 'error');
        return;
    }
    
    // 图表类型循环
    const chartTypes = ['bar', 'line', 'pie', 'scatter', 'table'];
    let nextTypeIndex = (chartTypes.indexOf(currentChartType) + 1) % chartTypes.length;
    currentChartType = chartTypes[nextTypeIndex];
    
    // 重新渲染图表
    renderChartWithType(currentChartType, currentChartData);
}

// 导出图表
async function exportChart() {
    if (!currentChartData) {
        showMessage('没有可用的图表数据', 'error');
        return;
    }
    
    try {
        // 准备导出数据
        const chartTitle = prompt('请输入图表标题', '数据图表');
        if (!chartTitle) return; // 用户取消
        
        // 请求导出
        const response = await fetch('/api/export-chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chart_data: currentChartData,
                chart_type: currentChartType,
                chart_title: chartTitle
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            showMessage(`导出失败: ${result.error}`, 'error');
            return;
        }
        
        // 导出为JSON文件
        const dataStr = JSON.stringify(result.export_data, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
        
        // 创建下载链接
        const exportName = `chart_${chartTitle.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.json`;
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportName);
        document.body.appendChild(linkElement);
        linkElement.click();
        document.body.removeChild(linkElement);
        
        // 如果是图表类型，还可以导出为图片
        if (currentChartObject && currentChartType !== 'table') {
            exportChartAsImage(chartTitle);
        }
        
        showMessage('导出成功', 'success');
        
    } catch (error) {
        showMessage(`导出过程中发生错误: ${error.message}`, 'error');
    }
}

// 导出图表为图片
function exportChartAsImage(title) {
    if (!currentChartObject) return;
    
    const canvas = currentChartObject.canvas;
    const imageUri = canvas.toDataURL('image/png');
    
    // 创建下载链接
    const exportName = `chart_${title.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.png`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', imageUri);
    linkElement.setAttribute('download', exportName);
    document.body.appendChild(linkElement);
    linkElement.click();
    document.body.removeChild(linkElement);
}

// 生成随机颜色
function generateColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const hue = (i * 137) % 360; // 均匀分布的色相
        colors.push(`hsl(${hue}, 70%, 60%)`);
    }
    return colors;
}

// 显示消息
function showMessage(message, type = 'info') {
    // 使用toast显示消息
    showToast(message, type);
}

// 加载JS脚本
function loadScript(url, callback) {
    const script = document.createElement('script');
    script.src = url;
    script.onload = callback;
    document.head.appendChild(script);
}

// 获取数据库配置
function getDbConfig() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const host = document.getElementById('host').value;
    const port = document.getElementById('port').value;
    const database = document.getElementById('database').value;
    
    if (!username || !host || !port) return null;
    
    return {
        username: username,
        password: password,
        host: host,
        port: port,
        database: database
    };
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initDataVisualization();
}); 