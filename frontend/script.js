document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = "http://104.248.31.242:8000"; // Adjust if your backend runs elsewhere

    // Конфигурация Elements
    const clientIdInput = document.getElementById('clientId');
    const clientSecretInput = document.getElementById('clientSecret');
    const feedUrlInput = document.getElementById('feedUrl');
    const feedOffsetInput = document.getElementById('feedOffset');
    const maxItemsInput = document.getElementById('maxItems');
    const keywordFilterInput = document.getElementById('keywordFilter');
    const startBtn = document.getElementById('startBtn');
    const newUploadBtn = document.getElementById('newUploadBtn');

    // Status Area Elements
    const statusArea = document.getElementById('statusArea');
    const statusMessage = document.getElementById('statusMessage');
    const processedCount = document.getElementById('processedCount');
    const maxConfiguredItems = document.getElementById('maxConfiguredItems');
    const consideredCount = document.getElementById('consideredCount');
    const totalOffersInFeedSlice = document.getElementById('totalOffersInFeedSlice');
    const itemsReady = document.getElementById('itemsReady');
    const errorDisplay = document.getElementById('errorDisplay');

    // Decision Area Elements
    const decisionArea = document.getElementById('decisionArea');
    const offerName = document.getElementById('offerName');
    const offerId = document.getElementById('offerId');
    const similarityScore = document.getElementById('similarityScore');
    const suggestionsList = document.getElementById('suggestionsList');
    const decisionForm = document.getElementById('decisionForm');
    const typeIdInput = document.getElementById('typeId');
    const descCatIdInput = document.getElementById('descCatId');
    const skipOfferBtn = document.getElementById('skipOfferBtn');
    
    // Submission Area Elements
    const submissionArea = document.getElementById('submissionArea');
    const submitToOzonBtn = document.getElementById('submitToOzonBtn');
    
    // Ozon Results Area Elements
    const ozonResultsArea = document.getElementById('ozonResultsArea');
    const ozonTaskId = document.getElementById('ozonTaskId');
    const ozonTaskInfo = document.getElementById('ozonTaskInfo');
    const refreshTaskInfoBtn = document.getElementById('refreshTaskInfoBtn');

    let currentDecisionId = null;
    let currentOzonTaskId = null;

    function showError(message) {
        errorDisplay.textContent = message;
        errorDisplay.style.display = 'block';
    }
    function clearError() {
        errorDisplay.textContent = '';
        errorDisplay.style.display = 'none';
    }

    function resetUIForNewUpload() {
        // Hide dynamic areas
        decisionArea.style.display = 'none';
        submissionArea.style.display = 'none';
        ozonResultsArea.style.display = 'none';

        // Clear status area content, then set a new message
        statusMessage.textContent = "Готово к новой загрузке. Введите конфигурацию и нажмите 'Начать обработку'.";
        processedCount.textContent = '0';
        // maxConfiguredItems will be updated by startBtn click
        consideredCount.textContent = '0';
        totalOffersInFeedSlice.textContent = '0';
        itemsReady.textContent = '0';
        statusArea.style.display = 'block'; // Keep status area visible with the new message

        clearError();

        // Reset internal state variables
        currentDecisionId = null;
        currentOzonTaskId = null;

        // Enable config inputs and start button
        clientIdInput.disabled = false;
        clientSecretInput.disabled = false;
        feedUrlInput.disabled = false;
        feedOffsetInput.disabled = false;
        maxItemsInput.disabled = false;
        keywordFilterInput.disabled = false;
        startBtn.disabled = false;

        // Reset submission and Ozon results elements
        submitToOzonBtn.disabled = true;
        refreshTaskInfoBtn.style.display = 'none';
        ozonTaskInfo.textContent = '';
        ozonTaskId.textContent = '';

        // Clear decision form inputs (optional, but good for a clean slate)
        typeIdInput.value = '';
        descCatIdInput.value = '';
        suggestionsList.innerHTML = '';
    }


    function updateStatusUI(data) {
        clearError();
        statusArea.style.display = 'block';
        statusMessage.textContent = data.status_message;
        processedCount.textContent = data.processed_item_count_for_api;
        maxConfiguredItems.textContent = maxItemsInput.value; // Reflects current config
        consideredCount.textContent = data.current_offer_index_overall - (parseInt(feedOffsetInput.value) || 0);
        totalOffersInFeedSlice.textContent = data.total_offers_to_consider;
        itemsReady.textContent = data.items_ready_for_submission;

        if (data.error_message) {
            showError(data.error_message);
        }

        startBtn.disabled = !!data.pending_decision_id;

        // Always clear and update suggestions list when decision is required
        if (data.pending_decision_id && data.decision_details) {
            currentDecisionId = data.pending_decision_id;
            decisionArea.style.display = 'block';
            offerName.textContent = data.decision_details.name;
            offerId.textContent = data.decision_details.offer_id;

            // Show similarity score if available
            if (typeof data.decision_details.current_similarity === 'number') {
                similarityScore.textContent = data.decision_details.current_similarity.toFixed(2);
            } else {
                similarityScore.textContent = '';
            }

            suggestionsList.innerHTML = '';
            if (Array.isArray(data.decision_details.suggestions) && data.decision_details.suggestions.length > 0) {
                data.decision_details.suggestions.forEach((s, index) => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span><b>${s.type_name}</b> (Уверенность: ${typeof s.similarity === 'number' ? s.similarity.toFixed(2) : 'Н/Д'})</span>`;
                    const useBtn = document.createElement('button');
                    useBtn.textContent = '✔️';
                    useBtn.onclick = () => {
                        typeIdInput.value = s.type_id;
                        descCatIdInput.value = s.description_category_id; // Corrected: Use backend-resolved value directly
                    };
                    li.appendChild(useBtn);
                    suggestionsList.appendChild(li);
                    // Autofill the first suggestion
                    if (index === 0) {
                        typeIdInput.value = s.type_id;
                        descCatIdInput.value = s.description_category_id; // Corrected: Use backend-resolved value directly
                    }
                });
            } else {
                suggestionsList.innerHTML = '<li>Предложения недоступны. Пожалуйста, введите вручную.</li>';
                typeIdInput.value = '';
                descCatIdInput.value = '';
            }
            // Ensure decision form buttons are enabled when decision area is shown
            decisionForm.querySelector('button[type="submit"]').disabled = false;
            skipOfferBtn.disabled = false;
            submissionArea.style.display = 'none';
        } else {
            decisionArea.style.display = 'none';
            currentDecisionId = null;
        }

        const isProcessingCompleteOrMaxed = data.status_message.includes("Готово к отправке") || 
                                          data.status_message.includes("Все товары обработаны") || 
                                          data.status_message.includes("Достигнуто максимальное количество");
        
        if (isProcessingCompleteOrMaxed && !data.pending_decision_id) {
             if (data.items_ready_for_submission > 0) {
                submissionArea.style.display = 'block';
                submitToOzonBtn.disabled = false;
             } else {
                submissionArea.style.display = 'none';
                submitToOzonBtn.disabled = true;
                if(isProcessingCompleteOrMaxed && data.items_ready_for_submission === 0) {
                    // Append to status if processing is done but nothing to submit
                    if (!statusMessage.textContent.includes("Нет товаров для отправки")) {
                         statusMessage.textContent += " Нет товаров для отправки.";
                    }
                }
             }
             startBtn.disabled = false; 
        } else if (!data.pending_decision_id) { 
            submissionArea.style.display = 'none';
            submitToOzonBtn.disabled = true;
        }


        if (data.ozon_submission_task_id) {
            currentOzonTaskId = data.ozon_submission_task_id;
            ozonResultsArea.style.display = 'block';
            ozonTaskId.textContent = currentOzonTaskId;
            refreshTaskInfoBtn.style.display = 'inline-block';
            if (data.ozon_task_info) {
                ozonTaskInfo.textContent = JSON.stringify(data.ozon_task_info, null, 2);
            } else if (currentOzonTaskId) { // Fetch if task_id is present but no info yet
                fetchOzonTaskInfo(); 
            }
        } else {
            // Only hide Ozon results if there was no task ID to begin with or it was explicitly cleared.
            // This prevents hiding results if a status update without task_id (e.g. during processing) occurs.
            if (!currentOzonTaskId) {
                 ozonResultsArea.style.display = 'none';
            }
        }
    }

    async function fetchData(url, options = {}) {
        // Disable all major action buttons during any fetch
        startBtn.disabled = true;
        submitToOzonBtn.disabled = true;
        // Decision form buttons are handled more specifically

        try {
            const response = await fetch(API_BASE_URL + url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `Server error: ${response.statusText}` }));
                throw new Error(`HTTP error ${response.status}: ${errorData.detail || 'Unknown server error'}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            showError(error.message);
            // Re-enable start button if a general fetch error occurs and not in a decision state
            if (!currentDecisionId) {
                startBtn.disabled = false;
            }
            throw error; 
        }
    }

    startBtn.addEventListener('click', async () => {
        // Validate required fields
        if (!clientIdInput.value.trim()) {
            showError('Client ID обязателен');
            return;
        }
        if (!clientSecretInput.value.trim()) {
            showError('Client Secret обязателен');
            return;
        }

        statusMessage.textContent = "Запуск обработки...";
        clearError();
        ozonResultsArea.style.display = 'none'; 
        currentOzonTaskId = null; 
        submissionArea.style.display = 'none';
        decisionArea.style.display = 'none';

        const config = {
            client_id: clientIdInput.value.trim(),
            client_secret: clientSecretInput.value.trim(),
            feed_url: feedUrlInput.value.trim() || null,
            feed_offset: parseInt(feedOffsetInput.value) || 0,
            max_items: parseInt(maxItemsInput.value) || 10,
            keyword: keywordFilterInput.value.trim() || null
        };
        maxConfiguredItems.textContent = config.max_items;

        try {
            // Disable config inputs during processing
            clientIdInput.disabled = true;
            clientSecretInput.disabled = true;
            feedUrlInput.disabled = true;
            feedOffsetInput.disabled = true;
            maxItemsInput.disabled = true;
            keywordFilterInput.disabled = true;

            const data = await fetchData('/start-processing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            updateStatusUI(data);
        } catch (err) {
            startBtn.disabled = false;
            // Re-enable config inputs if start fails
            clientIdInput.disabled = false;
            clientSecretInput.disabled = false;
            feedUrlInput.disabled = false;
            feedOffsetInput.disabled = false;
            maxItemsInput.disabled = false;
            keywordFilterInput.disabled = false;
        }
    });

    decisionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!currentDecisionId) {
            showError('Нет активного решения для отправки');
            return;
        }

        // Validate required fields
        const typeId = parseInt(typeIdInput.value);
        const descCatId = parseInt(descCatIdInput.value);
        
        if (!typeId || isNaN(typeId)) {
            showError('Type ID обязателен и должен быть числом');
            return;
        }
        
        if (!descCatId || isNaN(descCatId)) {
            showError('Description Category ID обязателен и должен быть числом');
            return;
        }

        const payload = {
            chosen_type_id: typeId,
            chosen_description_category_id: descCatId
        };
        
        // Store the decision ID to ensure we're working with the correct one
        const decisionIdToSubmit = currentDecisionId;
        
        decisionForm.querySelector('button[type="submit"]').disabled = true;
        skipOfferBtn.disabled = true;

        try {
            // URL encode the decision ID to handle special characters like slashes
            const encodedDecisionId = encodeURIComponent(decisionIdToSubmit);
            const data = await fetchData(`/submit-decision/${encodedDecisionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            // If the submission was successful and no new decision is immediately pending,
            // explicitly hide the decision area. updateStatusUI will confirm this.
            if (!data.pending_decision_id) {
                decisionArea.style.display = 'none';
            }
            updateStatusUI(data);
        } catch (err) { 
            // If error, re-enable decision buttons if still in decision state
            if (currentDecisionId === decisionIdToSubmit && decisionArea.style.display === 'block') {
                 decisionForm.querySelector('button[type="submit"]').disabled = false;
                 skipOfferBtn.disabled = false;
            }
        }
    });

    skipOfferBtn.addEventListener('click', async () => {
        if (!currentDecisionId) {
            showError('Нет активного решения для пропуска');
            return;
        }
        
        // Store the decision ID to ensure consistency
        const decisionIdToSkip = currentDecisionId;
        
        decisionForm.querySelector('button[type="submit"]').disabled = true;
        skipOfferBtn.disabled = true;
        
        try {
            // URL encode the decision ID to handle special characters like slashes
            const encodedDecisionId = encodeURIComponent(decisionIdToSkip);
            const data = await fetchData(`/skip-offer/${encodedDecisionId}`, { method: 'POST' });
            // If skipping was successful and no new decision is immediately pending,
            // explicitly hide the decision area. updateStatusUI will confirm this.
            if (!data.pending_decision_id) {
                decisionArea.style.display = 'none';
            }
            updateStatusUI(data);
        } catch (err) { 
            if (currentDecisionId === decisionIdToSkip && decisionArea.style.display === 'block') {
                 decisionForm.querySelector('button[type="submit"]').disabled = false;
                 skipOfferBtn.disabled = false;
            }
        }
    });

    submitToOzonBtn.addEventListener('click', async () => {
        statusMessage.textContent = "Отправка в Ozon...";
        try {
            const submissionResponse = await fetchData('/submit-to-ozon', { method: 'POST' });
            // After attempting submission, always fetch the latest full status.
            // The submissionResponse might just be a task_id or simple ack.
            const statusData = await fetchData('/processing-status'); 
            updateStatusUI(statusData); 

            // Explicitly handle currentOzonTaskId if submissionResponse contains it,
            // as /processing-status might lag or be a generic state.
            if (submissionResponse && submissionResponse.task_id) {
                 currentOzonTaskId = submissionResponse.task_id;
                 ozonResultsArea.style.display = 'block';
                 ozonTaskId.textContent = currentOzonTaskId;
                 refreshTaskInfoBtn.style.display = 'inline-block';
                 fetchOzonTaskInfo(); // Fetch immediately
            } else if (!currentOzonTaskId && statusData.ozon_submission_task_id) {
                // Fallback if direct response didn't have it but status did
                currentOzonTaskId = statusData.ozon_submission_task_id;
            }

        } catch (err) {
            // If submission fails before getting a task_id, re-enable button
            // updateStatusUI will handle button states based on the overall status
            const latestStatus = await fetchData('/processing-status').catch(() => null);
            if (latestStatus) updateStatusUI(latestStatus);
            else if (!currentOzonTaskId) submitToOzonBtn.disabled = false; // Fallback if status also fails
        }
    });
    
    async function fetchOzonTaskInfo() {
        if (!currentOzonTaskId) return;
        refreshTaskInfoBtn.disabled = true;
        ozonTaskInfo.textContent = "Получение информации о задаче...";
        try {
            // Use a more specific fetchData call that doesn't globally disable unrelated buttons
            const response = await fetch(API_BASE_URL + `/ozon-task-info/${currentOzonTaskId}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `Server error: ${response.statusText}` }));
                throw new Error(`HTTP error ${response.status}: ${errorData.detail || 'Unknown server error'}`);
            }
            const data = await response.json();
            ozonTaskInfo.textContent = JSON.stringify(data, null, 2);
        } catch (err) {
            console.error('Ошибка получения информации о задаче Ozon:', err);
            ozonTaskInfo.textContent = `Ошибка получения информации о задаче: ${err.message}`;
            showError(`Не удалось получить информацию о задаче Ozon: ${err.message}`);
        } finally {
            refreshTaskInfoBtn.disabled = false;
        }
    }

    refreshTaskInfoBtn.addEventListener('click', fetchOzonTaskInfo);

    newUploadBtn.addEventListener('click', async () => {
        try {
            // Call backend to reset its session state
            const statusData = await fetchData('/reset-session-state', { method: 'POST' });
            // Reset UI based on the fresh state from backend or a predefined reset
            resetUIForNewUpload(); // Visually reset the UI first
            if (statusData) { // Then update with any specific messages from backend reset
                statusMessage.textContent = statusData.status_message || "Готово к новой загрузке.";
                // updateStatusUI(statusData); // Or, more comprehensively update based on response
            }
        } catch (error) {
            console.error('Ошибка при сбросе сессии:', error);
            showError('Не удалось сбросить сессию на сервере, но UI сброшен. ' + error.message);
            resetUIForNewUpload(); // Ensure UI is reset even if backend call fails
        }
    });

    // Initial state setup:
    // Call updateStatusUI with a default-like state or fetch initial status
    // This ensures buttons are in a sensible state before any user interaction.
    async function initializeApp() {
        try {
            const data = await fetchData('/processing-status');
            updateStatusUI(data);
        } catch (err) {
            if (statusMessage) {
                statusMessage.textContent = "Готово к запуску. Не удалось подключиться к серверу или получить начальный статус.";
            }
            console.warn("Не удалось получить начальный статус:", err.message);
            // Set a basic initial state for UI elements if backend is down
            statusArea.style.display = 'block';
            startBtn.disabled = false; // Allow user to try starting
            submissionArea.style.display = 'none';
            decisionArea.style.display = 'none';
            ozonResultsArea.style.display = 'none';
        }
    }
    initializeApp();
});
