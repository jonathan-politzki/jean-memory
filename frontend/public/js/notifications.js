// Simple notification system
window.showNotification = function(message, type = 'info', duration = 3000) {
    // Create notification container if it doesn't exist
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '9999';
        document.body.appendChild(notificationContainer);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = message;
    
    // Style the notification
    notification.style.backgroundColor = type === 'error' ? '#f44336' : 
                                        type === 'success' ? '#4CAF50' : 
                                        type === 'warning' ? '#ff9800' : '#2196F3';
    notification.style.color = 'white';
    notification.style.padding = '12px 16px';
    notification.style.margin = '0 0 10px 0';
    notification.style.borderRadius = '4px';
    notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
    notification.style.minWidth = '250px';
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.3s ease';
    
    // Add close button
    const closeButton = document.createElement('span');
    closeButton.innerHTML = '&times;';
    closeButton.style.float = 'right';
    closeButton.style.fontWeight = 'bold';
    closeButton.style.fontSize = '20px';
    closeButton.style.lineHeight = '1';
    closeButton.style.cursor = 'pointer';
    closeButton.style.marginLeft = '10px';
    
    closeButton.onclick = function() {
        clearTimeout(removeTimeout);
        removeNotification();
    };
    
    notification.insertBefore(closeButton, notification.firstChild);
    
    // Add to container
    notificationContainer.appendChild(notification);
    
    // Fade in
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 10);
    
    // Remove after duration
    const removeTimeout = setTimeout(removeNotification, duration);
    
    function removeNotification() {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode === notificationContainer) {
                notificationContainer.removeChild(notification);
            }
            
            // Remove container if empty
            if (notificationContainer.children.length === 0) {
                document.body.removeChild(notificationContainer);
            }
        }, 300);
    }
    
    return notification;
}; 