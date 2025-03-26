
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
    let synth = window.speechSynthesis;
    
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
                
                if (messageInput.value.trim()) {
                    sendMessage();
                }
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
    
    const welcomeMessage = "こんにちは！ Konnichiwa! I'm your Japanese tutor. How can I help you today?";
    addAssistantMessage(welcomeMessage);
    speakText(welcomeMessage);
    
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
    
    function speakText(text) {
        if (synth.speaking) {
            synth.cancel();
        }
        
        const cleanText = text.replace(/\*\*/g, '').replace(/\*/g, '').replace(/`/g, '');
        
        let speechText = cleanText;
        
        speechText = speechText.replace(/\([^)]+\)/g, '');
        
        const utterance = new SpeechSynthesisUtterance(speechText);
        
        if (/[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\uFF00-\uFFEF\u4E00-\u9FAF]/.test(speechText)) {
            utterance.lang = 'ja-JP';
        } else {
            utterance.lang = 'en-US';
        }
        
        synth.speak(utterance);
    }
    
    async function sendMessage() {
        const message = messageInput.value.trim();
        
        if (!message && !currentImageData) return;
        
        const imageDataToSend = currentImageData;
        
        addUserMessage(message, imageDataToSend);
        
        messageInput.value = '';
        
        clearImagePreview();
        
        currentImageData = null;
        
        const loadingElement = addLoadingIndicator();
        
        try {
            const hasCameraQuery = message.toLowerCase().includes('camera') || 
                                  message.toLowerCase().includes('look') || 
                                  message.toLowerCase().includes('see') ||
                                  message.toLowerCase().includes('what is this');
            
            const useFallback = true; 
            
            if (imageDataToSend && useFallback) {
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
                speakText(response);
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
                speakText(response);
                return;
            }
            
            const requestData = {
                message: message
            };
            
            if (imageDataToSend) {
                let base64Data = imageDataToSend;
                
                if (base64Data.includes(',')) {
                    base64Data = imageDataToSend.split(',')[1];
                } else if (base64Data.startsWith('data:')) {
                    base64Data = base64Data.replace(/^data:image\/(png|jpeg|jpg);base64,/, '');
                }
                
                requestData.image_data = `data:image/jpeg;base64,${base64Data}`;
                
                console.log('Image data:', requestData.image_data.substring(0, 50) + '...');
            }
            
            const hostname = window.location.hostname;
            const protocol = window.location.protocol;
            const port = window.location.port ? `:${window.location.port}` : '';
            
            const apiUrl = `${protocol}//${hostname}${port}/api/chat`;
            
            console.log('Sending request to:', apiUrl);
            console.log('Image data included:', !!imageDataToSend);
            
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
                speakText(data.response);
            }
            
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
            
            if (messageInput.value.trim() === '') {
                messageInput.value = 'What is in this image?';
            }
            
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
            const imgContainer = document.createElement('div');
            imgContainer.className = 'image-container';
            
            const img = document.createElement('img');
            
            let imgSrc = imageData;
            if (typeof imageData === 'string') {
                if (!imageData.startsWith('data:')) {
                    imgSrc = `data:image/jpeg;base64,${imageData}`;
                }
            }
            
            img.src = imgSrc;
            img.alt = 'User Image';
            img.className = 'chat-image';
            img.style.maxWidth = '200px';
            img.style.maxHeight = '200px';
            img.style.borderRadius = '8px';
            img.style.marginTop = '8px';
            
            imgContainer.appendChild(img);
            messageDiv.appendChild(imgContainer);
            
            console.log('Image added to chat:', imgSrc.substring(0, 50) + '...');
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
