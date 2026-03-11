// A股短线选股AI系统 - 前端应用

// 全局变量：Chart.js 实例
let stockChartInstance = null;
let currentStockCode = '';
let currentStockName = '';

// 初始化回测图表
function initBacktestCharts() {
    // 检查是否在回测标签页
    const backtestTab = document.getElementById('backtest');
    if (!backtestTab) return;

    // 加载现有总览
    loadBacktestOverview();

    // 加载新图表
    loadSuccessRateTrend();
    loadScoreDistribution();
    loadHeatmap();
}

// ==================== 股票走势查看功能 ====================

/**
 * 显示股票走势模态框
 * @param {string} stockCode - 股票代码
 * @param {string} stockName - 股票名称
 */
async function showStockChart(stockCode, stockName) {
    currentStockCode = stockCode;
    currentStockName = stockName;

    document.getElementById('modal-stock-name').textContent = stockName;
    document.getElementById('modal-stock-code').textContent = stockCode;
    document.getElementById('stock-chart-modal').style.display = 'block';
    document.getElementById('modal-overlay').style.display = 'block';

    await loadStockChartData(30);
}

/**
 * 关闭股票走势模态框
 */
function closeStockChart() {
    document.getElementById('stock-chart-modal').style.display = 'none';
    document.getElementById('modal-overlay').style.display = 'none';

    if (stockChartInstance) {
        stockChartInstance.destroy();
        stockChartInstance = null;
    }
}

/**
 * 加载股票历史数据
 * @param {number} days - 数据天数
 */
async function loadStockChartData(days) {
    const loadingEl = document.getElementById('chart-loading');
    const errorEl = document.getElementById('chart-error');

    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';

    try {
        const response = await fetch(`/charts/${currentStockCode}/history?days=${days}`);
        const data = await response.json();

        loadingEl.style.display = 'none';

        if (!data.success) {
            throw new Error(data.detail || '获取数据失败');
        }

        document.getElementById('modal-current-price').textContent = data.data.current_price;

        const changePercent = data.data.change_percent;
        const changeEl = document.getElementById('modal-change-percent');
        changeEl.textContent = `${changePercent > 0 ? '+' : ''}${changePercent}%`;
        changeEl.className = `info-value ${changePercent >= 0 ? 'positive' : 'negative'}`;

        renderStockChart(data.data.history, days);

    } catch (error) {
        loadingEl.style.display = 'none';
        errorEl.style.display = 'block';
        document.getElementById('chart-error-message').textContent = error.message;
        renderPlaceholderChart(days);
    }
}

/**
 * 渲染股票走势图表
 */
function renderStockChart(historyData, days) {
    const canvas = document.getElementById('stockChart');

    if (stockChartInstance) {
        stockChartInstance.destroy();
    }

    const dates = historyData.map(d => d.date);
    const closes = historyData.map(d => d.close);

    const ctx = canvas.getContext('2d');

    stockChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: '收盘价',
                data: closes,
                borderColor: '#2196F3',
                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                borderWidth: 2,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    callbacks: {
                        label: function(context) {
                            return '收盘价: ¥' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 10, maxRotation: 45, minRotation: 0 }
                },
                y: {
                    grid: { color: 'rgba(0, 0, 0, 0.1)' },
                    ticks: { callback: function(value) { return '¥' + value.toFixed(2); } }
                }
            }
        }
    });
}

/**
 * 渲染占位符图表
 */
function renderPlaceholderChart(days) {
    const canvas = document.getElementById('stockChart');

    if (stockChartInstance) {
        stockChartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');

    stockChartInstance = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: { x: { display: false }, y: { display: false } }
        }
    });
}

/**
 * 改变图表时间范围
 */
async function changeChartPeriod() {
    const select = document.getElementById('chart-period-select');
    const days = parseInt(select.value);
    await loadStockChartData(days);
}

