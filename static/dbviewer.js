/**
 * 数据库可视化与数据编辑模块
 */

// 当前数据库连接配置
let currentDbConfig = null;

// 初始化数据库浏览器组件
function initDatabaseViewer() {
    // 初始化事件监听
    document.getElementById('show-db-structure').addEventListener('click', loadDatabaseStructure);
    document.getElementById('show-relationships').addEventListener('click', loadTableRelationships);
    
    // 添加表格行双击事件代理（用于表格编辑）
    document.addEventListener('dblclick', function(e) {
        const tableCell = e.target.closest('td');
        if (tableCell && tableCell.closest('.editable-table')) {
            makeTableCellEditable(tableCell);
        }
    });
}

// 加载数据库结构
async function loadDatabaseStructure() {
    const dbStructureContainer = document.getElementById('db-structure-container');
    dbStructureContainer.innerHTML = '<div class="loading p-4">加载数据库结构...</div>';
    
    try {
        // 获取当前连接配置
        const dbConfig = getDbConfig();
        if (!dbConfig) {
            dbStructureContainer.innerHTML = '<div class="p-4 bg-red-100 text-red-700 rounded">请先配置并连接数据库</div>';
            return;
        }
        
        currentDbConfig = dbConfig;
        
        // 请求数据库结构
        const response = await fetch('/api/db-structure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dbConfig)
        });
        
        const result = await response.json();
        
        if (!result.success) {
            dbStructureContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">获取数据库结构失败: ${result.error}</div>`;
            return;
        }
        
        // 显示数据库结构
        dbStructureContainer.innerHTML = '';
        const dbInfo = result.db_structure;
        
        // 检查是否返回的是字符串而非对象
        if (typeof dbInfo === 'string') {
            dbStructureContainer.innerHTML = `<div class="p-4 bg-white dark:bg-gray-800 rounded shadow">
                <h2 class="text-xl font-bold mb-2">数据库结构</h2>
                <pre class="bg-gray-100 dark:bg-gray-700 p-4 rounded overflow-auto whitespace-pre-wrap">${dbInfo}</pre>
            </div>`;
            return;
        }
        
        // 检查必要的属性是否存在
        if (!dbInfo || !dbInfo.database_name) {
            dbStructureContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">无效的数据库结构信息</div>`;
            return;
        }
        
        // 确保tables和relationships属性存在
        const tables = dbInfo.tables || [];
        const relationships = dbInfo.relationships || [];
        
        // 创建数据库信息头部
        const header = document.createElement('div');
        header.className = 'bg-blue-100 dark:bg-blue-900 p-4 rounded-t border-b border-blue-200 dark:border-blue-700';
        header.innerHTML = `
            <h2 class="text-xl font-bold">数据库: ${dbInfo.database_name}</h2>
            <div class="text-sm mt-1">共 ${tables.length} 个表, ${relationships.length} 个表关系</div>
        `;
        dbStructureContainer.appendChild(header);
        
        // 创建表列表
        const tableList = document.createElement('div');
        tableList.className = 'p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4';
        
        // 检查是否有表可以显示
        if (tables.length === 0) {
            tableList.innerHTML = `<div class="col-span-3 p-4 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded">
                未找到表信息
            </div>`;
            dbStructureContainer.appendChild(tableList);
            return;
        }
        
        tables.forEach(table => {
            const tableCard = document.createElement('div');
            tableCard.className = 'bg-white dark:bg-gray-800 rounded shadow p-4 hover:shadow-md transition-shadow cursor-pointer';
            tableCard.onclick = () => loadTableData(table.name);
            
            let columnsHtml = '';
            table.columns.forEach(col => {
                let colClass = '';
                if (col.name === table.primary_key) colClass = 'text-blue-600 dark:text-blue-400 font-bold';
                else if (col.key === 'MUL') colClass = 'text-green-600 dark:text-green-400';
                
                columnsHtml += `
                    <div class="text-sm py-1 border-b border-gray-100 dark:border-gray-700 flex justify-between">
                        <span class="${colClass}">${col.name}</span>
                        <span class="text-gray-500 dark:text-gray-400 text-xs">${col.type}</span>
                    </div>
                `;
            });
            
            tableCard.innerHTML = `
                <div class="font-bold text-lg mb-2 flex justify-between items-center">
                    <span>${table.name}</span>
                    <span class="text-xs bg-gray-200 dark:bg-gray-700 rounded px-2 py-1">${table.row_count} 行</span>
                </div>
                <div class="overflow-y-auto max-h-40">${columnsHtml}</div>
            `;
            
            tableList.appendChild(tableCard);
        });
        
        dbStructureContainer.appendChild(tableList);
        
    } catch (error) {
        dbStructureContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">获取数据库结构时发生错误: ${error.message}</div>`;
    }
}

