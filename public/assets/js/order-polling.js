/**
 * DigiBhoj Real-time Order Polling
 * Periodic status checks for Customers, Providers, and Riders.
 */

class OrderPolling {
    constructor() {
        this.ctx = window.DigiBhoj || {};
        this.interval = 10000; // Poll every 10 seconds
        this.lastOrderState = {};
        this.timer = null;
        
        if (this.ctx.userRole) {
            this.init();
        }
    }

    init() {
        this.timer = setInterval(() => this.poll(), this.interval);
        // Instant check on load
        this.poll();
    }

    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    async poll() {
        try {
            if (this.ctx.userRole === 'customer') {
                await this.pollCustomer();
            } else if (this.ctx.userRole === 'provider') {
                await this.pollProvider();
            } else if (this.ctx.userRole === 'delivery') {
                await this.pollDelivery();
            }
        } catch (e) {
            console.error("Polling error:", e);
        }
    }

    async pollCustomer() {
        try {
            const response = await fetch('/api/orders/customer');
            if (response.status === 401) {
                console.warn('OrderPolling: Unauthorized (401). Stopping customer poll.');
                this.stop();
                return;
            }
            if (!response.ok) return;
            const orders = await response.json();
            
            orders.forEach(order => {
                const lastStatus = this.lastOrderState[order.id];
                if (lastStatus && lastStatus !== order.status) {
                    _showToast(`Order #${order.id} status updated to ${order.status.replace('_', ' ')}!`, 'info');
                }
                this.lastOrderState[order.id] = order.status;
            });

            // Also poll for unread notifications
            await this.pollNotifications();
        } catch (err) {
            console.error('OrderPolling Customer Error:', err);
        }
    }

    async pollNotifications() {
        try {
            // We fetch the header notifications which are already injected in UI (or we could have a dedicated API)
            // But since I updated UI_router to inject them, we need an API to fetch them periodically.
            // Let's check if there is a GET /api/notifications
            const response = await fetch('/api/notifications');
            if (response.ok) {
                const notifications = await response.json();
                const unread = notifications.filter(n => !n.is_read);
                const lastCount = this.lastOrderState['unread_notifications'] || 0;
                
                if (unread.length > lastCount) {
                    const latest = unread[0];
                    _showToast(`New Notification: ${latest.message}`, 'success');
                    // We could also update the DOM badge here if we had the code
                    if (document.getElementById('notif-badge')) {
                        document.getElementById('notif-badge').textContent = unread.length;
                        document.getElementById('notif-badge').style.display = 'block';
                    }
                }
                this.lastOrderState['unread_notifications'] = unread.length;
            }
        } catch (err) {
            console.error('OrderPolling Notifications Error:', err);
        }
    }

    async pollProvider() {
        if (!this.ctx.roleId) return;
        try {
            const response = await fetch(`/api/provider/orders/${this.ctx.roleId}`);
            if (response.status === 401) {
                console.warn('OrderPolling: Unauthorized (401). Stopping provider poll.');
                this.stop();
                return;
            }
            if (!response.ok) return;
            const orders = await response.json();
            
            const currentCount = orders.filter(o => o.status === 'created').length;
            const lastCount = this.lastOrderState['pending_count'] || 0;
            
            if (currentCount > lastCount) {
                _showToast(`You have ${currentCount} new order(s)!`, 'success');
            }
            this.lastOrderState['pending_count'] = currentCount;
        } catch (err) {
            console.error('OrderPolling Provider Error:', err);
        }
    }

    async pollDelivery() {
        if (!this.ctx.roleId) return;
        try {
            const response = await fetch(`/api/delivery/tasks/${this.ctx.roleId}`);
            if (response.status === 401) {
                console.warn('OrderPolling: Unauthorized (401). Stopping delivery poll.');
                this.stop();
                return;
            }
            if (!response.ok) return;
            const tasks = await response.json();
            
            const pendingTasks = tasks.filter(t => t.status === 'assigned').length;
            const lastCount = this.lastOrderState['pending_tasks_count'] || 0;
            
            if (pendingTasks > lastCount) {
                _showToast(`New delivery task available! 🚚`, 'success');
            }
            this.lastOrderState['pending_tasks_count'] = pendingTasks;
        } catch (err) {
            console.error('OrderPolling Delivery Error:', err);
        }
    }
}

// Helper to show toasts (integrated with existing toast.js if available)
function _showToast(message, type = 'info') {
    // If there is a global showToast that isn't THIS function, use it
    if (window.showToast && window.showToast !== _showToast) {
        window.showToast(message, type);
    } else {
        const toastContainer = document.getElementById('toast-container');
        if (toastContainer) {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toastContainer.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        } else {
            console.log(`[REALTIME] ${type.toUpperCase()}: ${message}`);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.orderPolling = new OrderPolling();
});
