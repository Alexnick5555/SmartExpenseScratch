/**
 * SmartExpense - Voice Input Module
 * Listens to user speech and auto-fills expense/income form fields.
 * Developed by Nitish Mishra & Nishant Singh
 */

const VoiceInput = (() => {

    // Keywords mapped to partial category names (matched against <select> option text)
    const CATEGORY_KEYWORDS = {
        'food':         ['food', 'eating', 'eat', 'restaurant', 'lunch', 'dinner', 'breakfast',
                         'cafe', 'coffee', 'meal', 'snack', 'pizza', 'burger', 'biryani',
                         'chai', 'tea', 'swiggy', 'zomato', 'dhaba', 'hotel food'],
        'transport':    ['transport', 'taxi', 'uber', 'ola', 'auto', 'bus', 'train', 'metro',
                         'fuel', 'petrol', 'diesel', 'rickshaw', 'cab', 'parking', 'bike',
                         'rapido', 'local', 'commute', 'fare'],
        'shopping':     ['shopping', 'clothes', 'shirt', 'shoes', 'amazon', 'flipkart',
                         'purchase', 'bought', 'dress', 'pants', 'outfit', 'clothing', 'apparel'],
        'bills':        ['bill', 'electricity', 'water', 'gas', 'internet', 'recharge',
                         'wifi', 'utility', 'phone bill', 'mobile bill', 'broadband', 'dth'],
        'entertainment':['entertainment', 'movie', 'netflix', 'spotify', 'youtube', 'game',
                         'gaming', 'music', 'concert', 'show', 'cinema', 'ott', 'prime',
                         'hotstar', 'theatre', 'ticket'],
        'health':       ['health', 'medicine', 'doctor', 'hospital', 'gym', 'fitness',
                         'pharmacy', 'medical', 'clinic', 'tablet', 'injection', 'checkup'],
        'education':    ['education', 'book', 'course', 'tuition', 'college', 'school',
                         'fees', 'stationery', 'pen', 'notebook', 'class', 'coaching'],
        'travel':       ['travel', 'flight', 'hotel', 'trip', 'holiday', 'vacation',
                         'booking', 'tour', 'journey', 'airfare', 'resort'],
        'groceries':    ['groceries', 'grocery', 'vegetable', 'fruit', 'milk', 'bread',
                         'supermarket', 'kirana', 'sabzi', 'ration', 'dmart', 'bigbasket'],
        'salary':       ['salary', 'wages', 'paycheck', 'stipend', 'monthly salary'],
        'freelance':    ['freelance', 'project payment', 'client', 'gig'],
        'investment':   ['investment', 'stocks', 'mutual fund', 'sip', 'shares', 'dividend'],
        'gift':         ['gift', 'birthday', 'celebration', 'present', 'bonus'],
        'rent':         ['rent', 'house rent', 'flat rent', 'pg', 'hostel'],
    };

    const EXPENSE_WORDS = ['spent', 'spend', 'paid', 'pay', 'bought', 'buy', 'purchase',
                           'expense', 'cost', 'charged', 'deducted', 'used', 'withdrawn'];
    const INCOME_WORDS  = ['received', 'receive', 'earned', 'earn', 'got', 'income',
                           'salary', 'credited', 'deposited', 'transferred to me', 'payment received'];

    // Voice command patterns
    const COMMAND_PATTERNS = {
        // Navigation commands
        'dashboard': ['go to dashboard', 'show dashboard', 'open dashboard', 'dashboard'],
        'expenses': ['go to expenses', 'show expenses', 'open expenses', 'expenses', 'my expenses'],
        'income': ['go to income', 'show income', 'open income', 'income', 'my income'],
        'accounts': ['go to accounts', 'show accounts', 'open accounts', 'accounts', 'my accounts'],
        'reports': ['go to reports', 'show reports', 'open reports', 'reports'],
        'analytics': ['go to analytics', 'show analytics', 'open analytics', 'analytics'],
        'templates': ['go to templates', 'show templates', 'open templates', 'templates'],
        'recurring': ['go to recurring', 'show recurring', 'open recurring', 'recurring', 'recurring transactions'],
        'calendar': ['go to calendar', 'show calendar', 'open calendar', 'calendar'],
        'settings': ['go to settings', 'show settings', 'open settings', 'settings'],
        'profile': ['go to profile', 'show profile', 'open profile', 'profile'],
        
        // Action commands
        'add_expense': ['add expense', 'new expense', 'create expense', 'expense add'],
        'add_income': ['add income', 'new income', 'create income', 'income add'],
        'quick_add': ['quick add', 'quick expense', 'quick income'],
        
        // Query commands
        'show_balance': ['show balance', 'my balance', 'what is my balance', 'check balance'],
        'show_spending': ['show spending', 'my spending', 'what did i spend', 'total spending'],
        'show_income': ['show income', 'my income', 'what did i earn', 'total income'],
        'show_savings': ['show savings', 'my savings', 'how much did i save'],
        'show_net_worth': ['show net worth', 'my net worth', 'what is my net worth'],
        
        // Utility commands
        'help': ['help', 'what can i say', 'voice commands', 'commands'],
        'stop': ['stop', 'cancel', 'never mind', 'forget it'],
    };

    // ── Parsers ────────────────────────────────────────────────────────────────

    function extractAmount(text) {
        const wordMap = { 
            lakh: 100000, lac: 100000, 
            thousand: 1000, k: 1000, 
            hundred: 100
        };
        
        // Handle "1 lakh", "2 thousand", "5 hundred", "1.5k"
        let match = text.match(/(\d+(?:\.\d+)?)\s*(lakh|lac|thousand|hundred|k)\b/i);
        if (match) return String(parseFloat(match[1]) * wordMap[match[2].toLowerCase()]);

        // Handle word numbers like "five hundred", "two thousand"
        const wordNumbers = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
            'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
            'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
            'eighty': 80, 'ninety': 90
        };
        
        const wordMatch = text.toLowerCase().match(/(\w+)\s*(hundred|thousand|lakh|k|lac)/);
        if (wordMatch && wordNumbers[wordMatch[1]]) {
            const num = wordNumbers[wordMatch[1]];
            const multiplier = wordMatch[2] === 'hundred' ? 100 : wordMatch[2] === 'thousand' || wordMatch[2] === 'k' ? 1000 : 100000;
            return String(num * multiplier);
        }
        
        // Plain number with optional commas and currency symbols
        const numMatch = text.match(/₹?\s*(\d[\d,]*(?:\.\d+)?)/);
        if (numMatch) return numMatch[1].replace(/,/g, '');

        return '';
    }

    function detectType(text) {
        const lower = text.toLowerCase();
        for (const w of INCOME_WORDS) if (lower.includes(w)) return 'income';
        for (const w of EXPENSE_WORDS) if (lower.includes(w)) return 'expense';
        return 'expense';
    }

    function findCategoryOption(text, selectEl) {
        if (!selectEl) return '';
        const lower = text.toLowerCase();
        const options = Array.from(selectEl.options).filter(o => o.value !== '');

        // 1. Direct option-text substring match
        for (const opt of options) {
            const name = opt.text.toLowerCase();
            if (lower.includes(name)) return opt.value;
            // Also try individual words of the category name
            for (const part of name.split(/[\s&]/)) {
                if (part.length > 3 && lower.includes(part)) return opt.value;
            }
        }

        // 2. Keyword-to-category mapping
        for (const [key, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
            for (const kw of keywords) {
                if (lower.includes(kw)) {
                    // Find the option whose text partially matches the key
                    for (const opt of options) {
                        if (opt.text.toLowerCase().includes(key)) return opt.value;
                    }
                }
            }
        }

        return '';
    }

    function buildDescription(text, amount, categoryName) {
        let desc = text;
        
        // Remove amount patterns
        if (amount) {
            const amountStr = String(amount).replace('.', '\\.');
            desc = desc.replace(new RegExp(amountStr, 'gi'), '');
            desc = desc.replace(/Rs\.?\s*\d+[\d,]*/gi, '');
            desc = desc.replace(/₹\s*\d+[\d,]*/gi, '');
            desc = desc.replace(/\d+\s*(lakh|lac|thousand|hundred|k)/gi, '');
        }
        
        // More comprehensive list of words to remove
        const removeWords = ['spent', 'spend', 'paid', 'pay', 'bought', 'buy', 'purchase',
            'expense', 'cost', 'charged', 'deducted', 'used', 'withdrawn', 'on',
            'for', 'to', 'at', 'the', 'a', 'an', 'my', 'i', 'received', 'receive',
            'earned', 'earn', 'got', 'credited', 'deposited', 'transferred',
            'rupees', 'rupee', 'rs', 'inr', 'amount', 'today', 'yesterday', 
            'this', 'month', 'week', 'day', 'morning', 'evening', 'night',
            'just', 'only', 'mere', 'liye', 'ke', 'ka', 'ki', 'ke liye'];
        
        const words = desc.split(/\s+/).filter(w => {
            const lower = w.toLowerCase().replace(/[^\w]/g, '');
            return lower.length > 2 && !removeWords.includes(lower);
        });
        
        // Take first 4-5 meaningful words for description
        if (words.length > 0) {
            desc = words.slice(0, 5).join(' ');
            // Capitalize first letter
            desc = desc.charAt(0).toUpperCase() + desc.slice(1);
            return desc;
        }
        
        // Fallback
        return categoryName ? `${categoryName}` : 'Expense';
    }

    function parse(transcript, categorySelectEl) {
        const amount   = extractAmount(transcript);
        const type     = detectType(transcript);
        const catVal   = findCategoryOption(transcript, categorySelectEl);
        const catName  = catVal && categorySelectEl
            ? Array.from(categorySelectEl.options).find(o => o.value === catVal)?.text || ''
            : '';
        const description = buildDescription(transcript, amount, catName);
        return { amount, type, categoryValue: catVal, categoryName: catName, description, raw: transcript };
    }

    // ── UI Helpers ─────────────────────────────────────────────────────────────

    function setFieldValue(selector, value) {
        const el = document.querySelector(selector);
        if (!el || !value) return;
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function fillForm(result, opts = {}) {
        const {
            amountSelector      = '#id_amount',
            typeSelector        = '#id_transaction_type',
            categorySelector    = '#id_category',
            descriptionSelector = '#id_description',
        } = opts;

        if (result.amount)        setFieldValue(amountSelector, result.amount);
        if (result.type)          setFieldValue(typeSelector, result.type);
        if (result.categoryValue) setFieldValue(categorySelector, result.categoryValue);
        if (result.description)   setFieldValue(descriptionSelector, result.description);
    }

    function fillQuickForm(result, opts = {}) {
        const {
            amountSelector      = '[name="amount"]',
            categorySelector    = '[name="category"]',
            descriptionSelector = '[name="description"]',
        } = opts;

        if (result.amount)        { const el = document.querySelector(amountSelector);      if (el) el.value = result.amount; }
        if (result.categoryValue) { const el = document.querySelector(categorySelector);    if (el) el.value = result.categoryValue; }
        if (result.description)   { const el = document.querySelector(descriptionSelector); if (el) el.value = result.description; }
    }

    // ── SpeechRecognition wrapper ──────────────────────────────────────────────

    function createRecognizer() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) return null;
        const rec = new SR();
        rec.lang = 'en-IN';
        rec.interimResults = false;
        rec.maxAlternatives = 1;
        rec.continuous = false;
        return rec;
    }

    // ── Button factory ─────────────────────────────────────────────────────────

    /**
     * Creates and returns a voice button element.
     * @param {object} options
     *   categorySelector  — CSS selector for the category <select>
     *   onResult(result)  — called with parsed result
     *   onTranscript(txt) — called with raw transcript string (optional)
     *   mode              — 'form' | 'quick'  (affects fillForm vs fillQuickForm)
     *   formSelectors     — override default selectors
     */
    function createButton(options = {}) {
        const {
            categorySelector = '#id_category',
            onResult,
            onTranscript,
            mode = 'form',
            formSelectors = {},
        } = options;

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-voice';
        btn.title = 'Click and speak your expense';
        btn.innerHTML = `<i class="bi bi-mic-fill"></i><span class="voice-label">Voice</span>`;

        // Inject button styles once
        if (!document.getElementById('voice-btn-style')) {
            const style = document.createElement('style');
            style.id = 'voice-btn-style';
            style.textContent = `
                .btn-voice {
                    background: linear-gradient(135deg, #4F46E5, #7C3AED);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 0.5rem 1rem;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.4rem;
                    font-size: 0.9rem;
                    cursor: pointer;
                    transition: all 0.2s;
                    box-shadow: 0 2px 8px rgba(79,70,229,0.35);
                }
                .btn-voice:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(79,70,229,0.45); }
                .btn-voice.listening {
                    background: linear-gradient(135deg, #DC2626, #EF4444);
                    animation: voicePulse 1s infinite;
                    box-shadow: 0 2px 12px rgba(220,38,38,0.5);
                }
                @keyframes voicePulse {
                    0%,100% { transform: scale(1); }
                    50%      { transform: scale(1.06); }
                }
                .voice-transcript-box {
                    background: #F3F4F6;
                    border: 1px dashed #9CA3AF;
                    border-radius: 8px;
                    padding: 0.6rem 0.9rem;
                    font-size: 0.85rem;
                    color: #374151;
                    margin-top: 0.5rem;
                    min-height: 36px;
                    display: none;
                }
                .voice-transcript-box.visible { display: block; }
                .voice-badge {
                    display: inline-block;
                    background: #EDE9FE;
                    color: #5B21B6;
                    border-radius: 6px;
                    padding: 0.15rem 0.5rem;
                    font-size: 0.78rem;
                    font-weight: 600;
                    margin-right: 4px;
                }
                .voice-not-supported {
                    font-size: 0.8rem;
                    color: #9CA3AF;
                    margin-left: 8px;
                }
            `;
            document.head.appendChild(style);
        }

        const rec = createRecognizer();
        if (!rec) {
            btn.disabled = true;
            btn.title = 'Voice input not supported in this browser';
            return btn;
        }

        let listening = false;

        btn.addEventListener('click', () => {
            if (listening) { rec.stop(); return; }
            rec.start();
        });

        rec.onstart = () => {
            listening = true;
            btn.classList.add('listening');
            btn.querySelector('.voice-label').textContent = 'Listening…';
            btn.querySelector('i').className = 'bi bi-mic-mute-fill';
        };

        rec.onend = () => {
            listening = false;
            btn.classList.remove('listening');
            btn.querySelector('.voice-label').textContent = 'Voice';
            btn.querySelector('i').className = 'bi bi-mic-fill';
        };

        rec.onerror = (e) => {
            console.warn('Voice recognition error:', e.error);
            btn.classList.remove('listening');
            btn.querySelector('.voice-label').textContent = 'Voice';
            btn.querySelector('i').className = 'bi bi-mic-fill';
            if (typeof SmartExpense !== 'undefined') {
                SmartExpense.showToast('Could not capture voice. Please try again.', 'warning');
            }
        };

        rec.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (onTranscript) onTranscript(transcript);

            const catSelectEl = document.querySelector(categorySelector);
            const result = parse(transcript, catSelectEl);

            if (mode === 'quick') {
                fillQuickForm(result, formSelectors);
            } else {
                fillForm(result, formSelectors);
            }

            if (onResult) onResult(result);

            if (typeof SmartExpense !== 'undefined') {
                const catLabel = result.categoryName ? `<span class="voice-badge">${result.categoryName}</span>` : '';
                const amtLabel = result.amount ? `<span class="voice-badge">₹${result.amount}</span>` : '';
                SmartExpense.showToast(
                    `Heard: "${transcript}"<br>${amtLabel}${catLabel}`,
                    'success'
                );
            }
        };

        return btn;
    }

    // ── Command Processor ────────────────────────────────────────────────────────

    function detectCommand(text) {
        const lower = text.toLowerCase();
        
        for (const [command, patterns] of Object.entries(COMMAND_PATTERNS)) {
            for (const pattern of patterns) {
                if (lower.includes(pattern)) {
                    return command;
                }
            }
        }
        
        return null;
    }

    function executeCommand(command) {
        if (!command) return false;
        
        const routes = {
            'dashboard': '/dashboard/',
            'expenses': '/expenses/',
            'income': '/income/',
            'accounts': '/accounts/',
            'reports': '/reports/',
            'analytics': '/analytics/',
            'templates': '/templates/',
            'recurring': '/recurring/',
            'calendar': '/financial-calendar/',
            'settings': '/settings/',
            'profile': '/profile/',
            'add_expense': '/expenses/add/',
            'add_income': '/income/add/',
            'quick_add': '/quick-add-expense/',
        };
        
        if (routes[command]) {
            window.location.href = routes[command];
            return true;
        }
        
        // Handle query commands
        if (command === 'show_balance' || command === 'show_spending' ||
            command === 'show_income' || command === 'show_savings' ||
            command === 'show_net_worth') {
            window.location.href = '/dashboard/';
            return true;
        }
        
        // Handle help command
        if (command === 'help') {
            showVoiceHelp();
            return true;
        }
        
        return false;
    }

    function showVoiceHelp() {
        const helpModal = document.createElement('div');
        helpModal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        
        helpModal.innerHTML = `
            <div style="
                background: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 2rem;
                max-width: 600px;
                max-height: 80vh;
                overflow-y: auto;
                color: #E2E8F0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h2 style="font-size: 1.5rem; font-weight: 600; margin: 0;">Voice Commands</h2>
                    <button id="closeVoiceHelp" style="
                        background: none;
                        border: none;
                        color: #94A3B8;
                        font-size: 1.5rem;
                        cursor: pointer;
                        padding: 0.5rem;
                    ">&times;</button>
                </div>
                
                <div style="margin-bottom: 1.5rem;">
                    <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.75rem; color: #3B82F6;">Navigation</h3>
                    <ul style="list-style: none; padding: 0; margin: 0; color: #94A3B8;">
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"Go to dashboard"</strong> - Open dashboard
                        </li>
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"Show expenses"</strong> - View expenses list
                        </li>
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"Go to reports"</strong> - Open reports page
                        </li>
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"Open analytics"</strong> - View analytics
                        </li>
                        <li style="padding: 0.5rem 0;">
                            <strong style="color: #E2E8F0;">"Go to settings"</strong> - Open settings
                        </li>
                    </ul>
                </div>
                
                <div style="margin-bottom: 1.5rem;">
                    <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.75rem; color: #10B981;">Actions</h3>
                    <ul style="list-style: none; padding: 0; margin: 0; color: #94A3B8;">
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"Add expense"</strong> - Create new expense
                        </li>
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"Add income"</strong> - Create new income
                        </li>
                        <li style="padding: 0.5rem 0;">
                            <strong style="color: #E2E8F0;">"Quick add"</strong> - Quick add transaction
                        </li>
                    </ul>
                </div>
                
                <div style="margin-bottom: 1.5rem;">
                    <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.75rem; color: #FBBF24;">Queries</h3>
                    <ul style="list-style: none; padding: 0; margin: 0; color: #94A3B8;">
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"Show my balance"</strong> - View account balances
                        </li>
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            <strong style="color: #E2E8F0;">"What did I spend"</strong> - View spending summary
                        </li>
                        <li style="padding: 0.5rem 0;">
                            <strong style="color: #E2E8F0;">"Show my net worth"</strong> - View net worth
                        </li>
                    </ul>
                </div>
                
                <div>
                    <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.75rem; color: #EF4444;">Transaction Entry</h3>
                    <p style="color: #94A3B8; margin-bottom: 0.5rem;">Say transactions like:</p>
                    <ul style="list-style: none; padding: 0; margin: 0; color: #94A3B8;">
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            "Spent 500 on food at restaurant"
                        </li>
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            "Paid 2000 for electricity bill"
                        </li>
                        <li style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                            "Received 50000 salary"
                        </li>
                        <li style="padding: 0.5rem 0;">
                            "Bought clothes for 3000"
                        </li>
                    </ul>
                </div>
            </div>
        `;
        
        document.body.appendChild(helpModal);
        
        document.getElementById('closeVoiceHelp').addEventListener('click', () => {
            document.body.removeChild(helpModal);
        });
        
        helpModal.addEventListener('click', (e) => {
            if (e.target === helpModal) {
                document.body.removeChild(helpModal);
            }
        });
    }

    // ── Enhanced Voice Command Button ───────────────────────────────────────────

    function createCommandButton(options = {}) {
        const {
            onCommand,
            onTranscript,
        } = options;

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-voice-command';
        btn.title = 'Click and speak a command';
        btn.innerHTML = `<i class="bi bi-mic-fill"></i><span class="voice-label">Voice Command</span>`;

        // Inject button styles once
        if (!document.getElementById('voice-cmd-btn-style')) {
            const style = document.createElement('style');
            style.id = 'voice-cmd-btn-style';
            style.textContent = `
                .btn-voice-command {
                    background: linear-gradient(135deg, #7C3AED, #4F46E5);
                    color: white;
                    border: none;
                    border-radius: 50px;
                    padding: 0.75rem 1.5rem;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-size: 0.95rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.3s;
                    box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4);
                }
                .btn-voice-command:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(124, 58, 237, 0.5);
                }
                .btn-voice-command.listening {
                    background: linear-gradient(135deg, #DC2626, #B91C1C);
                    animation: voiceCmdPulse 1.5s infinite;
                    box-shadow: 0 4px 20px rgba(220, 38, 38, 0.6);
                }
                @keyframes voiceCmdPulse {
                    0%,100% { transform: scale(1); box-shadow: 0 4px 15px rgba(220, 38, 38, 0.4); }
                    50%      { transform: scale(1.05); box-shadow: 0 6px 25px rgba(220, 38, 38, 0.6); }
                }
                .voice-command-fab {
                    position: fixed;
                    bottom: 30px;
                    right: 30px;
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #7C3AED, #4F46E5);
                    color: white;
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.5rem;
                    box-shadow: 0 4px 20px rgba(124, 58, 237, 0.5);
                    transition: all 0.3s;
                    z-index: 9999;
                }
                .voice-command-fab:hover {
                    transform: scale(1.1);
                    box-shadow: 0 6px 30px rgba(124, 58, 237, 0.6);
                }
                .voice-command-fab.listening {
                    background: linear-gradient(135deg, #DC2626, #B91C1C);
                    animation: fabPulse 1.5s infinite;
                }
                @keyframes fabPulse {
                    0%,100% { transform: scale(1); }
                    50%      { transform: scale(1.15); }
                }
            `;
            document.head.appendChild(style);
        }

        const rec = createRecognizer();
        if (!rec) {
            btn.disabled = true;
            btn.title = 'Voice commands not supported in this browser';
            return btn;
        }

        let listening = false;

        btn.addEventListener('click', () => {
            if (listening) { rec.stop(); return; }
            rec.start();
        });

        rec.onstart = () => {
            listening = true;
            btn.classList.add('listening');
            btn.querySelector('.voice-label').textContent = 'Listening…';
            btn.querySelector('i').className = 'bi bi-mic-mute-fill';
        };

        rec.onend = () => {
            listening = false;
            btn.classList.remove('listening');
            btn.querySelector('.voice-label').textContent = 'Voice Command';
            btn.querySelector('i').className = 'bi bi-mic-fill';
        };

        rec.onerror = (e) => {
            console.warn('Voice recognition error:', e.error);
            btn.classList.remove('listening');
            btn.querySelector('.voice-label').textContent = 'Voice Command';
            btn.querySelector('i').className = 'bi bi-mic-fill';
            if (typeof SmartExpense !== 'undefined') {
                SmartExpense.showToast('Could not capture voice. Please try again.', 'warning');
            }
        };

        rec.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (onTranscript) onTranscript(transcript);

            // First check for commands
            const command = detectCommand(transcript);
            if (command) {
                if (executeCommand(command)) {
                    if (typeof SmartExpense !== 'undefined') {
                        SmartExpense.showToast(`Executing: "${transcript}"`, 'success');
                    }
                    if (onCommand) onCommand(command, transcript);
                    return;
                }
            }

            // If no command detected, try to parse as transaction
            const catSelectEl = document.querySelector('#id_category');
            const result = parse(transcript, catSelectEl);

            if (result.amount || result.categoryValue) {
                // Navigate to add expense/income form with pre-filled data
                const type = result.type || 'expense';
                const url = type === 'income' ? '/income/add/' : '/expenses/add/';
                
                // Store data in sessionStorage for pre-filling
                sessionStorage.setItem('voiceTransactionData', JSON.stringify(result));
                
                if (typeof SmartExpense !== 'undefined') {
                    SmartExpense.showToast(`Adding ${type}: "${transcript}"`, 'success');
                }
                
                window.location.href = url;
            } else {
                if (typeof SmartExpense !== 'undefined') {
                    SmartExpense.showToast('Could not understand. Try "help" for commands.', 'warning');
                }
            }

            if (onCommand) onCommand(null, transcript);
        };

        return btn;
    }

    // ── Floating Action Button ─────────────────────────────────────────────────

    function createFloatingButton() {
        const fab = document.createElement('button');
        fab.type = 'button';
        fab.className = 'voice-command-fab';
        fab.title = 'Voice Commands';
        fab.innerHTML = '<i class="bi bi-mic-fill"></i>';

        const rec = createRecognizer();
        if (!rec) {
            fab.style.display = 'none';
            return fab;
        }

        let listening = false;

        fab.addEventListener('click', () => {
            if (listening) { rec.stop(); return; }
            rec.start();
        });

        rec.onstart = () => {
            listening = true;
            fab.classList.add('listening');
        };

        rec.onend = () => {
            listening = false;
            fab.classList.remove('listening');
        };

        rec.onerror = (e) => {
            console.warn('Voice recognition error:', e.error);
            fab.classList.remove('listening');
        };

        rec.onresult = (event) => {
            const transcript = event.results[0][0].transcript;

            // Check for commands
            const command = detectCommand(transcript);
            if (command) {
                executeCommand(command);
                if (typeof SmartExpense !== 'undefined') {
                    SmartExpense.showToast(`Executing: "${transcript}"`, 'success');
                }
                return;
            }

            // Try to parse as transaction
            const catSelectEl = document.querySelector('#id_category');
            const result = parse(transcript, catSelectEl);

            if (result.amount || result.categoryValue) {
                const type = result.type || 'expense';
                const url = type === 'income' ? '/income/add/' : '/expenses/add/';
                sessionStorage.setItem('voiceTransactionData', JSON.stringify(result));
                
                if (typeof SmartExpense !== 'undefined') {
                    SmartExpense.showToast(`Adding ${type}: "${transcript}"`, 'success');
                }
                
                window.location.href = url;
            } else {
                if (typeof SmartExpense !== 'undefined') {
                    SmartExpense.showToast('Could not understand. Try "help" for commands.', 'warning');
                }
            }
        };

        return fab;
    }

    // ── Auto-fill from sessionStorage ───────────────────────────────────────────

    function autoFillFromSession() {
        const data = sessionStorage.getItem('voiceTransactionData');
        if (!data) return;

        try {
            const result = JSON.parse(data);
            sessionStorage.removeItem('voiceTransactionData');

            // Fill form fields
            setTimeout(() => {
                if (result.amount) {
                    const amountEl = document.querySelector('#id_amount');
                    if (amountEl) {
                        amountEl.value = result.amount;
                        amountEl.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
                if (result.categoryValue) {
                    const catEl = document.querySelector('#id_category');
                    if (catEl) {
                        catEl.value = result.categoryValue;
                        catEl.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
                if (result.description) {
                    const descEl = document.querySelector('#id_description');
                    if (descEl) {
                        descEl.value = result.description;
                        descEl.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
                if (result.type) {
                    const typeEl = document.querySelector('#id_transaction_type');
                    if (typeEl) {
                        typeEl.value = result.type;
                        typeEl.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }

                if (typeof SmartExpense !== 'undefined') {
                    SmartExpense.showToast('Form auto-filled from voice input', 'success');
                }
            }, 100);
        } catch (e) {
            console.error('Error parsing voice transaction data:', e);
        }
    }

    // Initialize auto-fill on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoFillFromSession);
    } else {
        autoFillFromSession();
    }

    // Public API
    return {
        createButton,
        parse,
        extractAmount,
        detectType,
        findCategoryOption,
        createCommandButton,
        createFloatingButton,
        showVoiceHelp,
        detectCommand,
        executeCommand
    };

})();

window.VoiceInput = VoiceInput;