// 加载表关系图谱
async function loadTableRelationships() {
    const relationshipsContainer = document.getElementById('relationships-container');
    relationshipsContainer.innerHTML = '<div class="loading p-4">加载表关系图谱...</div>';
    
    try {
        // 获取当前连接配置
        const dbConfig = getDbConfig();
        if (!dbConfig) {
            relationshipsContainer.innerHTML = '<div class="p-4 bg-red-100 text-red-700 rounded">请先配置并连接数据库</div>';
            return;
        }
        
        currentDbConfig = dbConfig;
        
        // 请求表关系数据
        const response = await fetch('/api/table-relationships', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dbConfig)
        });
        
        const result = await response.json();
        
        if (!result.success) {
            relationshipsContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">获取表关系失败: ${result.error}</div>`;
            return;
        }
        
        // 检查relationships数据
        const relationships = result.relationships;
        
        // 如果返回的是字符串而非对象
        if (typeof relationships === 'string') {
            relationshipsContainer.innerHTML = `<div class="p-4 bg-white dark:bg-gray-800 rounded shadow">
                <h2 class="text-xl font-bold mb-2">表关系信息</h2>
                <pre class="bg-gray-100 dark:bg-gray-700 p-4 rounded overflow-auto whitespace-pre-wrap">${relationships}</pre>
            </div>`;
            return;
        }
        
        // 检查是否有节点和边
        if (!relationships || !relationships.nodes || !relationships.edges) {
            relationshipsContainer.innerHTML = `<div class="p-4 bg-yellow-100 text-yellow-800 rounded">
                未找到表关系数据。数据库可能没有定义外键关系。
            </div>`;
            return;
        }
        
        // 如果没有节点或没有边，显示提示
        if (relationships.nodes.length === 0 || relationships.edges.length === 0) {
            relationshipsContainer.innerHTML = `<div class="p-4 bg-yellow-100 text-yellow-800 rounded">
                数据库没有表关系或外键约束。
            </div>`;
            return;
        }
        
        // 准备渲染关系图
        relationshipsContainer.innerHTML = '<div id="graph-container" style="height: 600px; width: 100%;"></div>';
        
        // 使用可视化库渲染关系图
        renderGraphWithVisJs(relationships, 'graph-container');
        
    } catch (error) {
        relationshipsContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">加载表关系图谱时发生错误: ${error.message}</div>`;
    }
}

