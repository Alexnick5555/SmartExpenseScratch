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

    // Public API
    return { createButton, parse, extractAmount, detectType, findCategoryOption };

})();

window.VoiceInput = VoiceInput;
