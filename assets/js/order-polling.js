/**
 * DigiBhoj Real-time Order Polling
 * Periodic status checks for Customers, Providers, and Riders.
 */

class OrderPolling {
    constructor() {
        this.ctx = window.DigiBhoj || {};
        this.interval = 10000; // Poll every 10 seconds
        this.lastOrderState = {};
        
        if (this.ctx.userRole) {
            this.init();
        }
    }

    init() {
        setInterval(() => this.poll(), this.interval);
        // Instant check on load
        this.poll();
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
        const response = await fetch('/api/orders/customer');
        if (!response.ok) return;
        const orders = await response.json();
        
        orders.forEach(order => {
            const lastStatus = this.lastOrderState[order.id];
            if (lastStatus && lastStatus !== order.status) {
                _showToast(`Order #${order.id} status updated to ${order.status.replace('_', ' ')}!`, 'info');
                // Refresh page if on order detail or list to show update
                if (window.location.pathname.includes('/customer/order/') || 
                    window.location.pathname.includes('/customer/orders')) {
                    setTimeout(() => window.location.reload(), 2000);
                }
            }
            this.lastOrderState[order.id] = order.status;
        });
    }

    async pollProvider() {
        if (!this.ctx.roleId) return;
        const response = await fetch(`/api/provider/orders/${this.ctx.roleId}`);
        if (!response.ok) return;
        const orders = await response.json();
        
        const currentCount = orders.filter(o => o.status === 'created').length;
        const lastCount = this.lastOrderState['pending_count'] || 0;
        
        if (currentCount > lastCount) {
            _showToast(`You have ${currentCount} new order(s)!`, 'success');
            if (window.location.pathname.includes('/provider/dashboard') || 
                window.location.pathname.includes('/provider/orders')) {
                setTimeout(() => window.location.reload(), 2000);
            }
        }
        this.lastOrderState['pending_count'] = currentCount;
    }

    async pollDelivery() {
        if (!this.ctx.roleId) return;
        const response = await fetch(`/api/delivery/tasks/${this.ctx.roleId}`);
        if (!response.ok) return;
        const tasks = await response.json();
        
        const pendingTasks = tasks.filter(t => t.status === 'pending').length;
        const lastCount = this.lastOrderState['pending_tasks_count'] || 0;
        
        if (pendingTasks > lastCount) {
            _showToast(`New delivery task available! 🚚`, 'success');
            if (window.location.pathname.includes('/delivery/dashboard')) {
                setTimeout(() => window.location.reload(), 2000);
            }
        }
        this.lastOrderState['pending_tasks_count'] = pendingTasks;
    }
}

// Helper to show toasts (integrated with existing toast.js if available)
function _showToast(message, type = 'info') {
    // If there is a global showToast that isn't THIS function, use it
    if (window.showToast && window.showToast !== _showToast) {
        window.showToast(message, type);
    } else {
        console.log(`[REALTIME] ${type.toUpperCase()}: ${message}`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.orderPolling = new OrderPolling();
});
