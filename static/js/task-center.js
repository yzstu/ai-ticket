/**
 * 任务中心管理模块
 * 处理异步任务的创建、监控和管理
 */

class TaskCenter {
    constructor() {
        this.ws = null;
        this.clientId = this.generateClientId();
        this.runningTasks = new Map();
        this.taskHistory = [];
        this.refreshInterval = null;
        this.init();
    }

    /**
     * 初始化任务中心
     */
    init() {
        this.bindEvents();
        this.loadTaskStatistics();
        this.loadRunningTasks();
        this.loadTaskHistory();
        this.initWebSocket();
        this.startAutoRefresh();
    }

    /**
     * 生成客户端ID
     */
    generateClientId() {
        return 'client-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 快速创建任务按钮
        document.getElementById('create-analysis-task')?.addEventListener('click', () => {
            this.showCreateAnalysisDialog();
        });

        document.getElementById('create-backtest-task')?.addEventListener('click', () => {
            this.showCreateBacktestDialog();
        });

        document.getElementById('create-cache-task')?.addEventListener('click', () => {
            this.showCreateCacheDialog();
        });

        document.getElementById('create-sector-task')?.addEventListener('click', () => {
            this.showCreateSectorDialog();
        });

        // 刷新按钮
        document.getElementById('refresh-running-tasks')?.addEventListener('click', () => {
            this.loadRunningTasks();
        });

        document.getElementById('refresh-task-history')?.addEventListener('click', () => {
            this.loadTaskHistory();
        });
    }

