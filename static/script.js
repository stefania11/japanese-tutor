
document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const imageUpload = document.getElementById('image-upload');
    const imagePreview = document.getElementById('image-preview');
    
    let currentImageData = null;
    
    addAssistantMessage("こんにちは！ Konnichiwa! I'm your Japanese tutor. How can I help you today?");
    
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    imageUpload.addEventListener('change', handleImageUpload);
    
    document.addEventListener('paste', handlePaste);
    
    async function sendMessage() {
        const message = messageInput.value.trim();
        
        if (!message && !currentImageData) return;
        
        addUserMessage(message, currentImageData);
        
        messageInput.value = '';
        
        const loadingElement = addLoadingIndicator();
        
        try {
            const requestData = {
                message: message
            };
            
            if (currentImageData) {
                requestData.image_data = currentImageData;
            }
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            const data = await response.json();
            
            loadingElement.remove();
            
            if (data.error) {
                addErrorMessage(data.error);
            } else {
                addAssistantMessage(data.response);
            }
            
            clearImagePreview();
            
        } catch (error) {
            loadingElement.remove();
            
            addErrorMessage('Error: Could not connect to the server');
            console.error('Error:', error);
        }
    }
    
    function handleImageUpload(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            processImageFile(file);
        }
    }
    
    function handlePaste(event) {
        const items = (event.clipboardData || event.originalEvent.clipboardData).items;
        
        for (const item of items) {
            if (item.type.indexOf('image') === 0) {
                const blob = item.getAsFile();
                processImageFile(blob);
                event.preventDefault();
                return;
            }
        }
    }
    
    function processImageFile(file) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            currentImageData = e.target.result;
            
            displayImagePreview(currentImageData);
        };
        
        reader.readAsDataURL(file);
    }
    
    function displayImagePreview(imageData) {
        clearImagePreview();
        
        const img = document.createElement('img');
        img.src = imageData;
        img.alt = 'Image Preview';
        
        imagePreview.appendChild(img);
    }
    
    function clearImagePreview() {
        imagePreview.innerHTML = '';
        currentImageData = null;
    }
    
    function addUserMessage(text, imageData = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        
        if (text) {
            const textDiv = document.createElement('div');
            textDiv.className = 'message-content';
            textDiv.textContent = text;
            messageDiv.appendChild(textDiv);
        }
        
        if (imageData) {
            const img = document.createElement('img');
            img.src = imageData;
            img.alt = 'User Image';
            messageDiv.appendChild(img);
        }
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function addAssistantMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        
        const formattedText = formatMessage(text);
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-content';
        textDiv.innerHTML = formattedText;
        
        messageDiv.appendChild(textDiv);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function addErrorMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message error-message';
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading';
        
        const dotsDiv = document.createElement('div');
        dotsDiv.className = 'loading-dots';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dotsDiv.appendChild(dot);
        }
        
        loadingDiv.appendChild(dotsDiv);
        chatMessages.appendChild(loadingDiv);
        scrollToBottom();
        
        return loadingDiv;
    }
    
    function formatMessage(text) {
        text = text.replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
        
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        text = text.replace(/\n/g, '<br>');
        
        return text;
    }
    
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
