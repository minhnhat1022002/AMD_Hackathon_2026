// Front Desk Dashboard - Hospitality AI
class FrontDeskDashboard {
    constructor() {
        this.apiBaseUrl = window.location.origin;
        this.currentFilter = 'all';
        this.refreshInterval = 5000; // 5 seconds
        this.refreshTimer = null;
        
        this.initializeElements();
        this.bindEvents();
        this.startAutoRefresh();
        this.loadInitialData();
    }

    initializeElements() {
        // Header elements
        this.connectionStatus = document.getElementById('connection-status');
        this.refreshBtn = document.getElementById('refresh-btn');
        
        // Booking Override elements
        this.reservationSearch = document.getElementById('reservation-search');
        this.reservationList = document.getElementById('reservation-list');
        this.overrideForm = document.getElementById('override-form');
        this.modifyForm = document.getElementById('modify-form');
        
        // Guest Monitor elements
        this.guestList = document.getElementById('guest-list');
        this.filterTabs = document.querySelectorAll('.tab-btn');
        
        // Decision Queue elements
        this.caseList = document.getElementById('case-list');
        this.urgentCount = document.getElementById('urgent-count');
        this.pendingCount = document.getElementById('pending-count');
        
        // Modal elements
        this.caseModal = document.getElementById('case-modal');
        this.caseDetails = document.getElementById('case-details');
        this.caseActions = document.getElementById('case-actions');
        this.closeModal = document.getElementById('close-modal');
    }

