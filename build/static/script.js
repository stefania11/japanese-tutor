
document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const voiceButton = document.getElementById('voice-button');
    const imageUpload = document.getElementById('image-upload');
    const imagePreview = document.getElementById('image-preview');
    
    let currentImageData = null;
    let isRecording = false;
    let recognition = null;
    
    try {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US'; // Default language
            
            recognition.onstart = function() {
                isRecording = true;
                voiceButton.classList.add('recording');
                voiceButton.innerHTML = '<span>Listening...</span>';
            };
            
            recognition.onresult = function(event) {
                const transcript = Array.from(event.results)
                    .map(result => result[0])
                    .map(result => result.transcript)
                    .join('');
                    
                messageInput.value = transcript;
            };
            
            recognition.onend = function() {
                isRecording = false;
                voiceButton.classList.remove('recording');
                voiceButton.innerHTML = '<span>Voice Input</span>';
            };
            
            recognition.onerror = function(event) {
                console.error('Speech recognition error', event.error);
                isRecording = false;
                voiceButton.classList.remove('recording');
                voiceButton.innerHTML = '<span>Voice Input</span>';
                
                if (event.error === 'not-allowed') {
                    addErrorMessage('Microphone access denied. Please enable microphone permissions in your browser settings.');
                }
            };
        }
    } catch (e) {
        console.error('Error initializing speech recognition:', e);
    }
    
    addAssistantMessage("こんにちは！ Konnichiwa! I'm your Japanese tutor. How can I help you today?");
    
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    if (voiceButton) {
        voiceButton.addEventListener('click', function() {
            if (!recognition) {
                addErrorMessage('Speech recognition is not supported in your browser.');
                return;
            }
            
            if (isRecording) {
                recognition.stop();
            } else {
                messageInput.value = '';
                recognition.start();
            }
        });
    }
    
    imageUpload.addEventListener('change', handleImageUpload);
    
    document.addEventListener('paste', handlePaste);
    
    async function sendMessage() {
        const message = messageInput.value.trim();
        
        if (!message && !currentImageData) return;
        
        addUserMessage(message, currentImageData);
        
        messageInput.value = '';
        
        const loadingElement = addLoadingIndicator();
        
        try {
            const hasCameraQuery = message.toLowerCase().includes('camera') || 
                                  message.toLowerCase().includes('look') || 
                                  message.toLowerCase().includes('see') ||
                                  message.toLowerCase().includes('what is this');
                                  
            const useFallback = true; // Set to true to use fallback responses
            
            if (currentImageData && useFallback) {
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                let response;
                if (message.toLowerCase().includes('what')) {
                    response = 'これは何ですか？ (Kore wa nan desu ka?) - What is this?';
                } else if (message.toLowerCase().includes('translate')) {
                    response = 'テキストを翻訳します (Tekisuto o honyaku shimasu) - I will translate the text.';
                } else if (message.toLowerCase().includes('read')) {
                    response = 'テキストを読みます (Tekisuto o yomimasu) - I will read the text.';
                } else {
                    response = '画像を見ました (Gazō o mimashita) - I see the image.';
                }
                
                loadingElement.remove();
                addAssistantMessage(response);
                clearImagePreview();
                return;
            }
            
            if (useFallback) {
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                let response;
                if (message.toLowerCase().includes('book')) {
                    response = '本 (hon) means book in Japanese.';
                } else if (message.toLowerCase().includes('hello') || message.toLowerCase().includes('hi')) {
                    response = 'こんにちは (konnichiwa) means hello in Japanese.';
                } else if (message.toLowerCase().includes('thank')) {
                    response = 'ありがとう (arigatou) means thank you in Japanese.';
                } else if (hasCameraQuery) {
                    response = 'Please use the "Upload Image" button to share an image.';
                } else if (message.toLowerCase().includes('food') || message.toLowerCase().includes('eat')) {
                    response = '食べ物 (tabemono) means food in Japanese.';
                } else if (message.toLowerCase().includes('water')) {
                    response = '水 (mizu) means water in Japanese.';
                } else if (message.toLowerCase().includes('goodbye') || message.toLowerCase().includes('bye')) {
                    response = 'さようなら (sayounara) means goodbye in Japanese.';
                } else if (message.toLowerCase().includes('stop') || message.toLowerCase().includes('quit')) {
                    response = 'Sayonara! Goodbye!';
                } else {
                    response = '日本語 (nihongo) means Japanese language. How else can I help you learn Japanese?';
                }
                
                loadingElement.remove();
                addAssistantMessage(response);
                clearImagePreview();
                return;
            }
            
            const requestData = {
                message: message
            };
            
            if (currentImageData) {
                requestData.image_data = currentImageData;
            }
            
            const hostname = window.location.hostname;
            const protocol = window.location.protocol;
            const port = window.location.port ? `:${window.location.port}` : '';
            
            const apiUrl = `${protocol}//${hostname}${port}/api/chat`;
            
            console.log('Sending request to:', apiUrl);
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            console.log('Response status:', response.status);
            
            const data = await response.json();
            console.log('Response data:', data);
            
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
            console.log('Image loaded successfully:', currentImageData ? currentImageData.substring(0, 50) + '...' : 'null');
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