class StockAnalysisApp {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
    }

    bindEvents() {
        // 标签页切换
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // 分析表单
        document.getElementById('analysis-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitAnalysis();
        });

        // 快速分析
        document.getElementById('quick-analyze').addEventListener('click', () => {
            this.quickAnalysis();
        });

        // 重置表单
        document.getElementById('reset-form').addEventListener('click', () => {
            this.resetAnalysisForm();
        });

        // 股票搜索
        document.getElementById('stock-search').addEventListener('input', (e) => {
            this.filterStocks(e.target.value);
        });

        // 刷新股票列表
        document.getElementById('refresh-stocks').addEventListener('click', () => {
            this.loadStocks();
        });

        // 缓存管理
        document.getElementById('refresh-cache').addEventListener('click', () => {
            this.loadCacheStats();
        });

        document.getElementById('clear-cache').addEventListener('click', () => {
            this.clearCache();
        });

        // 调度器控制
        document.getElementById('start-scheduler').addEventListener('click', () => {
            this.controlScheduler('start');
        });

        document.getElementById('stop-scheduler').addEventListener('click', () => {
            this.controlScheduler('stop');
        });

        document.getElementById('trigger-now').addEventListener('click', () => {
            this.triggerScheduler();
        });

        // 分析模式切换
        document.getElementById('selection-mode').addEventListener('change', (e) => {
            this.toggleAnalysisMode(e.target.value);
        });

        // 回测功能
        document.getElementById('single-backtest-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.runSingleBacktest();
        });

        document.getElementById('clear-single-result').addEventListener('click', () => {
            document.getElementById('single-backtest-result').innerHTML = '';
        });

        document.getElementById('batch-backtest-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.runBatchBacktest();
        });

        document.getElementById('clear-batch-result').addEventListener('click', () => {
            document.getElementById('batch-backtest-result').innerHTML = '';
        });

        document.getElementById('history-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.loadRecommendationHistory();
        });

        // 板块功能
        document.getElementById('refresh-sectors')?.addEventListener('click', () => {
            const sortBy = document.getElementById('sector-sort').value;
            loadSectors(sortBy);
        });

        // 排序切换
        document.getElementById('sector-sort')?.addEventListener('change', function() {
            loadSectors(this.value);
        });
    }

    switchTab(tabName) {
        // 更新标签按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 更新内容区域
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        // 加载对应标签页的数据
        this.loadTabData(tabName);
    }

    loadTabData(tabName) {
        switch (tabName) {
            case 'dashboard':
                this.loadSystemHealth();
                this.loadSystemInfo();
                break;
            case 'stocks':
                this.loadStocks();
                break;
            case 'sectors':
                loadSectors();
                break;
            case 'cache':
                this.loadCacheStats();
                break;
            case 'scheduler':
                this.loadSchedulerStatus();
                break;
            case 'backtest':
                this.loadBacktestOverview();
                break;
        }
    }

    loadInitialData() {
        this.loadSystemStatus();
        this.loadSystemHealth();
        this.loadSystemInfo();
    }

    // 系统状态检查
    async loadSystemStatus() {
        try {
            console.log('[DEBUG] Loading system status...');
            const response = await fetch('/system/health');
            console.log('[DEBUG] Response status:', response.status);
            const data = await response.json();
            console.log('[DEBUG] Health data:', data);
            console.log('[DEBUG] Status value:', data.status);
            console.log('[DEBUG] Status type:', typeof data.status);

            const statusEl = document.getElementById('system-status');
            console.log('[DEBUG] Status element found:', statusEl);

            // 更宽松的状态检查
            const isHealthy = data.status === 'healthy' ||
                             data.status === 'ok' ||
                             data.status === 'running';

            console.log('[DEBUG] Is healthy?', isHealthy);

            if (isHealthy) {
                console.log('[DEBUG] Setting status to healthy');
                statusEl.className = 'status-indicator healthy';
                statusEl.innerHTML = '<i class="fas fa-circle"></i><span>系统正常</span>';
            } else {
                console.log('[DEBUG] Setting status to unhealthy, data.status was:', data.status);
                statusEl.className = 'status-indicator unhealthy';
                statusEl.innerHTML = '<i class="fas fa-circle"></i><span>系统异常</span>';
            }

            // 添加详细的服务状态显示
            if (data.services) {
                const cacheStatus = data.services.cache_system;
                const dbStatus = data.services.database;
                console.log('[DEBUG] Cache system:', cacheStatus);
                console.log('[DEBUG] Database:', dbStatus);
            }
        } catch (error) {
            console.error('[DEBUG] Failed to load system status:', error);
            const statusEl = document.getElementById('system-status');
            if (statusEl) {
                statusEl.className = 'status-indicator unhealthy';
                statusEl.innerHTML = '<i class="fas fa-circle"></i><span>系统异常 (网络错误)</span>';
            }
        }
    }

    // 加载系统健康信息
    async loadSystemHealth() {
        try {
            const response = await fetch('/system/health');
            const data = await response.json();

            const healthEl = document.getElementById('system-health');
            const services = data.services || {};

            healthEl.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">${data.status || 'unknown'}</div>
                        <div class="stat-label">总体状态</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${services.cache_system || 'unknown'}</div>
                        <div class="stat-label">缓存系统</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${services.scheduler || 'unknown'}</div>
                        <div class="stat-label">调度器</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${services.database || 'unknown'}</div>
                        <div class="stat-label">数据库</div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Failed to load system health:', error);
            document.getElementById('system-health').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    // 加载系统信息
    async loadSystemInfo() {
        try {
            const response = await fetch('/system/info');
            const data = await response.json();

            const infoEl = document.getElementById('system-info');
            infoEl.innerHTML = `
                <div class="info-grid">
                    <div><strong>版本:</strong> ${data.version || 'N/A'}</div>
                    <div><strong>环境:</strong> ${data.environment || 'N/A'}</div>
                    <div><strong>缓存目录:</strong> ${data.cache_dir || 'N/A'}</div>
                    <div><strong>启动时间:</strong> ${data.start_time || 'N/A'}</div>
                </div>
            `;
        } catch (error) {
            console.error('Failed to load system info:', error);
            document.getElementById('system-info').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    // 快速分析
    async quickAnalysis() {
        this.showLoading(true);
        try {
            const response = await fetch('/analysis/daily', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selection_mode: 'top_n',
                    max_results: 10,
                    use_parallel: true,
                    max_workers: 4,
                    use_cache: true
                })
            });

            const data = await response.json();
            this.displayAnalysisResult(data, 'quick-result');
        } catch (error) {
            console.error('Quick analysis failed:', error);
            this.showNotification('快速分析失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 提交分析
    async submitAnalysis() {
        this.showLoading(true);
        try {
            const formData = new FormData(document.getElementById('analysis-form'));
            const selectionMode = formData.get('selection_mode');
            let maxResults = parseInt(formData.get('max_results'));

            // 检查快速模式
            const isFastMode = maxResults <= 50;

            // 全部股票模式自动限制为500只
            if (selectionMode === 'all' && maxResults > 500) {
                maxResults = 500;
                this.showNotification('注意：全部股票模式最多分析500只股票，已自动调整为500只', 'warning');
            }

            // 板块模式自动限制数量
            if (['blue_chips', 'growth_stocks', 'kechuang'].includes(selectionMode) && maxResults > 1000) {
                maxResults = Math.min(maxResults, 1000);
            }

            const data = {
                selection_mode: selectionMode,
                max_results: maxResults,
                custom_stocks: formData.get('custom_stocks') ?
                    formData.get('custom_stocks').split(',').map(s => s.trim()) : null,
                code_range_start: formData.get('code_range_start'),
                code_range_end: formData.get('code_range_end'),
                use_parallel: formData.get('use_parallel') === 'on',
                max_workers: parseInt(formData.get('max_workers')),
                batch_size: parseInt(formData.get('batch_size')),
                thread_timeout: 30,
                use_cache: true
            };

            // 显示分析配置信息
            const startTime = new Date().toLocaleTimeString();
            const configInfo = `
🚀 开始股票分析

📊 分析配置:
   模式: ${selectionMode} ${isFastMode ? '(快速模式)' : '(标准模式)'}
   股票数: ${maxResults}
   并行度: ${data.use_parallel ? data.max_workers + ' 线程' : '禁用'}
   批处理: ${data.batch_size}
   开始时间: ${startTime}

${isFastMode ? '⚡ 使用快速分析，预期耗时 10-60 秒' : '🐌 使用标准分析，预期耗时 1-10 分钟'}

请耐心等待...
            `;

            console.log(configInfo);
            this.showNotification(isFastMode ? '使用快速分析模式' : '使用标准分析模式', 'info');

            const startTimestamp = Date.now();
            const response = await fetch('/analysis/daily', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            const endTimestamp = Date.now();
            const duration = (endTimestamp - startTimestamp) / 1000;

            console.log(`分析完成，耗时 ${duration.toFixed(2)} 秒`);
            console.log('分析结果:', result);

            // 显示结果统计
            const recommendedCount = result.total_recommended || result.recommended_stocks?.length || 0;
            const analyzedCount = result.total_analyzed || 0;

            if (recommendedCount > 0) {
                this.showNotification(`分析完成！分析了 ${analyzedCount} 只股票，推荐 ${recommendedCount} 只`, 'success');
            } else {
                this.showNotification(`分析完成，但未找到符合条件的推荐股票 (分析了 ${analyzedCount} 只)`, 'warning');
            }

            this.displayAnalysisResult(result, 'analysis-result');
        } catch (error) {
            console.error('Analysis failed:', error);
            this.showNotification('分析失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 显示分析结果
    displayAnalysisResult(data, containerId) {
        const container = document.getElementById(containerId);

        if (data.error) {
            container.innerHTML = `<div class="error">分析失败: ${data.error}</div>`;
            return;
        }

        // 兼容不同返回格式
        const recommendations = data.recommendations || data.recommended_stocks || data.all_results || [];
        const analyzedCount = data.total_analyzed || 0;
        const recommendedCount = data.total_recommended || recommendations.length;

        console.log('显示结果 - 原始数据:', data);
        console.log('显示结果 - 推荐股票数:', recommendedCount);

        if (recommendations.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <p>🤔 暂无推荐结果</p>
                    <p>可能原因：</p>
                    <ul style="text-align: left; margin-top: 10px;">
                        <li>分析了 ${analyzedCount} 只股票，但都不符合推荐条件</li>
                        <li>请尝试放宽筛选条件或增加分析数量</li>
                        <li>建议使用快速模式分析 Top-N 股票</li>
                    </ul>
                    <p><strong>推荐：</strong>使用 "Top-N 快速分析" 模式</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="analysis-summary">
                <h4>✅ 分析完成</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 15px 0;">
                    <div class="stat-item">
                        <div class="stat-value">${analyzedCount}</div>
                        <div class="stat-label">分析股票</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${recommendedCount}</div>
                        <div class="stat-label">推荐股票</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${(recommendedCount/analyzedCount*100 || 0).toFixed(1)}%</div>
                        <div class="stat-label">推荐率</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.analysis_type || 'standard'}</div>
                        <div class="stat-label">分析类型</div>
                    </div>
                </div>
            </div>
        `;

        console.log('[DEBUG] ===== 开始显示分析结果 =====');
        console.log('[DEBUG] 推荐股票数组:', recommendations);
        console.log('[DEBUG] 数组长度:', recommendations.length);

        recommendations.forEach((stock, index) => {
            // 调试：打印stock对象以查看所有可用字段
            console.log(`\n[DEBUG] ===== 处理第 ${index + 1} 只股票 =====`);
            console.log(`[DEBUG] 原始stock对象:`, JSON.stringify(stock, null, 2));

            // 使用防御性编程，确保即使字段不存在也有默认值
            const stockCode = typeof stock.code !== 'undefined' ? stock.code :
                             (typeof stock.stock_code !== 'undefined' ? stock.stock_code : 'N/A');
            const stockName = typeof stock.name !== 'undefined' ? stock.name :
                             (typeof stock.stock_name !== 'undefined' ? stock.stock_name : 'N/A');
            const overallScore = typeof stock.score !== 'undefined' ? stock.score :
                                (typeof stock.overall_score !== 'undefined' ? stock.overall_score : 0);
            const reason = typeof stock.explanation !== 'undefined' ? stock.explanation :
                          (typeof stock.reason !== 'undefined' ? stock.reason : '暂无说明');

            const priceChange = typeof stock.price_change !== 'undefined' ? stock.price_change : 0;
            const technicalScore = typeof stock.technical_score !== 'undefined' ? stock.technical_score : 0;

            // 计算量比
            let volumeRatio = typeof stock.volume_ratio !== 'undefined' ? stock.volume_ratio : null;
            if (volumeRatio == null && stock.volume && stock.avg_volume && stock.avg_volume > 0) {
                volumeRatio = stock.volume / stock.avg_volume;
            }

            // 获取资金流向
            const capitalFlow = typeof stock.capital_score !== 'undefined' ? stock.capital_score :
                               (typeof stock.capital_flow !== 'undefined' ? stock.capital_flow : 0);

            console.log(`[DEBUG] 提取的字段值:`, {
                stockCode: stockCode,
                stockName: stockName,
                overallScore: overallScore,
                reason: reason,
                priceChange: priceChange,
                volumeRatio: volumeRatio,
                capitalFlow: capitalFlow,
                technicalScore: technicalScore
            });

            // 格式化显示值
            const scoreDisplay = overallScore > 0 ? overallScore.toFixed(2) : 'N/A';
            const priceChangeDisplay = priceChange > 0 || priceChange < 0 ? priceChange.toFixed(2) + '%' : 'N/A';
            const volumeRatioDisplay = volumeRatio > 0 ? volumeRatio.toFixed(2) : 'N/A';
            const capitalFlowDisplay = capitalFlow > 0 ? capitalFlow.toFixed(2) : 'N/A';
            const technicalScoreDisplay = technicalScore > 0 ? technicalScore.toFixed(2) : 'N/A';

            console.log(`[DEBUG] 格式化后的显示值:`, {
                scoreDisplay: scoreDisplay,
                priceChangeDisplay: priceChangeDisplay,
                volumeRatioDisplay: volumeRatioDisplay,
                capitalFlowDisplay: capitalFlowDisplay,
                technicalScoreDisplay: technicalScoreDisplay
            });

            console.log(`[DEBUG] 将要插入HTML的标题: #${index + 1} ${stockCode} - ${stockName}`);

            html += `
                <div class="recommendation-item">
                    <h4>#${index + 1} ${stockCode} - ${stockName}</h4>
                    <p><strong>综合评分:</strong> ${scoreDisplay}</p>
                    <p><strong>推荐理由:</strong> ${reason}</p>
                    <div class="recommendation-metrics">
                        <div class="metric">
                            <div class="metric-value">${priceChangeDisplay}</div>
                            <div class="metric-label">涨跌幅</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${volumeRatioDisplay}</div>
                            <div class="metric-label">量比</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${capitalFlowDisplay}</div>
                            <div class="metric-label">资金流向</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${technicalScoreDisplay}</div>
                            <div class="metric-label">技术分</div>
                        </div>
                    </div>
                </div>
            `;

            console.log(`[DEBUG] 第 ${index + 1} 只股票处理完成`);
        });

        console.log('[DEBUG] ===== 完成显示分析结果 =====');

        container.innerHTML = html;
        this.showNotification('分析完成', 'success');
    }

    // 重置分析表单
    resetAnalysisForm() {
        document.getElementById('analysis-form').reset();
        document.getElementById('max-results').value = 10;
        document.getElementById('max-workers').value = 0;
        document.getElementById('use-parallel').checked = true;
        this.toggleAnalysisMode('top_n');
        document.getElementById('analysis-result').innerHTML = '';
    }

    // 切换分析模式
    toggleAnalysisMode(mode) {
        const customGroup = document.getElementById('custom-stocks-group');
        const rangeGroup = document.getElementById('code-range-group');

        customGroup.style.display = mode === 'custom' ? 'block' : 'none';
        rangeGroup.style.display = mode === 'range' ? 'grid' : 'none';
    }

    // 加载股票列表
    async loadStocks() {
        try {
            const response = await fetch('/stocks/list?use_cache=true');
            const data = await response.json();

            const container = document.getElementById('stocks-list');
            let html = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>代码</th>
                            <th>名称</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            data.forEach(stock => {
                html += `
                    <tr>
                        <td>${stock.code}</td>
                        <td>${stock.name}</td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="app.analyzeStock('${stock.code}')">
                                分析
                            </button>
                            <button class="btn btn-sm btn-secondary" onclick="showStockChart('${stock.code}', '${stock.name}')">
                                <i class="fas fa-chart-line"></i> 走势
                            </button>
                        </td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            container.innerHTML = html;
            this.stocksData = data; // 保存数据用于搜索过滤
        } catch (error) {
            console.error('Failed to load stocks:', error);
            document.getElementById('stocks-list').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    // 过滤股票
    filterStocks(query) {
        if (!this.stocksData) return;

        const filtered = this.stocksData.filter(stock =>
            stock.code.includes(query) ||
            (stock.name && stock.name.includes(query))
        );

        this.displayStocks(filtered);
    }

    // 显示股票列表
    displayStocks(stocks) {
        const container = document.getElementById('stocks-list');
        let html = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>代码</th>
                        <th>名称</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
        `;

        stocks.forEach(stock => {
            html += `
                <tr>
                    <td>${stock.code}</td>
                    <td>${stock.name}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="app.analyzeStock('${stock.code}')">
                            分析
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="showStockChart('${stock.code}', '${stock.name}')">
                            <i class="fas fa-chart-line"></i> 走势
                        </button>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // 分析单个股票
    async analyzeStock(stockCode) {
        this.showLoading(true);
        try {
            const response = await fetch('/analysis/daily', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selection_mode: 'custom',
                    custom_stocks: [stockCode],
                    use_cache: true
                })
            });

            const data = await response.json();

            // 切换到分析标签页
            this.switchTab('analysis');

            // 显示结果
            this.displayAnalysisResult(data, 'analysis-result');
        } catch (error) {
            console.error('Stock analysis failed:', error);
            this.showNotification('股票分析失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 加载缓存统计
    async loadCacheStats() {
        try {
            const response = await fetch('/cache/stats');
            const data = await response.json();

            // 计算缓存记录总数
            const totalRecords = (data.daily_data_count || 0) +
                                (data.capital_flow_count || 0) +
                                (data.sentiment_count || 0);

            // 计算命中率百分比
            const hitRate = data.cache_hit_rate ? data.cache_hit_rate.toFixed(1) + '%' : '0.0%';

            const container = document.getElementById('cache-stats');
            container.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">${totalRecords.toLocaleString()}</div>
                        <div class="stat-label">缓存记录数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.db_size_mb ? data.db_size_mb.toFixed(2) + ' MB' : '0 MB'}</div>
                        <div class="stat-label">总大小</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${hitRate}</div>
                        <div class="stat-label">命中率</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.cache_hits || 0}</div>
                        <div class="stat-label">命中次数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.cache_misses || 0}</div>
                        <div class="stat-label">未命中次数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.daily_data_count || 0}</div>
                        <div class="stat-label">日线数据</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.capital_flow_count || 0}</div>
                        <div class="stat-label">资金流向</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${data.sentiment_count || 0}</div>
                        <div class="stat-label">市场情绪</div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Failed to load cache stats:', error);
            document.getElementById('cache-stats').innerHTML = '<div class="error">加载失败: ' + error.message + '</div>';
        }
    }

    // 清理缓存
    async clearCache() {
        if (!confirm('确定要清理所有缓存吗？此操作不可撤销。')) {
            return;
        }

        this.showLoading(true);
        try {
            // 注意：缓存路由没有/api前缀
            const response = await fetch('/cache/clear?confirm=true', {
                method: 'DELETE'
            });
            const data = await response.json();

            if (response.ok) {
                this.showNotification('缓存清理成功', 'success');
                this.loadCacheStats(); // 重新加载统计
            } else {
                throw new Error(data.detail || '清理失败');
            }
        } catch (error) {
            console.error('Failed to clear cache:', error);
            this.showNotification('缓存清理失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 加载调度器状态
    async loadSchedulerStatus() {
        try {
            const response = await fetch('/scheduler/status');
            const result = await response.json();

            // API返回的数据结构是 {success: true, data: {...}}
            const data = result.data || {};

            const container = document.getElementById('scheduler-status');
            const statusClass = data.is_running ? 'running' : 'stopped';

            container.innerHTML = `
                <div class="scheduler-info">
                    <p><strong>状态:</strong>
                        <span class="status-badge ${statusClass}">
                            ${data.is_running ? '运行中' : '已停止'}
                        </span>
                    </p>
                    <p><strong>任务数:</strong> ${data.task_count || 0}</p>
                    <p><strong>下次执行:</strong> ${data.next_run || 'N/A'}</p>
                </div>
            `;

            // 同时加载任务列表和日志
            this.loadSchedulerJobs();
            this.loadSchedulerLogs();
        } catch (error) {
            console.error('Failed to load scheduler status:', error);
            document.getElementById('scheduler-status').innerHTML = '<div class="error">加载失败: ' + error.message + '</div>';
        }
    }

    // 加载调度任务列表
    async loadSchedulerJobs() {
        try {
            const response = await fetch('/scheduler/jobs');
            const result = await response.json();

            const data = result.data || {};
            const jobs = data.jobs || [];

            const container = document.getElementById('scheduler-jobs-list');

            if (jobs.length === 0) {
                container.innerHTML = '<div class="no-data">暂无调度任务</div>';
                return;
            }

            let html = '<div class="jobs-list">';
            jobs.forEach(job => {
                const nextRun = job.next_run_time ? new Date(job.next_run_time).toLocaleString() : 'N/A';
                html += `
                    <div class="job-item">
                        <div class="job-info">
                            <h5>${job.name || job.id}</h5>
                            <p><strong>任务ID:</strong> ${job.id}</p>
                            <p><strong>下次执行:</strong> ${nextRun}</p>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;

        } catch (error) {
            console.error('Failed to load scheduler jobs:', error);
            document.getElementById('scheduler-jobs-list').innerHTML = '<div class="error">加载任务列表失败: ' + error.message + '</div>';
        }
    }

    // 加载调度器日志
    async loadSchedulerLogs() {
        try {
            const response = await fetch('/scheduler/logs?lines=50');
            const result = await response.json();

            const data = result.data || {};
            const logs = data.logs || [];
            const container = document.getElementById('scheduler-logs');

            if (logs.length === 0) {
                container.innerHTML = '<div class="no-data">暂无日志记录</div>';
                return;
            }

            let html = '<div class="logs-list">';
            // 显示最新的20条日志
            const recentLogs = logs.slice(0, 20).reverse();
            recentLogs.forEach(log => {
                const timestamp = new Date(log.timestamp).toLocaleString();
                const levelClass = log.level.toLowerCase();
                html += `
                    <div class="log-item log-${levelClass}">
                        <span class="log-time">${timestamp}</span>
                        <span class="log-level">${log.level}</span>
                        <span class="log-message">${log.message}</span>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;

        } catch (error) {
            console.error('Failed to load scheduler logs:', error);
            document.getElementById('scheduler-logs').innerHTML = '<div class="error">加载日志失败: ' + error.message + '</div>';
        }
    }

    // 控制调度器
    async controlScheduler(action) {
        this.showLoading(true);
        try {
            const response = await fetch(`/scheduler/${action}`, { method: 'POST' });
            const data = await response.json();

            this.showNotification(`调度器${action === 'start' ? '启动' : '停止'}成功`, 'success');
            this.loadSchedulerStatus(); // 重新加载状态
        } catch (error) {
            console.error(`Scheduler ${action} failed:`, error);
            this.showNotification(`调度器${action}失败: ` + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 触发调度器
    async triggerScheduler() {
        this.showLoading(true);
        try {
            const response = await fetch('/scheduler/manual-cache', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    stock_codes: null,  // 缓存所有股票
                    batch_size: 50,
                    max_workers: 4
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            this.showNotification('缓存任务已触发', 'success');
        } catch (error) {
            console.error('Trigger scheduler failed:', error);
            this.showNotification('触发失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 显示/隐藏加载提示
    showLoading(show) {
        document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
    }

    // 显示通知
    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        container.appendChild(notification);

        // 3秒后自动移除
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // 格式化字节数
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // =================== 回测功能 ===================

    // 加载回测总览
    async loadBacktestOverview() {
        try {
            const response = await fetch('/backtest/success-rate');
            const data = await response.json();

            const container = document.getElementById('backtest-overview');

            // 显示评分分档统计
            let scoreBucketsHtml = `
                <div class="backtest-summary">
                    <h4>按推荐评分统计</h4>
                    <div class="stats-grid">
            `;

            data.score_buckets.forEach(bucket => {
                const rateColor = bucket.success_rate >= 70 ? 'success' : bucket.success_rate >= 60 ? 'warning' : 'danger';
                scoreBucketsHtml += `
                    <div class="stat-item">
                        <div class="stat-value ${rateColor}">${bucket.success_rate.toFixed(1)}%</div>
                        <div class="stat-label">≥${bucket.min_score}分 (${bucket.count}次)</div>
                    </div>
                `;
            });

            scoreBucketsHtml += '</div></div>';

            // 显示时间窗口统计
            let timeWindowsHtml = `
                <div class="backtest-summary">
                    <h4>不同跟踪时长成功率</h4>
                    <div class="backtest-chart">
                        <div class="backtest-bar-chart">
            `;

            data.time_windows.forEach(tw => {
                const height = Math.max(tw.success_rate * 2, 10); // 最小高度10px
                timeWindowsHtml += `
                    <div class="backtest-bar" style="height: ${height}px;">
                        <div class="backtest-bar-value">${tw.success_rate.toFixed(1)}%</div>
                        <div class="backtest-bar-label">${tw.days}天</div>
                    </div>
                `;
            });

            timeWindowsHtml += '</div></div></div>';

            // 总体统计
            const overallHtml = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">${data.total_recommendations}</div>
                        <div class="stat-label">总推荐次数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value success">${data.overall_success_rate.toFixed(1)}%</div>
                        <div class="stat-label">整体成功率</div>
                    </div>
                </div>
            `;

            container.innerHTML = overallHtml + scoreBucketsHtml + timeWindowsHtml;

        } catch (error) {
            console.error('Failed to load backtest overview:', error);
            document.getElementById('backtest-overview').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    // 单只股票回测
    async runSingleBacktest() {
        this.showLoading(true);
        try {
            const stockCode = document.getElementById('backtest-stock-code').value;
            const days = parseInt(document.getElementById('backtest-days').value);
            const minScore = parseFloat(document.getElementById('backtest-min-score').value);
            const startDate = document.getElementById('backtest-start-date').value;

            const response = await fetch('/backtest/stock', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    stock_code: stockCode,
                    days_forward: days,
                    min_recommendation_score: minScore,
                    start_date: startDate || null
                })
            });

            const data = await response.json();
            this.displaySingleBacktestResult(data);

        } catch (error) {
            console.error('Single backtest failed:', error);
            this.showNotification('单股回测失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 显示单股回测结果
    displaySingleBacktestResult(data) {
        const container = document.getElementById('single-backtest-result');

        if (data.error) {
            container.innerHTML = `<div class="error">回测失败: ${data.error}</div>`;
            return;
        }

        const results = data.results || [];

        // 汇总信息
        let summaryHtml = `
            <div class="backtest-summary">
                <h4>股票 ${data.stock_code} 回测结果 (${data.days_forward}天跟踪)</h4>
                <div class="backtest-stats">
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${data.total_recommendations}</div>
                        <div class="stat-label">总推荐次数</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value ${data.success_rate >= 60 ? 'success' : 'danger'}">${data.success_rate.toFixed(1)}%</div>
                        <div class="stat-label">成功率</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value ${data.avg_return >= 0 ? 'success' : 'danger'}">${data.avg_return.toFixed(2)}%</div>
                        <div class="stat-label">平均收益</div>
                    </div>
                </div>
        `;

        // 风险指标
        if (data.risk_metrics) {
            const risk = data.risk_metrics;
            summaryHtml += `
                <h4 style="margin-top: 20px; margin-bottom: 12px; color: #0c4a6e;">风险指标</h4>
                <div class="backtest-stats">
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${(risk.sharpe_ratio || 0).toFixed(2)}</div>
                        <div class="stat-label">夏普比率</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value ${risk.max_drawdown <= 10 ? 'success' : risk.max_drawdown <= 20 ? 'warning' : 'danger'}">${(risk.max_drawdown || 0).toFixed(1)}%</div>
                        <div class="stat-label">最大回撤</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${(risk.volatility || 0).toFixed(1)}%</div>
                        <div class="stat-label">波动率</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value ${(risk.win_rate || 0) >= 60 ? 'success' : 'warning'}">${(risk.win_rate || 0).toFixed(1)}%</div>
                        <div class="stat-label">胜率</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${(risk.profit_loss_ratio || 0).toFixed(2)}</div>
                        <div class="stat-label">盈亏比</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${(risk.calmar_ratio || 0).toFixed(2)}</div>
                        <div class="stat-label">卡尔玛比率</div>
                    </div>
                </div>
            `;
        }

        summaryHtml += `
                <p style="margin-top: 12px; color: #64748b; font-size: 14px;">
                    回测期间: ${data.backtest_period.start} 至 ${data.backtest_period.end}
                </p>
            </div>
        `;

        // 详细结果
        let detailsHtml = '<div class="backtest-summary"><h4>推荐记录明细</h4>';

        results.forEach((result, index) => {
            const isProfitable = result.is_profitable;
            const returnColor = isProfitable ? 'success' : 'danger';

            detailsHtml += `
                <div class="backtest-result-item">
                    <div class="backtest-result-header">
                        <span class="backtest-result-date">${result.recommendation_date}</span>
                        <span class="backtest-result-score">${result.recommendation_score.toFixed(2)}分</span>
                    </div>
                    <div class="backtest-result-metrics">
                        <div class="backtest-metric">
                            <div class="backtest-metric-value ${returnColor}">${result.total_return.toFixed(2)}%</div>
                            <div class="backtest-metric-label">总收益</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value">${result.max_return.toFixed(2)}%</div>
                            <div class="backtest-metric-label">最高收益</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value">${result.min_return.toFixed(2)}%</div>
                            <div class="backtest-metric-label">最低收益</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value ${isProfitable ? 'success' : 'danger'}">${isProfitable ? '盈利' : '亏损'}</div>
                            <div class="backtest-metric-label">结果</div>
                        </div>
                    </div>
                    <div style="margin-top: 12px;">
                        <strong>每日变化:</strong>
                        <div style="display: flex; gap: 4px; margin-top: 8px; flex-wrap: wrap;">
            `;

            // 显示每日变化
            result.price_changes.forEach((change, dayIndex) => {
                const dayColor = change >= 0 ? 'success' : 'danger';
                detailsHtml += `<span style="font-size: 12px; color: #64748b;">D+${dayIndex + 1}: <span class="${dayColor}" style="font-weight: 600;">${change.toFixed(1)}%</span></span>`;
            });

            detailsHtml += `
                        </div>
                    </div>
                </div>
            `;
        });

        detailsHtml += '</div>';

        container.innerHTML = summaryHtml + detailsHtml;
        this.showNotification('单股回测完成', 'success');
    }

    // 批量回测
    async runBatchBacktest() {
        this.showLoading(true);
        try {
            const stockCodes = document.getElementById('batch-stock-codes').value
                .split(',')
                .map(code => code.trim())
                .filter(code => code);
            const days = parseInt(document.getElementById('batch-days').value);
            const minScore = parseFloat(document.getElementById('batch-min-score').value);

            const response = await fetch('/backtest/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    stock_codes: stockCodes,
                    days_forward: days,
                    min_recommendation_score: minScore
                })
            });

            const data = await response.json();
            this.displayBatchBacktestResult(data);

        } catch (error) {
            console.error('Batch backtest failed:', error);
            this.showNotification('批量回测失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 显示批量回测结果
    displayBatchBacktestResult(data) {
        const container = document.getElementById('batch-backtest-result');

        if (data.error) {
            container.innerHTML = `<div class="error">批量回测失败: ${data.error}</div>`;
            return;
        }

        // 汇总信息
        let summaryHtml = `
            <div class="backtest-summary">
                <h4>批量回测汇总</h4>
                <div class="backtest-stats">
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${data.total_stocks}</div>
                        <div class="stat-label">回测股票数</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${data.total_recommendations}</div>
                        <div class="stat-label">总推荐次数</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value ${data.overall_success_rate >= 60 ? 'success' : 'danger'}">${data.overall_success_rate.toFixed(1)}%</div>
                        <div class="stat-label">整体成功率</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value ${data.overall_avg_return >= 0 ? 'success' : 'danger'}">${data.overall_avg_return.toFixed(2)}%</div>
                        <div class="stat-label">整体平均收益</div>
                    </div>
                </div>
            </div>
        `;

        // 股票排行
        let rankingHtml = `
            <div class="backtest-summary">
                <h4>股票回测排行</h4>
                <div class="backtest-ranking">
                    <div class="backtest-ranking-header">
                        <div>股票代码</div>
                        <div>总推荐</div>
                        <div>成功率</div>
                        <div>平均收益</div>
                        <div>状态</div>
                    </div>
        `;

        data.stock_summaries.forEach(stock => {
            const rateClass = stock.success_rate >= 70 ? 'success' : stock.success_rate >= 50 ? 'warning' : 'danger';
            rankingHtml += `
                <div class="backtest-ranking-row">
                    <div><strong>${stock.stock_code}</strong></div>
                    <div>${stock.total_recommendations}次</div>
                    <div>${stock.success_rate.toFixed(1)}%</div>
                    <div>${stock.avg_return.toFixed(2)}%</div>
                    <div>
                        <span class="success-rate-indicator ${rateClass}">
                            <i class="fas fa-circle"></i>
                            ${rateClass === 'success' ? '优秀' : rateClass === 'warning' ? '良好' : '待改进'}
                        </span>
                    </div>
                </div>
            `;
        });

        rankingHtml += '</div></div>';

        container.innerHTML = summaryHtml + rankingHtml;
        this.showNotification('批量回测完成', 'success');
    }

    // 加载推荐历史
    async loadRecommendationHistory() {
        this.showLoading(true);
        try {
            const stockCode = document.getElementById('history-stock-code').value;
            const limit = parseInt(document.getElementById('history-limit').value);

            const response = await fetch(`/backtest/recommendation-history/${stockCode}?limit=${limit}`);
            const data = await response.json();
            this.displayRecommendationHistory(data);

        } catch (error) {
            console.error('Failed to load recommendation history:', error);
            this.showNotification('加载推荐历史失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // 显示推荐历史
    displayRecommendationHistory(data) {
        const container = document.getElementById('history-result');

        if (data.error) {
            container.innerHTML = `<div class="error">加载失败: ${data.error}</div>`;
            return;
        }

        const history = data.history || [];

        // 汇总信息
        let summaryHtml = `
            <div class="backtest-summary">
                <h4>股票 ${data.stock_code} 推荐历史</h4>
                <div class="backtest-stats">
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${data.total_recommendations}</div>
                        <div class="stat-label">总推荐次数</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${data.avg_score.toFixed(2)}</div>
                        <div class="stat-label">平均评分</div>
                    </div>
                    <div class="backtest-stat-item">
                        <div class="backtest-stat-value">${data.high_confidence_count}</div>
                        <div class="stat-label">高置信度推荐</div>
                    </div>
                </div>
            </div>
        `;

        // 历史记录
        let historyHtml = '<div class="backtest-summary"><h4>推荐记录</h4>';

        history.forEach(rec => {
            const confClass = rec.confidence >= 0.8 ? 'success' : rec.confidence >= 0.6 ? 'warning' : 'danger';

            historyHtml += `
                <div class="backtest-result-item">
                    <div class="backtest-result-header">
                        <span class="backtest-result-date">${rec.date}</span>
                        <span class="backtest-result-score">${rec.score.toFixed(2)}分</span>
                    </div>
                    <div class="backtest-result-metrics">
                        <div class="backtest-metric">
                            <div class="backtest-metric-value">${rec.recommendation_type}</div>
                            <div class="backtest-metric-label">推荐类型</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value ${confClass}">${(rec.confidence * 100).toFixed(0)}%</div>
                            <div class="backtest-metric-label">置信度</div>
                        </div>
                        <div class="backtest-metric">
                            <div class="backtest-metric-value">${rec.price_at_recommendation}</div>
                            <div class="backtest-metric-label">推荐时价格</div>
                        </div>
                    </div>
                    <div style="margin-top: 12px; color: #64748b; font-size: 14px;">
                        <strong>推荐理由:</strong> ${rec.reason}
                    </div>
                </div>
            `;
        });

        historyHtml += '</div>';

        container.innerHTML = summaryHtml + historyHtml;
        this.showNotification('推荐历史加载完成', 'success');
    }
}

// 调试函数
window.debugScheduler = async function() {
    console.log('=== 定时任务调试 ===');
    try {
        const statusDiv = document.getElementById('scheduler-debug');
        const contentDiv = document.getElementById('scheduler-debug-content');
        statusDiv.style.display = statusDiv.style.display === 'none' ? 'block' : 'none';

        if (statusDiv.style.display === 'block') {
            contentDiv.innerHTML = '<div style="color: blue;">🔄 正在测试API...</div>';

            // 测试所有调度器相关API
            const tests = [
                { name: '状态API', url: '/scheduler/status' },
                { name: '任务列表API', url: '/scheduler/jobs' },
                { name: '日志API', url: '/scheduler/logs?lines=5' },
                { name: '配置API', url: '/scheduler/config' }
            ];

            let html = '<div style="font-family: monospace; font-size: 12px;">';
            for (const test of tests) {
                try {
                    const response = await fetch(test.url);
                    const result = await response.json();
                    const status = response.ok ? '✅' : '❌';
                    html += `<div>${status} ${test.name}: ${response.status}</div>`;
                    if (result.success) {
                        html += `<pre style="background: #f5f5f5; padding: 10px; margin: 5px 0; border-radius: 4px;">${JSON.stringify(result.data, null, 2)}</pre>`;
                    } else {
                        html += `<div style="color: red;">❌ 错误: ${JSON.stringify(result)}</div>`;
                    }
                } catch (error) {
                    html += `<div>❌ ${test.name}: ${error.message}</div>`;
                }
            }
            html += '</div>';
            contentDiv.innerHTML = html;
            console.log('调试完成');
        }
    } catch (error) {
        console.error('调试失败:', error);
        document.getElementById('scheduler-debug-content').innerHTML = `<div style="color: red;">❌ 调试失败: ${error.message}</div>`;
    }
};

/**
 * 加载回测总览
 */
async function loadBacktestOverview() {
    try {
        const container = document.getElementById('backtest-overview');
        if (!container) return;

        const response = await fetch('/backtest/success-rate');
        const result = await response.json();

        if (!result) {
            container.innerHTML = '<div class="error">无法加载回测统计</div>';
            return;
        }

        const { overall_success_rate, total_recommendations, time_windows, score_buckets } = result;

        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${overall_success_rate.toFixed(1)}%</div>
                    <div class="stat-label">总体成功率</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${total_recommendations}</div>
                    <div class="stat-label">总推荐数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${time_windows?.[0]?.success_rate?.toFixed(1) || '0.0'}%</div>
                    <div class="stat-label">1日成功率</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${time_windows?.[2]?.success_rate?.toFixed(1) || '0.0'}%</div>
                    <div class="stat-label">5日成功率</div>
                </div>
            </div>
            <div class="chart-note">基于历史回测数据统计</div>
        `;
    } catch (error) {
        console.error('加载回测总览失败:', error);
        const container = document.getElementById('backtest-overview');
        if (container) {
            container.innerHTML = '<div class="error">加载失败: ' + error.message + '</div>';
        }
    }
}

// ==================== 回测可视化增强 ====================

/**
 * 加载回测成功率趋势图
 */
async function loadSuccessRateTrend() {
    try {
        const days = document.getElementById('trend-days')?.value || 30;
        const interval = document.getElementById('trend-interval')?.value || 'daily';
        const response = await fetch(`/backtest/success-rate-trend?days=${days}&interval=${interval}`);
        const result = await response.json();

        if (!result.success || !result.data) {
            console.warn('暂无趋势数据');
            return;
        }

        renderTrendChart(result.data);
    } catch (error) {
        console.error('加载成功率趋势失败:', error);
    }
}

/**
 * 渲染趋势图
 */
function renderTrendChart(data) {
    const container = document.getElementById('trend-chart');
    if (!container) return;

    const { dates, success_rates, recommendation_counts } = data;

    // 简单的SVG折线图
    const width = 800;
    const height = 300;
    const padding = 40;

    const maxRate = Math.max(...success_rates, 100);
    const minRate = Math.min(...success_rates, 0);
    const yScale = (height - 2 * padding) / (maxRate - minRate || 1);
    const xStep = (width - 2 * padding) / (dates.length - 1 || 1);

    // 生成路径
    let pathD = '';
    success_rates.forEach((rate, i) => {
        const x = padding + i * xStep;
        const y = height - padding - (rate - minRate) * yScale;
        pathD += (i === 0 ? 'M' : 'L') + `${x},${y}`;
    });

    // 生成柱状图（推荐数量）
    let barsHtml = '';
    const maxCount = Math.max(...recommendation_counts, 1);
    const barWidth = xStep * 0.6;
    recommendation_counts.forEach((count, i) => {
        const x = padding + i * xStep - barWidth / 2;
        const barHeight = (count / maxCount) * (height - 2 * padding) * 0.3;
        const y = height - padding - barHeight;
        barsHtml += `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="rgba(100,181,246,0.3)" rx="2"/>`;
    });

    container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" class="trend-svg">
            <!-- 网格线 -->
            <g class="grid">
                ${[0, 25, 50, 75, 100].map(val => {
                    const y = height - padding - (val - minRate) * yScale;
                    return `<line x1="${padding}" y1="${y}" x2="${width-padding}" y2="${y}" stroke="#e0e0e0" stroke-dasharray="3,3"/>`;
                }).join('')}
            </g>

            <!-- 柱状图（推荐数量） -->
            <g class="bars">${barsHtml}</g>

            <!-- 成功率折线 -->
            <path d="${pathD}" fill="none" stroke="#4CAF50" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>

            <!-- 数据点 -->
            ${success_rates.map((rate, i) => {
                const x = padding + i * xStep;
                const y = height - padding - (rate - minRate) * yScale;
                return `<circle cx="${x}" cy="${y}" r="4" fill="#4CAF50" class="data-point"
                    data-rate="${rate}" data-date="${dates[i]}" data-count="${recommendation_counts[i]}"/>`;
            }).join('')}

            <!-- Y轴标签 -->
            <text x="${padding-10}" y="${height-padding+5}" text-anchor="end" font-size="12">${minRate}%</text>
            <text x="${padding-10}" y="${padding+5}" text-anchor="end" font-size="12">${maxRate}%</text>

            <!-- X轴标签（只显示部分） -->
            ${dates.filter((_, i) => i % 5 === 0).map((date, i) => {
                const idx = dates.indexOf(date);
                const x = padding + idx * xStep;
                return `<text x="${x}" y="${height-padding+20}" text-anchor="middle" font-size="10">${date.slice(5)}</text>`;
            }).join('')}
        </svg>

        <div class="trend-legend">
            <span class="legend-item"><span class="legend-color" style="background:#4CAF50"></span>成功率</span>
            <span class="legend-item"><span class="legend-color" style="background:rgba(100,181,246,0.5)"></span>推荐数量</span>
        </div>
    `;
}

/**
 * 渲染评分分布图
 */
async function loadScoreDistribution() {
    try {
        const response = await fetch('/backtest/score-distribution');
        const result = await response.json();

        if (!result.success || !result.data) return;

        renderScoreChart(result.data);
    } catch (error) {
        console.error('加载评分分布失败:', error);
    }
}

function renderScoreChart(data) {
    const container = document.getElementById('score-chart');
    if (!container) return;

    const { score_ranges, success_rates, counts, colors } = data;

    // 水平条形图
    const maxRate = Math.max(...success_rates, 100);

    container.innerHTML = `
        <div class="score-distribution">
            ${score_ranges.map((range, i) => `
                <div class="score-row">
                    <div class="score-label">${range}分</div>
                    <div class="score-bar-container">
                        <div class="score-bar" style="width: ${success_rates[i]}%; background: ${colors[i]}">
                            <span class="score-value">${success_rates[i]}%</span>
                        </div>
                    </div>
                    <div class="score-count">${counts[i]}次</div>
                </div>
            `).join('')}
        </div>
        <p class="chart-note">不同评分区间的成功率分布</p>
    `;
}

/**
 * 渲染热力图
 */
async function loadHeatmap() {
    try {
        const response = await fetch('/backtest/heatmap');
        const result = await response.json();

        if (!result.success || !result.data) return;

        renderHeatmapChart(result.data);
    } catch (error) {
        console.error('加载热力图失败:', error);
    }
}

function renderHeatmapChart(data) {
    const container = document.getElementById('heatmap-chart');
    if (!container) return;

    const { weekdays, hours, heatmap } = data;

    // 根据成功率获取颜色
    const getHeatColor = (rate) => {
        if (rate >= 70) return '#4CAF50';
        if (rate >= 60) return '#8BC34A';
        if (rate >= 50) return '#FFC107';
        if (rate >= 40) return '#FF9800';
        return '#F44336';
    };

    container.innerHTML = `
        <table class="heatmap-table">
            <thead>
                <tr>
                    <th></th>
                    ${hours.map(h => `<th>${h}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${weekdays.map((day, i) => `
                    <tr>
                        <td class="weekday-label">${day}</td>
                        ${hours.map((_, j) => `
                            <td class="heatmap-cell" style="background: ${getHeatColor(heatmap[i][j])}"
                                title="${day} ${hours[j]}: ${heatmap[i][j]}%">
                                ${heatmap[i][j]}%
                            </td>
                        `).join('')}
                    </tr>
                `).join('')}
            </tbody>
        </table>
        <div class="heatmap-legend">
            <span style="background:#F44336"><40%</span>
            <span style="background:#FF9800">40-50%</span>
            <span style="background:#FFC107">50-60%</span>
            <span style="background:#8BC34A">60-70%</span>
            <span style="background:#4CAF50">≥70%</span>
        </div>
    `;
}

// ==================== 板块功能 ====================

/**
 * 加载热门板块
 */
async function loadSectors(sortBy = 'heat') {
    const grid = document.getElementById('sectors-grid');
    grid.innerHTML = '<div class="loading">正在加载板块数据...</div>';

    try {
        const response = await fetch(`/api/sector/list?limit=50&sort_by=${sortBy}`);
        const result = await response.json();

        if (!result.success) {
            grid.innerHTML = `<div class="error">加载失败: ${result.error}</div>`;
            return;
        }

        renderSectors(result.data);
    } catch (error) {
        grid.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

/**
 * 渲染板块卡片
 */
function renderSectors(sectors) {
    const grid = document.getElementById('sectors-grid');

    if (sectors.length === 0) {
        grid.innerHTML = '<div class="no-data">暂无板块数据</div>';
        return;
    }

    grid.innerHTML = sectors.map(sector => {
        const heatClass = getHeatClass(sector.heat);
        const changeClass = sector.change >= 0 ? 'positive' : 'negative';
        const changeSign = sector.change >= 0 ? '+' : '';

        return `
            <div class="sector-card ${heatClass}"
                 onclick="analyzeSector('${sector.code}', '${sector.name}')"
                 data-code="${sector.code}">
                <div class="sector-name">
                    <span>${sector.name}</span>
                    <span class="heat-badge ${heatClass}">${sector.heat_level}</span>
                </div>
                <div class="sector-stats">
                    <div class="sector-change ${changeClass}">
                        涨跌: ${changeSign}${sector.change.toFixed(2)}%
                    </div>
                    <div>成交额: ${formatAmount(sector.amount)}</div>
                    <div>领涨: ${sector.lead_stock} (${sector.lead_stock_change >= 0 ? '+' : ''}${sector.lead_stock_change.toFixed(2)}%)</div>
                </div>
                <div class="heat-bar">
                    <div class="heat-bar-fill" style="width: ${sector.heat}%; background: ${sector.heat_color}"></div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 获取热度样式类
 */
function getHeatClass(heat) {
    if (heat >= 80) return 'super';
    if (heat >= 60) return 'hot';
    if (heat >= 40) return 'warm';
    if (heat >= 20) return 'cold';
    return 'frozen';
}

/**
 * 格式化金额
 */
function formatAmount(amount) {
    if (amount >= 1e8) {
        return (amount / 1e8).toFixed(2) + '亿';
    } else if (amount >= 1e4) {
        return (amount / 1e4).toFixed(2) + '万';
    }
    return amount.toFixed(2);
}

/**
 * 分析板块股票
 */
async function analyzeSector(sectorCode, sectorName) {
    // 显示分析区域
    const analysisCard = document.getElementById('sector-analysis');
    const resultDiv = document.getElementById('sector-stocks-result');
    const nameSpan = document.getElementById('sector-name');

    nameSpan.textContent = `- ${sectorName}`;
    analysisCard.style.display = 'block';
    resultDiv.innerHTML = '<div class="loading">正在分析板块股票...</div>';

    // 滚动到分析区域
    analysisCard.scrollIntoView({ behavior: 'smooth' });

    try {
        // 先获取板块股票列表
        const detailResponse = await fetch(`/api/sector/${sectorCode}`);
        const detail = await detailResponse.json();

        if (!detail.success || detail.stocks.length === 0) {
            resultDiv.innerHTML = `<div class="error">该板块无股票数据</div>`;
            return;
        }

        // 调用分析接口
        const stockCodes = detail.stocks.slice(0, 30).join(',');  // 最多分析30只
        const analysisResponse = await fetch(`/api/analysis/custom?stock_codes=${stockCodes}&use_parallel=true`);
        const analysis = await analysisResponse.json();

        renderSectorAnalysis(sectorName, analysis);

    } catch (error) {
        resultDiv.innerHTML = `<div class="error">分析失败: ${error.message}</div>`;
    }
}

/**
 * 渲染板块分析结果
 */
function renderSectorAnalysis(sectorName, analysis) {
    const resultDiv = document.getElementById('sector-stocks-result');

    const stocks = analysis.recommended_stocks || analysis.all_results || [];

    if (stocks.length === 0) {
        resultDiv.innerHTML = '<div class="no-data">该板块暂无推荐股票</div>';
        return;
    }

    const html = `
        <div class="sector-summary">
            <p>分析了 ${analysis.total_analyzed || stocks.length} 只股票，推荐 ${stocks.length} 只</p>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>代码</th>
                    <th>名称</th>
                    <th>评分</th>
                    <th>建议</th>
                    <th>价格</th>
                    <th>涨跌%</th>
                    <th>量比</th>
                </tr>
            </thead>
            <tbody>
                ${stocks.map(stock => `
                    <tr>
                        <td>${stock.code}</td>
                        <td>${stock.name}</td>
                        <td><span class="score">${stock.score.toFixed(1)}</span></td>
                        <td><span class="recommendation ${stock.recommendation.toLowerCase()}">${stock.recommendation}</span></td>
                        <td>${stock.price.toFixed(2)}</td>
                        <td class="${stock.price_change >= 0 ? 'positive' : 'negative'}">${stock.price_change >= 0 ? '+' : ''}${stock.price_change.toFixed(2)}%</td>
                        <td>${stock.volume_ratio.toFixed(2)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    resultDiv.innerHTML = html;
}

// 初始化应用
const app = new StockAnalysisApp();

// 延迟初始化回测图表（等待页面完全加载）
setTimeout(initBacktestCharts, 500);