    bindEvents() {
        // Refresh button
        this.refreshBtn.addEventListener('click', () => this.refreshAllData());
        
        // Reservation search
        this.reservationSearch.addEventListener('input', (e) => {
            this.searchReservations(e.target.value);
        });
        
        // Filter tabs
        this.filterTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.filterTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentFilter = tab.dataset.filter;
                this.loadGuestActivity();
            });
        });
        
        // Override form
        this.modifyForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitOverride();
        });
        
        document.getElementById('cancel-override').addEventListener('click', () => {
            this.hideOverrideForm();
        });
        
        // Modal
        this.closeModal.addEventListener('click', () => this.closeCaseModal());
        this.caseModal.addEventListener('click', (e) => {
            if (e.target === this.caseModal) {
                this.closeCaseModal();
            }
        });
    }

    startAutoRefresh() {
        this.refreshTimer = setInterval(() => {
            this.refreshAllData();
        }, this.refreshInterval);
    }

    async loadInitialData() {
        await Promise.all([
            this.loadReservations(),
            this.loadGuestActivity(),
            this.loadDecisionQueue()
        ]);
    }

    async refreshAllData() {
        this.setLoadingState(true);
        try {
            await this.loadInitialData();
            this.updateConnectionStatus(true);
        } catch (error) {
            console.error('Refresh error:', error);
            this.updateConnectionStatus(false);
        } finally {
            this.setLoadingState(false);
        }
    }

    setLoadingState(loading) {
        this.refreshBtn.disabled = loading;
        this.refreshBtn.textContent = loading ? '🔄 Loading...' : '🔄 Refresh';
    }

    updateConnectionStatus(connected) {
        const statusDot = this.connectionStatus.querySelector('.status-dot');
        const statusText = this.connectionStatus.querySelector('.status-text');
        
        if (connected) {
            statusDot.style.background = 'var(--success-color)';
            statusText.textContent = 'Connected';
        } else {
            statusDot.style.background = 'var(--danger-color)';
            statusText.textContent = 'Disconnected';
        }
    }

    async loadReservations() {
        try {
            const response = await this.callAPI('/booking/reservations');
            this.renderReservations(response.reservations || []);
        } catch (error) {
            console.error('Error loading reservations:', error);
            this.renderReservations(this.getMockReservations());
        }
    }

    async loadGuestActivity() {
        try {
            const response = await this.callAPI('/guest/activity');
            this.renderGuestActivity(response.guests || []);
        } catch (error) {
            console.error('Error loading guest activity:', error);
            this.renderGuestActivity(this.getMockGuestActivity());
        }
    }

    async loadDecisionQueue() {
        try {
            const response = await this.callAPI('/decision/queue');
            this.renderDecisionQueue(response.cases || []);
        } catch (error) {
            console.error('Error loading decision queue:', error);
            this.renderDecisionQueue(this.getMockDecisionQueue());
        }
    }

    async callAPI(endpoint) {
        const response = await fetch(`${this.apiBaseUrl}${endpoint}`);
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        return await response.json();
    }

    renderReservations(reservations) {
        this.reservationList.innerHTML = '';
        
        reservations.forEach(reservation => {
            const item = this.createReservationItem(reservation);
            this.reservationList.appendChild(item);
        });
    }

    createReservationItem(reservation) {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <div class="item-header">
                <div class="item-title">${reservation.id} - ${reservation.guest_name}</div>
                <div class="item-status status-${reservation.status}">${reservation.status}</div>
            </div>
            <div class="item-details">
                <div class="item-detail">📅 ${reservation.check_in} → ${reservation.check_out}</div>
                <div class="item-detail">🏠 ${reservation.room_type}</div>
                <div class="item-detail">💰 $${reservation.price}</div>
            </div>
        `;
        
        div.addEventListener('click', () => this.showOverrideForm(reservation));
        return div;
    }

    renderGuestActivity(guests) {
        this.guestList.innerHTML = '';
        
        const filteredGuests = this.filterGuests(guests, this.currentFilter);
        
        filteredGuests.forEach(guest => {
            const item = this.createGuestItem(guest);
            this.guestList.appendChild(item);
        });
    }

    filterGuests(guests, filter) {
        switch (filter) {
            case 'active':
                return guests.filter(g => g.status === 'active');
            case 'escalated':
                return guests.filter(g => g.status === 'escalated');
            default:
                return guests;
        }
    }

    createGuestItem(guest) {
        const div = document.createElement('div');
        div.className = `list-item ${guest.status}`;
        div.innerHTML = `
            <div class="item-header">
                <div class="item-title">${guest.guest_id} - ${guest.name}</div>
                <div class="item-status status-${guest.status}">${guest.status}</div>
            </div>
            <div class="item-details">
                <div class="item-detail">💬 ${guest.last_message}</div>
                <div class="item-detail">⏰ ${guest.last_activity}</div>
            </div>
        `;
        
        if (guest.status === 'escalated') {
            div.addEventListener('click', () => this.showCaseDetails(guest.case_id));
        }
        
        return div;
    }

    renderDecisionQueue(cases) {
        this.caseList.innerHTML = '';
        
        let urgentCount = 0;
        let pendingCount = 0;
        
        cases.forEach(caseItem => {
            if (caseItem.priority === 'urgent') urgentCount++;
            else pendingCount++;
            
            const item = this.createCaseItem(caseItem);
            this.caseList.appendChild(item);
        });
        
        this.urgentCount.textContent = urgentCount;
        this.pendingCount.textContent = pendingCount;
    }

    createCaseItem(caseItem) {
        const div = document.createElement('div');
        div.className = `list-item ${caseItem.priority}`;
        div.innerHTML = `
            <div class="item-header">
                <div class="item-title">Case ${caseItem.id} - ${caseItem.type}</div>
                <div class="item-status status-${caseItem.priority}">${caseItem.priority}</div>
            </div>
            <div class="item-details">
                <div class="item-detail">👤 ${caseItem.guest_id}</div>
                <div class="item-detail">📝 ${caseItem.description}</div>
                <div class="item-detail">⏰ ${caseItem.created_at}</div>
            </div>
        `;
        
        div.addEventListener('click', () => this.showCaseDetails(caseItem.id));
        return div;
    }

    showOverrideForm(reservation) {
        this.overrideForm.classList.add('active');
        document.getElementById('res-id').value = reservation.id;
        document.getElementById('guest-name').value = reservation.guest_name;
        document.getElementById('checkin-date').value = reservation.check_in;
        document.getElementById('checkout-date').value = reservation.check_out;
        document.getElementById('room-type').value = reservation.room_type;
    }

    hideOverrideForm() {
        this.overrideForm.classList.remove('active');
        this.modifyForm.reset();
    }

    async submitOverride() {
        const formData = new FormData(this.modifyForm);
        const data = Object.fromEntries(formData);
        
        try {
            await this.callAPI('/booking/override', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            
            this.hideOverrideForm();
            this.loadReservations();
            this.showNotification('Reservation updated successfully', 'success');
        } catch (error) {
            console.error('Override error:', error);
            this.showNotification('Failed to update reservation', 'error');
        }
    }

    showCaseDetails(caseId) {
        const caseData = this.getMockCaseDetails(caseId);
        
        this.caseDetails.innerHTML = `
            <div class="case-info">
                <h4>Case Information</h4>
                <p><strong>Case ID:</strong> ${caseData.id}</p>
                <p><strong>Type:</strong> ${caseData.type}</p>
                <p><strong>Priority:</strong> ${caseData.priority}</p>
                <p><strong>Guest:</strong> ${caseData.guest_id}</p>
                <p><strong>Description:</strong> ${caseData.description}</p>
                <p><strong>Created:</strong> ${caseData.created_at}</p>
            </div>
            <div class="case-history">
                <h4>History</h4>
                ${caseData.history.map(item => `
                    <div class="history-item">
                        <strong>${item.timestamp}:</strong> ${item.action}
                    </div>
                `).join('')}
            </div>
        `;
        
        this.caseActions.innerHTML = this.generateCaseActions(caseData);
        this.caseModal.style.display = 'flex';
    }

    generateCaseActions(caseData) {
        const actions = [];
        
        switch (caseData.type) {
            case 'complaint':
                actions.push('<button class="btn-primary" onclick="dashboard.resolveCase(\'apology\')">Send Apology</button>');
                actions.push('<button class="btn-secondary" onclick="dashboard.resolveCase(\'upgrade\')">Offer Upgrade</button>');
                actions.push('<button class="btn-secondary" onclick="dashboard.resolveCase(\'refund\')">Process Refund</button>');
                break;
            case 'booking_issue':
                actions.push('<button class="btn-primary" onclick="dashboard.resolveCase(\'modify\')">Modify Booking</button>');
                actions.push('<button class="btn-secondary" onclick="dashboard.resolveCase(\'cancel\')">Cancel & Refund</button>');
                break;
            default:
                actions.push('<button class="btn-primary" onclick="dashboard.resolveCase(\'resolve\')">Mark Resolved</button>');
        }
        
        return actions.join('');
    }

    closeCaseModal() {
        this.caseModal.style.display = 'none';
    }

    async resolveCase(action) {
        try {
            await this.callAPI('/decision/resolve', {
                method: 'POST',
                body: JSON.stringify({ action })
            });
            
            this.closeCaseModal();
            this.loadDecisionQueue();
            this.showNotification(`Case resolved: ${action}`, 'success');
        } catch (error) {
            console.error('Resolve case error:', error);
            this.showNotification('Failed to resolve case', 'error');
        }
    }

    searchReservations(query) {
        const items = this.reservationList.querySelectorAll('.list-item');
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(query.toLowerCase())) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }

    showNotification(message, type) {
        // Simple notification implementation
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            color: white;
            font-weight: 500;
            z-index: 1001;
            background: ${type === 'success' ? 'var(--success-color)' : 'var(--danger-color)'};
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Mock data methods
    getMockReservations() {
        return [
            {
                id: 'R001',
                guest_name: 'John Smith',
                check_in: '2024-01-15',
                check_out: '2024-01-17',
                room_type: 'deluxe',
                price: 240,
                status: 'confirmed'
            },
            {
                id: 'R002',
                guest_name: 'Sarah Johnson',
                check_in: '2024-01-16',
                check_out: '2024-01-18',
                room_type: 'standard',
                price: 160,
                status: 'pending'
            }
        ];
    }

    getMockGuestActivity() {
        return [
            {
                guest_id: 'G123',
                name: 'John Smith',
                status: 'active',
                last_message: 'Do you have rooms tomorrow?',
                last_activity: '2 minutes ago'
            },
            {
                guest_id: 'G456',
                name: 'Sarah Johnson',
                status: 'escalated',
                last_message: 'Room is dirty, I need help!',
                last_activity: '5 minutes ago',
                case_id: 'C001'
            }
        ];
    }

    getMockDecisionQueue() {
        return [
            {
                id: 'C001',
                type: 'complaint',
                priority: 'urgent',
                guest_id: 'G456',
                description: 'Guest reports room cleanliness issues',
                created_at: '10 minutes ago'
            },
            {
                id: 'C002',
                type: 'booking_issue',
                priority: 'pending',
                guest_id: 'G789',
                description: 'Guest wants to modify reservation dates',
                created_at: '25 minutes ago'
            }
        ];
    }

    getMockCaseDetails(caseId) {
        return {
            id: caseId,
            type: 'complaint',
            priority: 'urgent',
            guest_id: 'G456',
            description: 'Guest reports room cleanliness issues',
            created_at: '10 minutes ago',
            history: [
                { timestamp: '10:30 AM', action: 'Case created from guest chat' },
                { timestamp: '10:32 AM', action: 'Escalated to front desk' }
            ]
        };
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new FrontDeskDashboard();
});