// 使用vis-network渲染关系图
function renderGraphWithVisJs(graphData, containerId) {
    // 如果vis.js尚未加载，则加载它
    if (!window.vis) {
        loadScript('https://unpkg.com/vis-network/standalone/umd/vis-network.min.js', () => {
            renderGraph();
        });
    } else {
        renderGraph();
    }
    
    function renderGraph() {
        const container = document.getElementById(containerId);
        
        // 节点样式设置
        const nodes = new vis.DataSet(graphData.nodes.map(node => {
            let color = '#97C2FC';  // 默认蓝色
            let shape = 'dot';
            
            if (node.type === 'primary_key') {
                color = '#FB7E81';  // 红色
                shape = 'diamond';
            } else if (node.type === 'index') {
                color = '#7BE141';  // 绿色
                shape = 'triangle';
            } else if (node.type === 'column') {
                color = '#FFFF00';  // 黄色
                shape = 'dot';
            }
            
            return {
                id: node.id,
                label: node.label,
                size: node.size || 25,
                color: color,
                shape: shape,
                font: {
                    size: 12
                }
            };
        }));
        
        // 边样式设置
        const edges = new vis.DataSet(graphData.edges.map(edge => {
            return {
                from: edge.source,
                to: edge.target,
                label: edge.label,
                arrows: {
                    to: {
                        enabled: edge.type === 'foreign_key',
                        scaleFactor: 0.5
                    }
                },
                dashes: edge.type === 'has_column',
                color: {
                    color: edge.type === 'foreign_key' ? '#FF0000' : '#808080'
                },
                font: {
                    size: 10,
                    align: 'middle'
                }
            };
        }));
        
        // 创建网络图
        const data = { nodes, edges };
        const options = {
            physics: {
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -100,
                    centralGravity: 0.01,
                    springLength: 150,
                    springConstant: 0.08
                },
                stabilization: {
                    iterations: 100
                }
            },
            layout: {
                hierarchical: {
                    enabled: false
                }
            },
            interaction: {
                navigationButtons: true,
                hover: true
            }
        };
        
        new vis.Network(container, data, options);
    }
}

// 加载表数据进行编辑
async function loadTableData(tableName, page = 1, limit = 20) {
    const tableDataContainer = document.getElementById('table-data-container');
    tableDataContainer.innerHTML = '<div class="loading p-4">加载表数据...</div>';
    
    try {
        if (!currentDbConfig) {
            tableDataContainer.innerHTML = '<div class="p-4 bg-red-100 text-red-700 rounded">请先配置并连接数据库</div>';
            return;
        }
        
        // 请求表数据
        const response = await fetch('/api/table-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                config: currentDbConfig,
                table: tableName,
                page: page,
                limit: limit
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            tableDataContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">获取表数据失败: ${result.error}</div>`;
            return;
        }
        
        // 表格标题
        tableDataContainer.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded shadow">
                <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <h3 class="text-lg font-bold">${tableName}</h3>
                    <div>
                        <span class="text-sm text-gray-600 dark:text-gray-400">总计 ${result.total} 行</span>
                    </div>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full editable-table" id="data-table">
                        <thead class="bg-gray-100 dark:bg-gray-700">
                            <tr></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
                <div class="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center" id="pagination-controls">
                    <!-- 分页控件 -->
                </div>
            </div>
        `;
        
        const table = document.getElementById('data-table');
        const headerRow = table.querySelector('thead tr');
        
        // 表头
        let primaryKey = '';
        result.columns.forEach(column => {
            const th = document.createElement('th');
            th.className = 'px-4 py-2 text-left text-sm font-semibold';
            th.textContent = column.Field;
            
            // 判断主键
            if (column.Key === 'PRI') {
                primaryKey = column.Field;
                th.className += ' text-blue-600 dark:text-blue-400';
            }
            
            headerRow.appendChild(th);
        });
        
        // 表格数据
        const tbody = table.querySelector('tbody');
        result.data.forEach(row => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600';
            
            // 存储行数据，用于编辑
            tr.dataset.rowData = JSON.stringify(row);
            tr.dataset.primaryKey = primaryKey;
            tr.dataset.tableName = tableName;
            
            result.columns.forEach(column => {
                const td = document.createElement('td');
                td.className = 'px-4 py-2 text-sm';
                td.dataset.field = column.Field;
                
                // 如果是主键，设置为不可编辑
                if (column.Key === 'PRI') {
                    td.className += ' cursor-not-allowed bg-gray-100 dark:bg-gray-700';
                    td.dataset.editable = 'false';
                } else {
                    td.className += ' cursor-pointer';
                    td.dataset.editable = 'true';
                }
                
                td.textContent = row[column.Field] !== null ? row[column.Field] : '';
                tr.appendChild(td);
            });
            
            tbody.appendChild(tr);
        });
        
        // 添加分页控件
        const paginationControls = document.getElementById('pagination-controls');
        const totalPages = Math.ceil(result.total / limit);
        
        let paginationHtml = '<div class="flex space-x-2">';
        
        // 上一页按钮
        paginationHtml += `
            <button class="px-3 py-1 rounded ${page > 1 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500 cursor-not-allowed'}" 
                ${page > 1 ? `onclick="loadTableData('${tableName}', ${page-1}, ${limit})"` : ''}>
                上一页
            </button>
        `;
        
        // 页码按钮
        for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
            paginationHtml += `
                <button class="px-3 py-1 rounded ${i === page ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}" 
                    onclick="loadTableData('${tableName}', ${i}, ${limit})">
                    ${i}
                </button>
            `;
        }
        
        // 下一页按钮
        paginationHtml += `
            <button class="px-3 py-1 rounded ${page < totalPages ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500 cursor-not-allowed'}" 
                ${page < totalPages ? `onclick="loadTableData('${tableName}', ${page+1}, ${limit})"` : ''}>
                下一页
            </button>
        `;
        
        paginationHtml += '</div>';
        paginationControls.innerHTML = paginationHtml;
        
    } catch (error) {
        tableDataContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded">加载表数据时发生错误: ${error.message}</div>`;
    }
}