    /**
     * 初始化WebSocket连接
     */
    initWebSocket() {
        try {
            const wsUrl = `ws://${window.location.host}/ws/tasks/${this.clientId}`;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                // 尝试重连
                setTimeout(() => this.initWebSocket(), 5000);
            };
        } catch (error) {
            console.error('Failed to init WebSocket:', error);
        }
    }

    /**
     * 处理WebSocket消息
     */
    handleWebSocketMessage(data) {
        if (data.type === 'task_progress') {
            this.updateTaskProgress(data.data);
        } else if (data.type === 'subscribed') {
            console.log('Subscribed to task:', data.task_id);
        }
    }

    /**
     * 更新任务进度
     */
    updateTaskProgress(progress) {
        const taskId = progress.task_id;
        const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);

        if (taskCard) {
            // 更新进度条
            const progressBar = taskCard.querySelector('.task-progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress.progress_percent}%`;
            }

            // 更新进度文本
            const progressText = taskCard.querySelector('.task-progress-text');
            if (progressText) {
                progressText.textContent = `${progress.progress_percent.toFixed(1)}%`;
            }

            // 更新当前项
            const currentItem = taskCard.querySelector('.task-current-item');
            if (currentItem) {
                currentItem.textContent = progress.current_item || '处理中...';
            }

            // 更新任务状态
            if (progress.status) {
                const statusBadge = taskCard.querySelector('.task-status');
                if (statusBadge) {
                    statusBadge.textContent = progress.status;
                    statusBadge.className = `task-status status-${progress.status.toLowerCase()}`;
                }
            }
        }

        // 更新统计信息
        this.loadTaskStatistics();
    }

    /**
     * 显示创建分析任务对话框
     */
    showCreateAnalysisDialog() {
        const html = `
            <div class="task-dialog">
                <h3><i class="fas fa-brain"></i> 创建股票分析任务</h3>
                <form id="create-analysis-form">
                    <div class="form-group">
                        <label>选择模式</label>
                        <select name="selection_mode" required>
                            <option value="top_n">Top-N</option>
                            <option value="custom">自定义</option>
                            <option value="range">代码范围</option>
                            <option value="all">全部股票</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>最大结果数</label>
                        <input type="number" name="max_results" value="20" min="1" max="100" required>
                    </div>
                    <div class="form-group">
                        <label>使用并行分析</label>
                        <select name="use_parallel">
                            <option value="true">是</option>
                            <option value="false">否</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>任务名称</label>
                        <input type="text" name="task_name" placeholder="自定义任务名称（可选）">
                    </div>
                    <div class="dialog-actions">
                        <button type="button" class="btn btn-secondary" onclick="taskCenter.closeDialog()">取消</button>
                        <button type="submit" class="btn btn-primary">创建并启动</button>
                    </div>
                </form>
            </div>
        `;
        this.showDialog(html, (form) => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const params = Object.fromEntries(formData.entries());

                // 转换数据类型
                params.max_results = parseInt(params.max_results);
                params.use_parallel = params.use_parallel === 'true';

                try {
                    const response = await fetch('/tasks/create-analysis', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(params)
                    });
                    const result = await response.json();

                    if (result.success) {
                        this.showNotification('分析任务创建成功', 'success');
                        this.closeDialog();
                        this.loadRunningTasks();
                        this.loadTaskHistory();
                    } else {
                        this.showNotification('创建任务失败', 'error');
                    }
                } catch (error) {
                    console.error('Create task error:', error);
                    this.showNotification('创建任务时发生错误', 'error');
                }
            });
        });
    }

    /**
     * 显示创建回测任务对话框
     */
    showCreateBacktestDialog() {
        const html = `
            <div class="task-dialog">
                <h3><i class="fas fa-chart-area"></i> 创建批量回测任务</h3>
                <form id="create-backtest-form">
                    <div class="form-group">
                        <label>股票列表</label>
                        <textarea name="stocks" rows="5" placeholder="输入股票代码，每行一个&#10;例如：&#10;600519&#10;000001&#10;600036" required></textarea>
                    </div>
                    <div class="form-group">
                        <label>开始日期</label>
                        <input type="date" name="start_date" required>
                    </div>
                    <div class="form-group">
                        <label>结束日期</label>
                        <input type="date" name="end_date" required>
                    </div>
                    <div class="form-group">
                        <label>初始资金</label>
                        <input type="number" name="initial_capital" value="100000" min="1000" step="1000" required>
                    </div>
                    <div class="dialog-actions">
                        <button type="button" class="btn btn-secondary" onclick="taskCenter.closeDialog()">取消</button>
                        <button type="submit" class="btn btn-primary">创建并启动</button>
                    </div>
                </form>
            </div>
        `;
        this.showDialog(html, (form) => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const params = Object.fromEntries(formData.entries());

                // 转换股票列表
                params.stocks = params.stocks.split('\n').map(s => s.trim()).filter(s => s);
                params.initial_capital = parseFloat(params.initial_capital);

                try {
                    const response = await fetch('/tasks/create-backtest', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(params)
                    });
                    const result = await response.json();

                    if (result.success) {
                        this.showNotification('回测任务创建成功', 'success');
                        this.closeDialog();
                        this.loadRunningTasks();
                        this.loadTaskHistory();
                    } else {
                        this.showNotification('创建任务失败', 'error');
                    }
                } catch (error) {
                    console.error('Create task error:', error);
                    this.showNotification('创建任务时发生错误', 'error');
                }
            });
        });
    }

    /**
     * 显示创建缓存任务对话框
     */
    showCreateCacheDialog() {
        const html = `
            <div class="task-dialog">
                <h3><i class="fas fa-database"></i> 创建缓存预加载任务</h3>
                <form id="create-cache-form">
                    <div class="form-group">
                        <label>股票列表</label>
                        <textarea name="stocks" rows="5" placeholder="输入股票代码，每行一个&#10;例如：&#10;600519&#10;000001&#10;600036" required></textarea>
                    </div>
                    <div class="form-group">
                        <label>缓存目录</label>
                        <input type="text" name="cache_dir" value="./cache">
                    </div>
                    <div class="dialog-actions">
                        <button type="button" class="btn btn-secondary" onclick="taskCenter.closeDialog()">取消</button>
                        <button type="submit" class="btn btn-primary">创建并启动</button>
                    </div>
                </form>
            </div>
        `;
        this.showDialog(html, (form) => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const params = Object.fromEntries(formData.entries());

                // 转换股票列表
                params.stocks = params.stocks.split('\n').map(s => s.trim()).filter(s => s);

                try {
                    const response = await fetch('/tasks/create-cache', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(params)
                    });
                    const result = await response.json();

                    if (result.success) {
                        this.showNotification('缓存任务创建成功', 'success');
                        this.closeDialog();
                        this.loadRunningTasks();
                        this.loadTaskHistory();
                    } else {
                        this.showNotification('创建任务失败', 'error');
                    }
                } catch (error) {
                    console.error('Create task error:', error);
                    this.showNotification('创建任务时发生错误', 'error');
                }
            });
        });
    }

    /**
     * 显示创建板块任务对话框
     */
    showCreateSectorDialog() {
        const html = `
            <div class="task-dialog">
                <h3><i class="fas fa-layer-group"></i> 创建板块分析任务</h3>
                <form id="create-sector-form">
                    <div class="form-group">
                        <label>板块名称</label>
                        <input type="text" name="sector_name" placeholder="例如：科技板块" required>
                    </div>
                    <div class="form-group">
                        <label>股票列表</label>
                        <textarea name="stocks" rows="5" placeholder="输入股票代码，每行一个&#10;例如：&#10;600519&#10;000001&#10;600036" required></textarea>
                    </div>
                    <div class="dialog-actions">
                        <button type="button" class="btn btn-secondary" onclick="taskCenter.closeDialog()">取消</button>
                        <button type="submit" class="btn btn-primary">创建并启动</button>
                    </div>
                </form>
            </div>
        `;
        this.showDialog(html, (form) => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const params = Object.fromEntries(formData.entries());

                // 转换股票列表
                params.stocks = params.stocks.split('\n').map(s => s.trim()).filter(s => s);

                try {
                    const response = await fetch('/tasks/create-sector', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(params)
                    });
                    const result = await response.json();

                    if (result.success) {
                        this.showNotification('板块任务创建成功', 'success');
                        this.closeDialog();
                        this.loadRunningTasks();
                        this.loadTaskHistory();
                    } else {
                        this.showNotification('创建任务失败', 'error');
                    }
                } catch (error) {
                    console.error('Create task error:', error);
                    this.showNotification('创建任务时发生错误', 'error');
                }
            });
        });
    }

    /**
     * 显示对话框
     */
    showDialog(html, onSubmit) {
        const dialog = document.createElement('div');
        dialog.className = 'dialog-overlay';
        dialog.innerHTML = html;
        document.body.appendChild(dialog);

        const form = dialog.querySelector('form');
        if (form && onSubmit) {
            onSubmit(form);
        }
    }

    /**
     * 关闭对话框
     */
    closeDialog() {
        const dialog = document.querySelector('.dialog-overlay');
        if (dialog) {
            dialog.remove();
        }
    }

    /**
     * 显示通知
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * 加载任务统计信息
     */
    async loadTaskStatistics() {
        try {
            const response = await fetch('/tasks/statistics');
            const result = await response.json();

            const html = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">${result.total_tasks || 0}</div>
                        <div class="stat-label">总任务数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${result.running_tasks || 0}</div>
                        <div class="stat-label">运行中</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${result.completed_tasks || 0}</div>
                        <div class="stat-label">已完成</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${(result.success_rate || 0).toFixed(1)}%</div>
                        <div class="stat-label">成功率</div>
                    </div>
                </div>
            `;

            document.getElementById('task-statistics').innerHTML = html;
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }

    /**
     * 加载运行中的任务
     */
    async loadRunningTasks() {
        try {
            const response = await fetch('/tasks/running');
            const tasks = await response.json();

            if (tasks.length === 0) {
                document.getElementById('running-tasks-list').innerHTML =
                    '<div class="empty-message">暂无运行中的任务</div>';
                return;
            }

            const html = tasks.map(task => this.renderTaskCard(task, true)).join('');
            document.getElementById('running-tasks-list').innerHTML = html;

            // 绑定任务操作事件
            tasks.forEach(task => {
                this.bindTaskActions(task.task_id);
            });
        } catch (error) {
            console.error('Failed to load running tasks:', error);
        }
    }

    /**
     * 加载任务历史
     */
    async loadTaskHistory() {
        try {
            const response = await fetch('/tasks?limit=50');
            const tasks = await response.json();

            this.taskHistory = tasks;

            if (tasks.length === 0) {
                document.getElementById('task-history-list').innerHTML =
                    '<div class="empty-message">暂无任务历史</div>';
                return;
            }

            const html = tasks.map(task => this.renderTaskCard(task, false)).join('');
            document.getElementById('task-history-list').innerHTML = html;

            // 绑定任务操作事件
            tasks.forEach(task => {
                this.bindTaskActions(task.task_id);
            });
        } catch (error) {
            console.error('Failed to load task history:', error);
        }
    }

    /**
     * 渲染任务卡片
     */
    renderTaskCard(task, showProgress = false) {
        const statusClass = `status-${task.status.toLowerCase()}`;
        const progressPercent = task.progress_percent || 0;

        return `
            <div class="task-card ${statusClass}" data-task-id="${task.task_id}">
                <div class="task-header">
                    <div class="task-title">
                        <i class="fas fa-${this.getTaskTypeIcon(task.task_type)}"></i>
                        <span>${task.task_name}</span>
                    </div>
                    <div class="task-status ${statusClass}">${task.status}</div>
                </div>

                <div class="task-info">
                    <div class="task-info-item">
                        <i class="fas fa-hashtag"></i>
                        <span>ID: ${task.task_id.substr(0, 8)}...</span>
                    </div>
                    <div class="task-info-item">
                        <i class="fas fa-clock"></i>
                        <span>创建时间: ${new Date(task.created_at).toLocaleString()}</span>
                    </div>
                    ${task.started_at ? `
                    <div class="task-info-item">
                        <i class="fas fa-play"></i>
                        <span>开始时间: ${new Date(task.started_at).toLocaleString()}</span>
                    </div>
                    ` : ''}
                </div>

                ${showProgress ? `
                <div class="task-progress">
                    <div class="task-progress-bar" style="width: ${progressPercent}%"></div>
                    <div class="task-progress-text">${progressPercent.toFixed(1)}%</div>
                </div>
                <div class="task-current-item">
                    <i class="fas fa-cog fa-spin"></i>
                    <span>${task.current_item || '准备中...'}</span>
                </div>
                ` : ''}

                <div class="task-actions">
                    ${task.status === 'RUNNING' ? `
                        <button class="btn btn-sm btn-warning" onclick="taskCenter.pauseTask('${task.task_id}')">
                            <i class="fas fa-pause"></i> 暂停
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="taskCenter.cancelTask('${task.task_id}')">
                            <i class="fas fa-stop"></i> 取消
                        </button>
                    ` : ''}
                    ${task.status === 'PAUSED' ? `
                        <button class="btn btn-sm btn-success" onclick="taskCenter.resumeTask('${task.task_id}')">
                            <i class="fas fa-play"></i> 恢复
                        </button>
                    ` : ''}
                    ${task.status === 'FAILED' ? `
                        <button class="btn btn-sm btn-primary" onclick="taskCenter.retryTask('${task.task_id}')">
                            <i class="fas fa-redo"></i> 重试
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-info" onclick="taskCenter.viewTaskDetails('${task.task_id}')">
                        <i class="fas fa-eye"></i> 详情
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * 获取任务类型图标
     */
    getTaskTypeIcon(taskType) {
        const icons = {
            'analysis_daily': 'brain',
            'backtest_batch': 'chart-area',
            'scheduler_cache': 'database',
            'sector_analyze': 'layer-group'
        };
        return icons[taskType] || 'task';
    }

    /**
     * 绑定任务操作事件
     */
    bindTaskActions(taskId) {
        // 事件绑定在HTML中通过onclick实现
    }

    /**
     * 暂停任务
     */
    async pauseTask(taskId) {
        try {
            const response = await fetch(`/tasks/${taskId}/pause`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification('任务已暂停', 'success');
                this.loadRunningTasks();
            } else {
                this.showNotification('暂停任务失败', 'error');
            }
        } catch (error) {
            console.error('Pause task error:', error);
            this.showNotification('暂停任务时发生错误', 'error');
        }
    }

    /**
     * 恢复任务
     */
    async resumeTask(taskId) {
        try {
            const response = await fetch(`/tasks/${taskId}/resume`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification('任务已恢复', 'success');
                this.loadRunningTasks();
            } else {
                this.showNotification('恢复任务失败', 'error');
            }
        } catch (error) {
            console.error('Resume task error:', error);
            this.showNotification('恢复任务时发生错误', 'error');
        }
    }

    /**
     * 取消任务
     */
    async cancelTask(taskId) {
        if (!confirm('确定要取消这个任务吗？')) {
            return;
        }

        try {
            const response = await fetch(`/tasks/${taskId}/cancel`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification('任务已取消', 'success');
                this.loadRunningTasks();
                this.loadTaskHistory();
            } else {
                this.showNotification('取消任务失败', 'error');
            }
        } catch (error) {
            console.error('Cancel task error:', error);
            this.showNotification('取消任务时发生错误', 'error');
        }
    }

    /**
     * 重试任务
     */
    async retryTask(taskId) {
        try {
            const response = await fetch(`/tasks/${taskId}/retry`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification('任务重试已启动', 'success');
                this.loadTaskHistory();
            } else {
                this.showNotification('重试任务失败', 'error');
            }
        } catch (error) {
            console.error('Retry task error:', error);
            this.showNotification('重试任务时发生错误', 'error');
        }
    }

    /**
     * 查看任务详情
     */
    async viewTaskDetails(taskId) {
        try {
            const response = await fetch(`/tasks/${taskId}`);
            const task = await response.json();

            // 生成跳转链接
            const jumpLinks = this.generateJumpLinks(task);

            const html = `
                <div class="task-dialog">
                    <h3><i class="fas fa-info-circle"></i> 任务详情</h3>
                    <div class="task-details">
                        <div class="detail-item">
                            <label>任务ID:</label>
                            <span>${task.task_id}</span>
                        </div>
                        <div class="detail-item">
                            <label>任务名称:</label>
                            <span>${task.task_name}</span>
                        </div>
                        <div class="detail-item">
                            <label>任务类型:</label>
                            <span>${task.task_type}</span>
                        </div>
                        <div class="detail-item">
                            <label>状态:</label>
                            <span class="task-status status-${task.status.toLowerCase()}">${task.status}</span>
                        </div>
                        <div class="detail-item">
                            <label>创建时间:</label>
                            <span>${new Date(task.created_at).toLocaleString()}</span>
                        </div>
                        ${task.started_at ? `
                        <div class="detail-item">
                            <label>开始时间:</label>
                            <span>${new Date(task.started_at).toLocaleString()}</span>
                        </div>
                        ` : ''}
                        ${task.completed_at ? `
                        <div class="detail-item">
                            <label>完成时间:</label>
                            <span>${new Date(task.completed_at).toLocaleString()}</span>
                        </div>
                        ` : ''}
                        <div class="detail-item">
                            <label>进度:</label>
                            <span>${task.progress_percent?.toFixed(1) || 0}% (${task.completed_items || 0}/${task.total_items || 0})</span>
                        </div>
                        ${task.error_message ? `
                        <div class="detail-item">
                            <label>错误信息:</label>
                            <span class="error-text">${task.error_message}</span>
                        </div>
                        ` : ''}
                        ${jumpLinks ? `
                        <div class="detail-item">
                            <label>任务结果:</label>
                            <div class="task-jump-links">
                                ${jumpLinks}
                            </div>
                        </div>
                        ` : ''}
                        ${task.result && task.status === 'COMPLETED' ? `
                        <div class="detail-item">
                            <label>结果摘要:</label>
                            <div class="task-result-summary">
                                ${this.generateResultSummary(task)}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    <div class="dialog-actions">
                        ${jumpLinks ? `
                        <button type="button" class="btn btn-success" onclick="taskCenter.executeJump('${task.task_type}', \`${JSON.stringify(task).replace(/`/g, '\\`')}\`)">
                            <i class="fas fa-external-link-alt"></i> 查看完整结果
                        </button>
                        ` : ''}
                        <button type="button" class="btn btn-primary" onclick="taskCenter.closeDialog()">关闭</button>
                    </div>
                </div>
            `;

            this.showDialog(html);
        } catch (error) {
            console.error('View task details error:', error);
            this.showNotification('获取任务详情失败', 'error');
        }
    }

    /**
     * 生成任务跳转链接
     */
    generateJumpLinks(task) {
        if (task.status !== 'COMPLETED') {
            return '';
        }

        const type = task.task_type;
        const params = task.params || {};

        switch (type) {
            case 'analysis_daily':
                // 股票分析任务
                const selectionMode = params.selection_mode || 'top_n';
                const maxResults = params.max_results || 20;
                return `
                    <div class="jump-link-item">
                        <i class="fas fa-chart-line"></i>
                        <span>查看分析结果</span>
                        <a href="#" onclick="taskCenter.jumpToAnalysis('${selectionMode}', ${maxResults})" class="jump-link">
                            <i class="fas fa-arrow-right"></i>
                        </a>
                    </div>
                `;

            case 'backtest_batch':
                // 批量回测任务
                const stockCount = task.result?.total_stocks || 0;
                const successRate = task.result?.overall_success_rate || 0;
                return `
                    <div class="jump-link-item">
                        <i class="fas fa-chart-area"></i>
                        <span>查看回测结果</span>
                        <a href="#" onclick="taskCenter.jumpToBacktest()" class="jump-link">
                            <i class="fas fa-arrow-right"></i>
                        </a>
                    </div>
                    <div class="jump-link-summary">
                        回测了 ${stockCount} 只股票，成功率 ${successRate.toFixed(1)}%
                    </div>
                `;

            case 'scheduler_cache':
                // 缓存预加载任务
                const cachedStocks = task.result?.cached_stocks || 0;
                return `
                    <div class="jump-link-item">
                        <i class="fas fa-database"></i>
                        <span>查看缓存统计</span>
                        <a href="#" onclick="taskCenter.jumpToCache()" class="jump-link">
                            <i class="fas fa-arrow-right"></i>
                        </a>
                    </div>
                    <div class="jump-link-summary">
                        成功缓存 ${cachedStocks} 只股票
                    </div>
                `;

            case 'sector_analyze':
                // 板块分析任务
                const sectorName = params.sector_name || '未知板块';
                return `
                    <div class="jump-link-item">
                        <i class="fas fa-building"></i>
                        <span>查看板块分析结果 (${sectorName})</span>
                        <a href="#" onclick="taskCenter.jumpToSector('${sectorName}')" class="jump-link">
                            <i class="fas fa-arrow-right"></i>
                        </a>
                    </div>
                `;

            default:
                return '';
        }
    }

    /**
     * 生成结果摘要
     */
    generateResultSummary(task) {
        if (!task.result) {
            return '';
        }

        const type = task.task_type;
        const result = task.result;

        switch (type) {
            case 'analysis_daily':
                const recommendedCount = result.recommended_stocks?.length || 0;
                const totalAnalyzed = result.total_analyzed || 0;
                return `
                    <div class="result-summary-item">
                        <span class="summary-label">分析股票:</span>
                        <span class="summary-value">${totalAnalyzed} 只</span>
                    </div>
                    <div class="result-summary-item">
                        <span class="summary-label">推荐股票:</span>
                        <span class="summary-value recommendation">${recommendedCount} 只</span>
                    </div>
                `;

            case 'backtest_batch':
                const totalStocks = result.total_stocks || 0;
                const totalRecs = result.total_recommendations || 0;
                const successRate = result.overall_success_rate || 0;
                return `
                    <div class="result-summary-item">
                        <span class="summary-label">回测股票:</span>
                        <span class="summary-value">${totalStocks} 只</span>
                    </div>
                    <div class="result-summary-item">
                        <span class="summary-label">总推荐:</span>
                        <span class="summary-value">${totalRecs} 次</span>
                    </div>
                    <div class="result-summary-item">
                        <span class="summary-label">成功率:</span>
                        <span class="summary-value ${successRate >= 60 ? 'success' : 'warning'}">${successRate.toFixed(1)}%</span>
                    </div>
                `;

            case 'scheduler_cache':
                const cached = result.cached_stocks || 0;
                const failed = result.failed_stocks || 0;
                return `
                    <div class="result-summary-item">
                        <span class="summary-label">成功缓存:</span>
                        <span class="summary-value success">${cached} 只</span>
                    </div>
                    <div class="result-summary-item">
                        <span class="summary-label">失败数量:</span>
                        <span class="summary-value ${failed > 0 ? 'danger' : ''}">${failed} 只</span>
                    </div>
                `;

            case 'sector_analyze':
                const stockCount = result.stocks?.length || 0;
                return `
                    <div class="result-summary-item">
                        <span class="summary-label">分析股票:</span>
                        <span class="summary-value">${stockCount} 只</span>
                    </div>
                `;

            default:
                return '';
        }
    }

    /**
     * 执行跳转
     */
    executeJump(taskType, taskJson) {
        try {
            const task = JSON.parse(taskJson);
            switch (taskType) {
                case 'analysis_daily':
                    const selectionMode = task.params?.selection_mode || 'top_n';
                    const maxResults = task.params?.max_results || 20;
                    this.jumpToAnalysis(selectionMode, maxResults);
                    break;
                case 'backtest_batch':
                    this.jumpToBacktest();
                    break;
                case 'scheduler_cache':
                    this.jumpToCache();
                    break;
                case 'sector_analyze':
                    const sectorName = task.params?.sector_name || '';
                    this.jumpToSector(sectorName);
                    break;
            }
        } catch (error) {
            console.error('Execute jump error:', error);
            this.showNotification('跳转失败', 'error');
        }
    }

    /**
     * 跳转到股票分析页面
     */
    jumpToAnalysis(selectionMode, maxResults) {
        this.closeDialog();
        // 切换到分析标签页
        const analysisTab = document.querySelector('[data-tab="analysis"]');
        if (analysisTab) {
            analysisTab.click();
        }

        // 设置分析参数
        setTimeout(() => {
            const modeSelect = document.getElementById('selection-mode');
            const countInput = document.getElementById('max-results');

            if (modeSelect && countInput) {
                modeSelect.value = selectionMode;
                countInput.value = maxResults;

                // 显示通知
                this.showNotification(`已跳转到分析页面，模式: ${selectionMode}, 数量: ${maxResults}`, 'info');
            }
        }, 500);
    }

    /**
     * 跳转到回测页面
     */
    jumpToBacktest() {
        this.closeDialog();
        // 切换到回测标签页
        const backtestTab = document.querySelector('[data-tab="backtest"]');
        if (backtestTab) {
            backtestTab.click();
        }

        setTimeout(() => {
            this.showNotification('已跳转到回测分析页面', 'info');
        }, 500);
    }

    /**
     * 跳转到缓存页面
     */
    jumpToCache() {
        this.closeDialog();
        // 切换到缓存标签页
        const cacheTab = document.querySelector('[data-tab="cache"]');
        if (cacheTab) {
            cacheTab.click();
        }

        setTimeout(() => {
            this.showNotification('已跳转到系统缓存页面', 'info');
        }, 500);
    }

    /**
     * 跳转到板块分析页面
     */
    jumpToSector(sectorName) {
        this.closeDialog();
        // 切换到板块标签页
        const sectorTab = document.querySelector('[data-tab="sectors"]');
        if (sectorTab) {
            sectorTab.click();
        }

        setTimeout(() => {
            if (sectorName) {
                this.showNotification(`已跳转到板块页面: ${sectorName}`, 'info');
            } else {
                this.showNotification('已跳转到板块页面', 'info');
            }
        }, 500);
    }

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadRunningTasks();
            this.loadTaskStatistics();
        }, 5000); // 每5秒刷新一次
    }

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

/**
 * 筛选任务
 */
function filterTasks() {
    if (window.taskCenter) {
        window.taskCenter.loadTaskHistory();
    }
}

// 初始化任务中心
let taskCenter;
document.addEventListener('DOMContentLoaded', () => {
    // 检查当前是否在任务中心标签页
    const tasksTab = document.querySelector('.tab-btn[data-tab="tasks"]');
    if (tasksTab) {
        tasksTab.addEventListener('click', () => {
            if (!taskCenter) {
                taskCenter = new TaskCenter();
            }
        });
    }

    // 立即初始化TaskCenter，无需等待标签点击
    taskCenter = new TaskCenter();

    console.log('✅ TaskCenter initialized');
});