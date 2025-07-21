document.addEventListener('DOMContentLoaded', () => {
    // ÇOK ÖNEMLİ: BU BİLGİLERİ KENDİ FIREBASE PROJENİZDEN ALIP DOLDURUN
    const firebaseConfig = {
        apiKey: "AIzaSyDkJch-8B46dpZSB-pMSR4q1uvzadCVekE",
        authDomain: "aviator-90c8b.firebaseapp.com",
        databaseURL: "https://aviator-90c8b-default-rtdb.firebaseio.com",
        projectId: "aviator-90c8b",
        storageBucket: "aviator-90c8b.appspot.com",
        messagingSenderId: "823763988442",
        appId: "1:823763988442:web:16a797275675a219c3dae3"
    };
    // -----------------------------------------------------------------

    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
    const database = firebase.database();

    // HTML elementleri
    const loginContainer = document.getElementById('login-container');
    const appContainer = document.getElementById('app-container');
    const loginButton = document.getElementById('login-button');
    const logoutButton = document.getElementById('logout-button');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('login-error');
    const symbolInput = document.getElementById('symbol-input');
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');
    const statusMessageSpan = document.getElementById('status-message');
    const currentSymbolSpan = document.getElementById('current-symbol');
    const positionStatusSpan = document.getElementById('position-status');
    const lastSignalSpan = document.getElementById('last-signal');
    const statsTotal = document.getElementById('stats-total-trades');
    const statsWinning = document.getElementById('stats-winning-trades');
    const statsLosing = document.getElementById('stats-losing-trades');
    const statsTotalProfit = document.getElementById('stats-total-profit');
    const statsTotalLoss = document.getElementById('stats-total-loss');
    const statsNetPnl = document.getElementById('stats-net-pnl');
    let statusInterval;

    // --- KİMLİK DOĞRULAMA ---
    loginButton.addEventListener('click', () => {
        loginError.textContent = "";
        auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
            .catch(error => { loginError.textContent = "Hatalı e-posta veya şifre."; });
    });

    logoutButton.addEventListener('click', () => { auth.signOut(); });

    auth.onAuthStateChanged(user => {
        if (user) {
            loginContainer.style.display = 'none';
            appContainer.style.display = 'flex';
            getStatus();
            statusInterval = setInterval(getStatus, 8000); // Durum sorgulama aralığı
            listenForTradeUpdates();
        } else {
            loginContainer.style.display = 'flex';
            appContainer.style.display = 'none';
            if (statusInterval) clearInterval(statusInterval);
        }
    });

    // --- API İSTEKLERİ ---
    async function fetchApi(endpoint, options = {}) {
        const user = auth.currentUser;
        if (!user) { return null; }
        const idToken = await user.getIdToken(true);
        const headers = { ...options.headers, 'Authorization': `Bearer ${idToken}` };
        if (options.body) headers['Content-Type'] = 'application/json';
        try {
            const response = await fetch(endpoint, { ...options, headers });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                console.error("API Hatası:", errorData.detail);
                // Kullanıcıya hata göstermek için bir mekanizma eklenebilir
                return null;
            }
            return response.json();
        } catch (error) { console.error("API isteği hatası:", error); return null; }
    }
    
    // --- ARAYÜZ GÜNCELLEME ---
    const updateUI = (data) => {
        if (!data) return;
        statusMessageSpan.textContent = data.status_message;
        currentSymbolSpan.textContent = data.symbol || 'N/A';
        lastSignalSpan.textContent = data.last_signal || 'N/A';
        if (data.is_running) {
            startButton.disabled = true; stopButton.disabled = false; symbolInput.disabled = true;
            symbolInput.value = data.symbol; statusMessageSpan.className = 'status-running';
        } else {
            startButton.disabled = false; stopButton.disabled = true; symbolInput.disabled = false;
            statusMessageSpan.className = 'status-stopped';
        }
        positionStatusSpan.textContent = data.in_position ? 'Evet' : 'Hayır';
        positionStatusSpan.className = data.in_position ? 'status-in-position' : '';
    };

    const getStatus = async () => updateUI(await fetchApi('/api/status'));
    startButton.addEventListener('click', async () => {
        const symbol = symbolInput.value.trim().toUpperCase();
        if (!symbol) return alert('Lütfen bir coin sembolü girin.');
        updateUI(await fetchApi('/api/start', { method: 'POST', body: JSON.stringify({ symbol }) }));
    });
    stopButton.addEventListener('click', async () => updateUI(await fetchApi('/api/stop', { method: 'POST' })));

    // --- İSTATİSTİK HESAPLAMA ---
    function listenForTradeUpdates() {
        const tradesRef = database.ref('trades');
        tradesRef.on('value', (snapshot) => {
            const trades = snapshot.val() ? Object.values(snapshot.val()) : [];
            calculateAndDisplayStats(trades);
        });
    }

    function calculateAndDisplayStats(trades) {
        let totalTrades = trades.length;
        let winningTrades = 0, losingTrades = 0;
        let totalProfit = 0, totalLoss = 0;

        trades.forEach(trade => {
            const pnl = parseFloat(trade.pnl) || 0;
            if (pnl > 0) {
                winningTrades++;
                totalProfit += pnl;
            } else {
                losingTrades++;
                totalLoss += pnl;
            }
        });
        
        const netPnl = totalProfit + totalLoss;

        statsTotal.textContent = totalTrades;
        const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;
        const loseRate = totalTrades > 0 ? ((losingTrades / totalTrades) * 100).toFixed(1) : 0;
        statsWinning.textContent = `${winningTrades} (%${winRate})`;
        statsLosing.textContent = `${losingTrades} (%${loseRate})`;

        formatPnl(statsTotalProfit, totalProfit);
        formatPnl(statsTotalLoss, totalLoss);
        formatPnl(statsNetPnl, netPnl);
    }

    function formatPnl(element, value) {
        element.textContent = `${value.toFixed(2)} USDT`;
        element.className = value > 0 ? 'stats-value pnl-positive' : (value < 0 ? 'stats-value pnl-negative' : 'stats-value');
    }
});