// 使表格单元格可编辑
function makeTableCellEditable(cell) {
    // 检查是否可编辑
    if (cell.dataset.editable !== 'true') return;
    
    const originalValue = cell.textContent;
    const field = cell.dataset.field;
    const row = cell.parentElement;
    const tableName = row.dataset.tableName;
    const primaryKey = row.dataset.primaryKey;
    const rowData = JSON.parse(row.dataset.rowData);
    const primaryValue = rowData[primaryKey];
    
    // 创建输入框
    cell.innerHTML = `<input type="text" class="w-full px-2 py-1 border rounded" value="${originalValue}">`;
    const input = cell.querySelector('input');
    input.focus();
    input.select();
    
    // 处理按键事件
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            saveEdit();
        } else if (e.key === 'Escape') {
            cancelEdit();
        }
    });
    
    // 处理失去焦点事件
    input.addEventListener('blur', function() {
        saveEdit();
    });
    
    // 保存编辑
    async function saveEdit() {
        const newValue = input.value;
        
        // 如果值没有变化，直接取消编辑
        if (newValue === originalValue) {
            cancelEdit();
            return;
        }
        
        // 显示加载状态
        cell.innerHTML = '<div class="loading"></div>';
        
        try {
            // 创建更新数据
            const updateData = {};
            updateData[field] = newValue;
            
            // 发送更新请求
            const response = await fetch('/api/update-row', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    config: currentDbConfig,
                    table: tableName,
                    row: updateData,
                    primary_key: primaryKey,
                    primary_value: primaryValue
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 更新成功
                cell.textContent = newValue;
                
                // 更新行数据
                rowData[field] = newValue;
                row.dataset.rowData = JSON.stringify(rowData);
                
                // 显示成功提示
                showToast('数据更新成功', 'success');
            } else {
                // 更新失败
                cell.textContent = originalValue;
                showToast(`更新失败: ${result.error}`, 'error');
            }
            
        } catch (error) {
            cell.textContent = originalValue;
            showToast(`更新时发生错误: ${error.message}`, 'error');
        }
    }
    
    // 取消编辑
    function cancelEdit() {
        cell.textContent = originalValue;
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 检查是否已有toast容器
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed top-4 right-4 z-50 flex flex-col space-y-2';
        document.body.appendChild(toastContainer);
    }
    
    // 创建新的toast
    const toast = document.createElement('div');
    toast.className = `py-2 px-4 rounded shadow-lg transform transition-all duration-300 ease-in-out opacity-0 translate-x-full`;
    
    // 根据类型设置样式
    switch (type) {
        case 'success':
            toast.className += ' bg-green-500 text-white';
            break;
        case 'error':
            toast.className += ' bg-red-500 text-white';
            break;
        case 'warning':
            toast.className += ' bg-yellow-500 text-white';
            break;
        default:
            toast.className += ' bg-blue-500 text-white';
    }
    
    toast.innerHTML = message;
    
    // 添加到容器
    toastContainer.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.classList.remove('opacity-0', 'translate-x-full');
    }, 10);
    
    // 3秒后隐藏
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-x-full');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
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

// 文档加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initDatabaseViewer();
}); 